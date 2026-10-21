"""부산 사례 심화와 보조 자료 분석.

입력
 - data/processed/sigungu_panel_classified.csv, sido_panel.csv (01·02 실행 결과)
 - data/raw/busan_bigdatawave/ : 부산 Big-데이터웨이브(부산교통공사 역별 권종별 승하차, 부산시설공단 두리발 운행 기록, 노인·장애인 보호구역)
 - data/raw/koroad_api/KoROAD_frequentzoneOldman_2023_2025.csv : 보행노인 교통사고 다발지역(도로교통공단 API)
 - data/raw/kosis_projection/ : 통계청 장래인구추계(성 및 연령별 추계인구, 중위)
출력: outputs/results_busan.json, outputs/tables/table_busan_gu.csv, outputs/figures/fig5_busan_case.png

분석
 1) 부산 도시철도 승차 중 무임 비중 추이(2014~2024) — 고령자의 대중교통 의존 증가
 2) 시도 비교: 반납률 1위 부산의 고령운전자 사고 사망률
 3) 두리발(교통약자 특별교통수단) 2025.5 운행 기록: 미배차율, 접수→승차 대기시간(구군별) — 반납자용 수요응답형 교통 설계 근거
 4) 부산 구군: 버스 이용·고령운전자 사고(2024~2025 합)·두리발 대기
 5) 보행노인 교통사고 다발지역과 노인보호구역의 거리(부산, 보호구역 자료가 있는 11개 구군)
 6) 65세 이상 인구 전망(2025→2035)과 반납 수요
"""
from __future__ import annotations

import glob
import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib import font_manager

ROOT = Path(__file__).resolve().parent.parent
PROC = ROOT / "data" / "processed"
BW = ROOT / "data" / "raw" / "busan_bigdatawave"
KR = ROOT / "data" / "raw" / "koroad_api"
OUTD = ROOT / "outputs"
FIG, TAB = OUTD / "figures", OUTD / "tables"

for fp in font_manager.findSystemFonts():
    if "NotoSansCJK" in fp and ("Regular" in fp or "Medium" in fp):
        font_manager.fontManager.addfont(fp)
plt.rcParams.update({"font.family": "Noto Sans CJK JP", "axes.unicode_minus": False, "figure.dpi": 150, "savefig.dpi": 200,
                     "axes.spines.top": False, "axes.spines.right": False, "axes.titleweight": "bold", "font.size": 10})
for name in ("Noto Sans CJK KR", "Noto Sans CJK JP", "Noto Sans CJK TC"):
    if any(name == f.name for f in font_manager.fontManager.ttflist):
        plt.rcParams["font.family"] = name
        break
INK, MUTED, ACCENT, BLUE = "#1f2937", "#9ca3af", "#d6453d", "#2563eb"


def read_any(path: str | Path, **kw) -> pd.DataFrame:
    for enc in ("utf-8-sig", "cp949"):
        try:
            return pd.read_csv(path, encoding=enc, **kw)
        except UnicodeDecodeError:
            continue
    raise ValueError(path)


def one(pattern: str) -> Path:
    m = sorted(glob.glob(str(BW / pattern)))
    if len(m) != 1:
        raise FileNotFoundError(f"{pattern}: {m}")
    return Path(m[0])


R: dict = {}
d = pd.read_csv(PROC / "sigungu_panel_classified.csv")
s = pd.read_csv(PROC / "sido_panel.csv")

# ------------------------------------------------------------------ 1. 도시철도 무임 비중
e = read_any(one("15128561_*/*.csv"), dtype=str)
for c in ["승차", "무임"]:
    e[c] = pd.to_numeric(e[c].str.replace(",", ""), errors="coerce")
e["year"] = e["연월"].str.extract(r"(\d{4})").astype(int)
ym = e.groupby("year")[["승차", "무임"]].sum()
ym["share"] = ym["무임"] / ym["승차"] * 100
months = e.groupby("year")["연월"].nunique()
assert (months == 12).all(), months
# 교차검사: 부산교통공사 '무임이용인원'(우대권) 연간 합과 같은지
u = pd.concat([read_any(p) for p in glob.glob(str(BW / "15061983_*/*.csv"))])
u["year"] = u["연월"].astype(str).str.strip().str[:4].astype(int)
u = u.drop_duplicates(subset=["연월"])
uy = u.groupby("year")["우대권이용객수"].agg(["sum", "count"])
full = uy[uy["count"] == 12]["sum"]
match = {int(y): bool(int(full[y]) == int(ym.loc[y, "무임"])) for y in full.index if y in ym.index}
R["subway_free"] = {"share": {int(k): round(v, 1) for k, v in ym["share"].items()},
                    "free_riders_2024": int(ym.loc[2024, "무임"]), "boardings_2024": int(ym.loc[2024, "승차"]),
                    "free_riders_2014": int(ym.loc[2014, "무임"]),
                    "crosscheck_with_우대권_series": match}

# ------------------------------------------------------------------ 2. 시도 비교
sr = s.sort_values("return_rate_2024_per1k65", ascending=False).reset_index(drop=True)
bs = s.set_index("sido").loc["부산"]
R["busan_sido"] = {"return_rate_2024": round(float(bs["return_rate_2024_per1k65"]), 2),
                   "return_rank": int(sr.index[sr["sido"] == "부산"][0]) + 1,
                   "olddrv_death_per100k65_2024": round(float(bs["olddrv_death_per100k65_2024"]), 2),
                   "olddrv_death_rank_low": int(s["olddrv_death_per100k65_2024"].rank().loc[s["sido"] == "부산"].iloc[0]),
                   "national_olddrv_death_per100k65_2024": round(float(s["lg_olddrv_death_2024"].sum() / s["p65_2024"].sum() * 1e5), 2),
                   "p65_share_of_national": round(float(bs["p65"] / s["p65"].sum() * 100), 1)}

# ------------------------------------------------------------------ 3. 두리발 운행 기록(2025.5)
t = read_any(one("15147515_*/*.csv"), dtype=str)
for c in ["접수시간", "승차"]:
    t[c] = pd.to_datetime(t[c], errors="coerce")
t["sido_o"] = t["출발지 행정동"].str.split().str[0]
t["gu"] = t["출발지 행정동"].str.split().str[1]
t = t[t["sido_o"] == "부산광역시"].copy()           # 부산 출발만(관외 출발 소수 제외)
t["wait"] = (t["승차"] - t["접수시간"]).dt.total_seconds() / 60
t["dist"] = pd.to_numeric(t["거리(km)"], errors="coerce")
t["fare"] = pd.to_numeric(t["금액"], errors="coerce")
t["unserved"] = t["결과"].eq("미배차")
done = t[t["결과"] == "하차"]
ok = done[(done["예약타입"] == "즉시") & done["wait"].between(0, 300)]   # 음수·5시간 초과는 기록 오류로 제외
R["duribal"] = {"period": [str(t["접수시간"].min().date()), str(t["접수시간"].max().date())],
                "requests": int(len(t)), "completed": int(len(done)), "unserved": int(t["unserved"].sum()),
                "unserved_rate": round(float(t["unserved"].mean() * 100), 1),
                "completed_rate": round(len(done) / len(t) * 100, 1),
                "wait_median_min": round(float(ok["wait"].median()), 1), "wait_p75_min": round(float(ok["wait"].quantile(0.75)), 1),
                "share_wait_over_60": round(float((ok["wait"] > 60).mean() * 100), 1),
                "share_65plus_type": round(float((t["장애유형"] == "65세이상").mean() * 100), 1),
                "share_hospital": round(float((t["목적"] == "병원").mean() * 100), 1),
                "dist_median_km": round(float(done["dist"].median()), 1), "fare_median_won": int(done["fare"].median()),
                "n_wait_obs": int(len(ok)), "excluded_wait_records": int(len(done[(done["예약타입"] == "즉시")]) - len(ok))}
gw = ok.groupby("gu")["wait"].median().rename("duribal_wait_med")
gu_ = t.groupby("gu")["unserved"].mean().mul(100).rename("duribal_unserved")
gn = t.groupby("gu").size().rename("duribal_requests")

# ------------------------------------------------------------------ 4. 부산 구군 표
b = d[d["sido"] == "부산"].copy()
b["olddrv_death_2y"] = b["lg_olddrv_death_2024"] + b["lg_olddrv_death_2025"]
b["olddrv_acc_2y"] = b["lg_olddrv_acc_2024"] + b["lg_olddrv_acc_2025"]
b["olddrv_death_per100k65_2y"] = b["olddrv_death_2y"] / (b["p65"] + b["p65_2024"]) * 1e5   # 2년 합 / 2년 65세 이상 인구 합(연평균 율)
b["olddrv_acc_per1k65_2y"] = b["olddrv_acc_2y"] / (b["p65"] + b["p65_2024"]) * 1000
b = b.merge(gw, left_on="sgg", right_index=True, how="left").merge(gu_, left_on="sgg", right_index=True, how="left") \
     .merge(gn, left_on="sgg", right_index=True, how="left")
cols = ["sgg", "pop", "p65", "share65", "bus_board_pc", "olddrv_death_2y", "olddrv_death_per100k65_2y", "olddrv_acc_per1k65_2y",
        "duribal_requests", "duribal_wait_med", "duribal_unserved"]
b[cols].sort_values("bus_board_pc").to_csv(TAB / "table_busan_gu.csv", index=False, encoding="utf-8-sig")
low = b.sort_values("bus_board_pc").iloc[0]
from scipy import stats  # noqa: E402
R["busan_gu"] = {"lowest_bus": {"sgg": low["sgg"], "bus_board_pc": round(float(low["bus_board_pc"]), 3),
                                "olddrv_death_per100k65_2y": round(float(low["olddrv_death_per100k65_2y"]), 1),
                                "olddrv_death_2y": int(low["olddrv_death_2y"]),
                                "olddrv_rank_high": int(b["olddrv_death_per100k65_2y"].rank(ascending=False).loc[low.name]),
                                "duribal_wait_med": round(float(low["duribal_wait_med"]), 1),
                                "wait_rank_high": int(b["duribal_wait_med"].rank(ascending=False).loc[low.name])},
                 "busan_olddrv_death_per100k65_2y": round(float(b["olddrv_death_2y"].sum() / (b["p65"] + b["p65_2024"]).sum() * 1e5), 1),
                 "spearman_bus_vs_olddrv_death": [round(v, 2) for v in stats.spearmanr(b["bus_board_pc"], b["olddrv_death_per100k65_2y"])],
                 "spearman_bus_vs_wait": [round(v, 2) for v in stats.spearmanr(b["bus_board_pc"], b["duribal_wait_med"])],
                 "n": int(len(b))}

# ------------------------------------------------------------------ 5. 보행노인 사고다발지역 × 노인보호구역(부산)
z = pd.read_csv(KR / "KoROAD_frequentzoneOldman_2023_2025.csv", dtype=str, encoding="utf-8-sig")
for c in ["lo_crd", "la_crd", "occrrnc_cnt", "dth_dnv_cnt"]:
    z[c] = pd.to_numeric(z[c], errors="coerce")
z["sido"] = z["sido_sgg_nm"].str.split().str[0].str.replace(r"\d+$", "", regex=True)
z["sgg"] = z["sido_sgg_nm"].str.replace(r"\d+$", "", regex=True).str.split(n=1).str[1].str.replace(" ", "")
zb = z[z["sido"] == "부산"].copy()
zz = pd.concat([read_any(p, dtype=str) for p in glob.glob(str(BW / "15034532_*/*.csv"))])
zz["lat"], zz["lon"] = pd.to_numeric(zz["위도"]), pd.to_numeric(zz["경도"])


def hav(lat1, lon1, lat2, lon2):
    p1, p2 = np.radians(lat1), np.radians(lat2)
    h = np.sin((p2 - p1) / 2) ** 2 + np.cos(p1) * np.cos(p2) * np.sin(np.radians(lon2 - lon1) / 2) ** 2
    return 2 * 6371000 * np.arcsin(np.sqrt(h))


covered = set(zz["시군구명"])
zc = zb[zb["sgg"].isin(covered)].copy()
zc["d_zone"] = [hav(r.la_crd, r.lo_crd, zz["lat"].values, zz["lon"].values).min() for r in zc.itertuples()]
R["ped_hotspots"] = {"national": int(len(z)), "busan": int(len(zb)), "busan_share": round(len(zb) / len(z) * 100, 1),
                     "by_year": z.groupby("req_year").size().to_dict(),
                     "busan_in_zone_gu": int(len(zc)), "zone_gu": sorted(covered), "n_zones": int(len(zz)),
                     "within_300m": int((zc["d_zone"] <= 300).sum()), "within_300m_share": round(float((zc["d_zone"] <= 300).mean() * 100), 1),
                     "median_dist_m": int(zc["d_zone"].median()),
                     # 자료는 연도별 지정 기록(2023~2025)이라 같은 지점이 여러 해 반복될 수 있음 → 같은 좌표를 하나로 센 참고값
                     "national_unique_xy": int(z[["lo_crd", "la_crd"]].drop_duplicates().shape[0]),
                     "busan_unique_xy": int(zb[["lo_crd", "la_crd"]].drop_duplicates().shape[0])}

# ------------------------------------------------------------------ 6. 65세 이상 인구 전망(통계청 장래인구추계, 중위)
x = pd.read_excel(sorted(glob.glob(str(ROOT / "data" / "raw" / "kosis_projection" / "*.xlsx")))[0], header=None)
hdr = x.iloc[0].tolist()
blk = x.iloc[1:24].copy()
blk.columns = hdr
blk = blk.set_index("연령별")
yrs = [c for c in hdr if str(c).isdigit()]
p65p = blk.loc[["65 - 69세", "70 - 74세", "75 - 79세", "80세이상"], yrs].astype(float).sum()
p75p = blk.loc[["75 - 79세", "80세이상"], yrs].astype(float).sum()
totp = blk.loc["계", yrs].astype(float)
nat_rate = float(s["r65_2024"].sum() / s["p65_2024"].sum() * 1000)   # 02와 같은 정의(전국 2024 반납 / 2024.6 65세 이상)
R["projection"] = {str(y): {"p65_10k": round(p65p[y] / 1e4, 1), "share65": round(p65p[y] / totp[y] * 100, 1), "p75_10k": round(p75p[y] / 1e4, 1)}
                   for y in (2025, 2030, 2035, 2040)}
R["projection"]["returns_2035_at_2024_rate"] = int(round(nat_rate * p65p[2035] / 1000, -2))
R["projection"]["returns_2024"] = int(s["r65_2024"].sum())
R["projection"]["growth_p65_2025_2035_pct"] = round((p65p[2035] / p65p[2025] - 1) * 100, 1)

# ------------------------------------------------------------------ 그림 5
fig, axes = plt.subplots(1, 2, figsize=(9.6, 3.6), gridspec_kw={"width_ratios": [1, 1.25]})
ax = axes[0]
ax.plot(ym.index, ym["share"], color=BLUE, marker="o", ms=3.5, lw=1.8)
for yv in (2014, 2019, 2024):
    ax.annotate(f"{ym.loc[yv, 'share']:.1f}%", (yv, ym.loc[yv, "share"]), xytext=(0, 6), textcoords="offset points", ha="center", fontsize=8.5)
ax.set_ylim(20, 38)
ax.set_xticks([2014, 2016, 2018, 2020, 2022, 2024])
ax.set_ylabel("승차 중 무임 비중(%)")
ax.set_title("(가) 부산 도시철도 승차 중 무임(경로 등) 비중", loc="left", fontsize=9.5)
ax = axes[1]
bb = b.dropna(subset=["duribal_wait_med"]).sort_values("duribal_wait_med")
colr = [ACCENT if g == low["sgg"] else MUTED for g in bb["sgg"]]
ax.barh(bb["sgg"], bb["duribal_wait_med"], color=colr, height=0.7)
for yv, (w, un) in enumerate(zip(bb["duribal_wait_med"], bb["duribal_unserved"])):
    ax.text(w + 0.6, yv, f"{w:.0f}분 · 미배차 {un:.0f}%", va="center", fontsize=7)
ax.set_xlim(0, bb["duribal_wait_med"].max() * 1.45)
ax.tick_params(axis="y", labelsize=7.5)
ax.set_xlabel("접수→승차 대기시간 중위값(분, 즉시 호출)")
ax.set_title(f"(나) 두리발(교통약자 특별교통수단) 구군별 대기·미배차 — 2025.5\n시 전체 {R['duribal']['requests']:,}건, 대기 중위 {R['duribal']['wait_median_min']:.0f}분, 미배차 {R['duribal']['unserved_rate']}%", loc="left", fontsize=9.5)
fig.suptitle(f"그림 5. 부산 사례: 노인의 도시철도 의존은 커졌고, 기존 수요응답형 교통은 호출 뒤 {R['duribal']['wait_median_min']:.0f}분(중위)을 기다린다", x=0.01, ha="left",
             fontweight="bold", fontsize=10.5)
fig.text(0.01, 0.005, "자료: 부산교통공사 월별 역별 권종별 승하차(2014~2024), 부산시설공단 교통약자 이동지원 차량 운영현황(2025.5) — 부산광역시 Big-데이터웨이브. "
         "무임에는 장애인·유공자 포함. 대기시간은 하차까지 완료된 즉시 호출 기준. 빨강 = 1인당 버스 승차가 가장 적은 구.", fontsize=6.2, color=MUTED)
fig.tight_layout(rect=(0, 0.03, 1, 0.93))
fig.savefig(FIG / "fig5_busan_case.png")
plt.close(fig)

(OUTD / "results_busan.json").write_text(json.dumps(R, ensure_ascii=False, indent=1, default=float), encoding="utf-8")
print(json.dumps(R, ensure_ascii=False, indent=1, default=float))
