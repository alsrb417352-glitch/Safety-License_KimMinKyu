"""분석·시각화. 입력: data/processed/*.csv, data/raw(정류장 좌표)  출력: outputs/figures/*.png, outputs/tables/*.csv, outputs/results.json

분석 내용
 1) 연령별 교통사고 사망률(2025)
 2) 고령운전자 면허 자진반납 추이(2015~2024)와 시도별 반납률 격차 — 대중교통 이용과의 관계
 3) 시군구 버스 이용 5분위별 교통사고 사망률(2025)·노인 교통사고 사망률(2018)
 4) 음이항 회귀(인구 offset): 사망자수 ~ 고령비율 + log(1인당 버스승차) + 지역유형 (+ 주행거리)
 5) '이동 사각지대' 시군구 유형화와 지도
 6) 반납률 격차 해소 시나리오: 추가 반납 → 회피 주행거리·CO2 (가정 범위 명시)
"""
from __future__ import annotations

import json
import re
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import statsmodels.api as sm
import statsmodels.formula.api as smf
from matplotlib import font_manager
from scipy import stats

import os

ROOT = Path(__file__).resolve().parent.parent
POP_SOURCE = os.environ.get("POP_SOURCE", "kosis")
SUFFIX = "" if POP_SOURCE == "kosis" else f"_{POP_SOURCE}"
POP_LABEL = "주민등록인구(2025.6, KOSIS API)" if POP_SOURCE == "kosis" else "주민등록인구(2026.9)"
PROC = ROOT / "data" / f"processed{SUFFIX}"
RAW = ROOT / "data" / "raw"
OUTD = ROOT / f"outputs{SUFFIX}"
FIG = OUTD / "figures"
TAB = OUTD / "tables"
FIG.mkdir(parents=True, exist_ok=True)
TAB.mkdir(parents=True, exist_ok=True)

for fp in font_manager.findSystemFonts():
    if "NotoSansCJK" in fp and ("Regular" in fp or "Medium" in fp):
        font_manager.fontManager.addfont(fp)
plt.rcParams.update({"font.family": "Noto Sans CJK JP", "axes.unicode_minus": False, "figure.dpi": 150, "savefig.dpi": 200,
                     "axes.spines.top": False, "axes.spines.right": False, "axes.titleweight": "bold", "font.size": 10})
for name in ("Noto Sans CJK KR", "Noto Sans CJK JP", "Noto Sans CJK TC"):
    if any(name == f.name for f in font_manager.fontManager.ttflist):
        plt.rcParams["font.family"] = name
        break

INK = "#1f2937"
MUTED = "#9ca3af"
ACCENT = "#d6453d"   # 위험·사각지대
BLUE = "#2563eb"     # 대중교통
ORANGE = "#f59e0b"
GREEN = "#10b981"
R: dict = {}

d = pd.read_csv(PROC / "sigungu_panel.csv")
s = pd.read_csv(PROC / "sido_panel.csv")
age = pd.read_csv(PROC / "age_deaths_2025.csv")

# ------------------------------------------------------------------ 1. 연령별 사망률
age = age[age["사상자연령층"] != "불명"].copy()
order = ["12세이하", "13-20세", "21-30세", "31-40세", "41-50세", "51-60세", "61-64세", "65세이상"]
age["o"] = age["사상자연령층"].map({k: i for i, k in enumerate(order)})
age = age.sort_values("o")
tot_death = int(pd.read_csv(PROC / "age_deaths_2025.csv")["사망자수"].sum())
d65 = int(age.loc[age["사상자연령층"] == "65세이상", "사망자수"].iloc[0])
pop_all = age["pop_denom"].sum()
p65 = float(age.loc[age["사상자연령층"] == "65세이상", "pop_denom"].iloc[0])
R["age"] = {"total_deaths_2025": tot_death, "deaths_65plus": d65, "share_deaths_65plus": round(d65 / tot_death * 100, 1),
            "share_pop_65plus": round(p65 / pop_all * 100, 1),
            "rate_65plus": round(float(age.loc[age["사상자연령층"] == "65세이상", "death_per100k"].iloc[0]), 2),
            "rate_under65": round(float(age.loc[age["사상자연령층"] != "65세이상", "사망자수"].sum() / age.loc[age["사상자연령층"] != "65세이상", "pop_denom"].sum() * 1e5), 2)}
R["age"]["ratio_65_vs_under65"] = round(R["age"]["rate_65plus"] / R["age"]["rate_under65"], 2)

fig, ax = plt.subplots(figsize=(6.4, 3.2))
cols = [ACCENT if a == "65세이상" else MUTED for a in age["사상자연령층"]]
ax.bar(age["사상자연령층"], age["death_per100k"], color=cols, width=0.7)
for x, v in zip(age["사상자연령층"], age["death_per100k"]):
    ax.text(x, v + 0.25, f"{v:.1f}", ha="center", va="bottom", fontsize=8.5, color=INK)
ax.set_ylabel("인구 10만 명당 사망자(명)")
ax.set_title("그림 1. 연령대별 교통사고 사망률(2025)", loc="left")
ax.text(0.02, 0.95, f"65세 이상: 사망자의 {R['age']['share_deaths_65plus']}% (인구 비중 {R['age']['share_pop_65plus']}%)\n"
        f"사망률 {R['age']['rate_65plus']:.1f}명 = 65세 미만({R['age']['rate_under65']:.1f}명)의 {R['age']['ratio_65_vs_under65']:.1f}배",
        transform=ax.transAxes, ha="left", va="top", fontsize=8.5, color=ACCENT)
ax.set_ylim(0, age["death_per100k"].max() * 1.25)
ax.tick_params(axis="x", labelsize=8.5)
fig.text(0.01, 0.005, "자료: 한국도로교통공단 사상자 연령층별 교통사고(2025), 행정안전부 " + POP_LABEL + ("." if POP_SOURCE == "kosis" else ". 분모 시점 차이 있음."), fontsize=6.5, color=MUTED)
fig.tight_layout(rect=(0, 0.03, 1, 1))
fig.savefig(FIG / "fig1_age_death_rate.png")
plt.close(fig)

# ------------------------------------------------------------------ 2. 면허 반납 추이와 시도 격차
yrs = list(range(2015, 2025))
nat = [int(s[f"r65_{y}"].sum()) for y in yrs]
R["returns"] = {"by_year_65plus": dict(zip(yrs, nat))}
nat_rate_2024 = s["r65_2024"].sum() / s["p65_2024"].sum() * 1000   # 시도 반납률과 같은 분모(2024.6 65세 이상)
R["returns"]["national_rate_2024_per1k65"] = round(nat_rate_2024, 2)
s2 = s[s["sido"] != "세종"].copy()  # 세종: 고령인구 규모가 작고 신도시 특성 — 산점도 표시에서만 별도 주석
rho, p_rho = stats.spearmanr(s["bus_board_pc"], s["return_rate_2024_per1k65"])
rho_d, p_d = stats.spearmanr(s["death_per100k"], s["return_rate_2024_per1k65"])
R["returns"].update({"spearman_bus_vs_return": [round(rho, 2), round(p_rho, 4)], "spearman_death_vs_return": [round(rho_d, 2), round(p_d, 4)],
                     "max": s.loc[s["return_rate_2024_per1k65"].idxmax(), ["sido", "return_rate_2024_per1k65"]].tolist(),
                     "min": s.loc[s["return_rate_2024_per1k65"].idxmin(), ["sido", "return_rate_2024_per1k65"]].tolist()})
R["returns"]["gap_ratio_max_min"] = round(R["returns"]["max"][1] / R["returns"]["min"][1], 2)
fig, axes = plt.subplots(1, 2, figsize=(9.6, 3.6), gridspec_kw={"width_ratios": [1, 1.25]})
ax = axes[0]
ax.bar([str(y)[2:] for y in yrs], [v / 1000 for v in nat], color=[MUTED] * 9 + [BLUE])
ax.set_title("(가) 65세 이상 면허 자진반납 건수", loc="left", fontsize=10)
ax.set_ylabel("천 건")
ax.set_xlabel("연도(20XX)")
for i, v in enumerate(nat):
    if i in (0, 4, 9):
        ax.text(i, v / 1000 + 2, f"{v/1000:.1f}", ha="center", fontsize=8)
ax = axes[1]
x = s["bus_board_pc"]
y = s["return_rate_2024_per1k65"]
sz = s["p65"] / 8000
ax.scatter(x, y, s=sz, color=BLUE, alpha=0.55, edgecolor="white", linewidth=0.8)
OFF = {"세종": (-22, -11), "광주": (5, 3), "충남": (5, 5), "충북": (5, -10), "경북": (-24, 6), "제주": (-22, 5), "인천": (5, 4),
       "경기": (6, 2), "전북": (-24, 4), "강원": (5, 4)}
for _, r in s.iterrows():
    ax.annotate(r["sido"], (r["bus_board_pc"], r["return_rate_2024_per1k65"]), fontsize=8, xytext=OFF.get(r["sido"], (4, 2)),
                textcoords="offset points", color=INK)
ax.axhline(nat_rate_2024, color=MUTED, lw=0.8, ls="--")
ax.text(x.max(), nat_rate_2024 + 0.15, f"전국 {nat_rate_2024:.1f}", ha="right", fontsize=8, color=MUTED)
ax.set_xlabel("1인당 하루 버스 승차(교통카드, 2025)")
ax.set_ylabel("65세 이상 1천 명당 반납(2024)")
ax.set_title(f"(나) 시도별 반납률과 버스 이용 (스피어만 ρ={rho:.2f}, p={p_rho:.3f})", loc="left", fontsize=10)
fig.suptitle("그림 2. 면허 반납은 늘었지만, 대중교통이 부족한 지역에서는 적게 반납한다", x=0.01, ha="left", fontweight="bold", fontsize=11)
fig.text(0.01, 0.005, "자료: 경찰청 시도별 고령운전자 자진반납 현황(2015~2024), 국토교통부 시군구별 정류장 평균이용량(2025), 행정안전부 " + ("주민등록인구(2024.6, KOSIS API)" if POP_SOURCE == "kosis" else "주민등록인구(2026.9)") + ". 원 크기=65세 이상 인구.",
         fontsize=6.5, color=MUTED)
fig.tight_layout(rect=(0, 0.03, 1, 0.95))
fig.savefig(FIG / "fig2_license_return.png")
plt.close(fig)

# ------------------------------------------------------------------ 3. 버스 이용 5분위별 사망률
dd = d.dropna(subset=["bus_board_pc"]).copy()
dd["q_bus"] = pd.qcut(dd["bus_board_pc"], 5, labels=["1분위\n(최저)", "2분위", "3분위", "4분위", "5분위\n(최고)"])
g = dd.groupby("q_bus", observed=True).agg(n=("sgg", "size"), bus_med=("bus_board_pc", "median"), share65_med=("share65", "median"),
                                           deaths=("사망자수", "sum"), pop=("pop", "sum"), p65=("p65", "sum"), old_d=("old_death_2018", "sum"),
                                           old_d25=("lg_old_death_2025", "sum"), od_acc=("lg_olddrv_acc_2025", "sum"),
                                           od_d=("lg_olddrv_death_2025", "sum"),
                                           gun=("region_type", lambda v: int((v == "군").sum())))
g["death_rate"] = g["deaths"] / g["pop"] * 1e5
g["old_death_rate"] = g["old_d"] / g["p65"] * 1e5                 # 2018 사고(참고용)
g["old_death_rate_2025"] = g["old_d25"] / g["p65"] * 1e5          # 65세 이상 사망자(2025)
g["olddrv_acc_rate"] = g["od_acc"] / g["p65"] * 1000               # 고령운전자 가해 사고, 65세 이상 1천 명당
g["olddrv_death_rate"] = g["od_d"] / g["p65"] * 1e5                # 고령운전자 가해 사고 사망자, 65세 이상 10만 명당
g["olddrv_cfr"] = g["od_d"] / g["od_acc"] * 100                     # 사고 100건당 사망자(치사율)
g["olddrv_death_share"] = g["od_d"] / g["deaths"] * 100
g.to_csv(TAB / "table_bus_quintiles.csv", encoding="utf-8-sig")
R["quintiles"] = {"death_rate": g["death_rate"].round(4).tolist(), "old_death_rate_2018": g["old_death_rate"].round(4).tolist(),
                  "old_death_rate_2025": g["old_death_rate_2025"].round(4).tolist(),
                  "olddrv_acc_rate": g["olddrv_acc_rate"].round(4).tolist(), "olddrv_death_rate": g["olddrv_death_rate"].round(4).tolist(),
                  "olddrv_cfr": g["olddrv_cfr"].round(4).tolist(), "olddrv_death_share": g["olddrv_death_share"].round(1).tolist(),
                  "ratio_q1_q5": round(g["death_rate"].iloc[0] / g["death_rate"].iloc[-1], 2),
                  "ratio_old_q1_q5": round(g["old_death_rate"].iloc[0] / g["old_death_rate"].iloc[-1], 2),
                  "ratio_old2025_q1_q5": round(g["old_death_rate_2025"].iloc[0] / g["old_death_rate_2025"].iloc[-1], 2),
                  "ratio_olddrv_death_q1_q5": round(g["olddrv_death_rate"].iloc[0] / g["olddrv_death_rate"].iloc[-1], 2),
                  "ratio_olddrv_acc_q1_q5": round(g["olddrv_acc_rate"].iloc[0] / g["olddrv_acc_rate"].iloc[-1], 2),
                  "ratio_olddrv_cfr_q1_q5": round(g["olddrv_cfr"].iloc[0] / g["olddrv_cfr"].iloc[-1], 2),
                  "pop_share_q1q2": round(g["pop"].iloc[:2].sum() / g["pop"].sum() * 100, 1),
                  "death_share_q1q2": round(g["deaths"].iloc[:2].sum() / g["deaths"].sum() * 100, 1),
                  "n_sgg": int(g["n"].sum()), "deaths_sgg": int(g["deaths"].sum()),
                  "n": g["n"].tolist(), "gun_count": g["gun"].tolist(), "bus_median": g["bus_med"].round(3).tolist()}
fig, axes = plt.subplots(1, 2, figsize=(9.6, 3.5))
ax = axes[0]
bars = ax.bar(g.index.astype(str), g["death_rate"], color=[ACCENT, ACCENT, MUTED, MUTED, BLUE], width=0.65)
for b, v in zip(bars, g["death_rate"]):
    ax.text(b.get_x() + b.get_width() / 2, v + g["death_rate"].max() * 0.02, f"{v:.1f}", ha="center", fontsize=8.5)
ax.set_title("(가) 전체 교통사고 사망률(2025)\n인구 10만 명당", loc="left", fontsize=9.5)
ax.set_xlabel("시군구 1인당 버스 승차 5분위")
ax = axes[1]
DRV = "#7f1d1d"
bars = ax.bar(g.index.astype(str), g["olddrv_death_rate"], color=[DRV, DRV, MUTED, MUTED, BLUE], width=0.65)
for b, v, a in zip(bars, g["olddrv_death_rate"], g["olddrv_acc_rate"]):
    ax.text(b.get_x() + b.get_width() / 2, v + g["olddrv_death_rate"].max() * 0.02, f"{v:.1f}", ha="center", fontsize=8.5)
    ax.text(b.get_x() + b.get_width() / 2, -g["olddrv_death_rate"].max() * 0.20, f"사고 {a:.1f}건", ha="center", fontsize=7.2, color="#6b7280")
ax.set_ylim(-g["olddrv_death_rate"].max() * 0.26, g["olddrv_death_rate"].max() * 1.12)
ax.axhline(0, color="#d1d5db", lw=0.8)
ax.set_title("(나) 고령운전자(65세+) 가해 사고 사망자(2025)\n65세 이상 10만 명당 · 회색 = 65세 이상 1천 명당 사고 건수", loc="left", fontsize=9.5)
ax.set_xlabel("시군구 1인당 버스 승차 5분위", labelpad=2)
ax.set_yticks([t for t in ax.get_yticks() if t >= 0])
fig.suptitle(f"그림 3. 버스 이용 하위 20% 시군구: 교통사고 사망률 {R['quintiles']['ratio_q1_q5']:.1f}배, "
             f"고령운전자 사고 사망 {R['quintiles']['ratio_olddrv_death_q1_q5']:.1f}배(사고 건수는 비슷)", x=0.01, ha="left",
             fontweight="bold", fontsize=10.5)
fig.text(0.01, 0.005, "자료: 한국도로교통공단 시군구별 교통사고(2025)·지자체별 대상 교통사고 통계(2025, OpenAPI), 국토교통부 정류장 평균이용량(2025), " + POP_LABEL + ". "
         "교통카드 자료가 없는 4개 군 제외(n=223).", fontsize=6.3, color=MUTED)
fig.tight_layout(rect=(0, 0.03, 1, 0.93))
fig.savefig(FIG / "fig3_bus_quintile_deaths.png")
plt.close(fig)

# ------------------------------------------------------------------ 4. 회귀
dd["lbus"] = np.log(dd["bus_board_pc"])
dd["log_pop"] = np.log(dd["pop"])
models = {}
f1 = "사망자수 ~ share65 + lbus + C(region_type, Treatment('시'))"
m1 = smf.glm(f1, data=dd, family=sm.families.NegativeBinomial(alpha=0.1), offset=dd["log_pop"]).fit()
nb = smf.negativebinomial(f1, data=dd, offset=dd["log_pop"]).fit(disp=0)
d3 = dd.dropna(subset=["vkt_car_private"])
f2 = "사망자수 ~ share65 + lbus + vkt_car_private + C(region_type, Treatment('시'))"
nb2 = smf.negativebinomial(f2, data=d3, offset=np.log(d3["pop"])).fit(disp=0)
# 모형3: 고령운전자 가해 사고 사망자(2025) — 65세 이상 인구 offset. 대중교통이 고령운전 위험과 따로 관련되는지 확인
f3 = "lg_olddrv_death_2025 ~ share65 + lbus + vkt_car_private + C(region_type, Treatment('시'))"
d4 = d3.dropna(subset=["lg_olddrv_death_2025"])
nb3 = smf.negativebinomial(f3, data=d4, offset=np.log(d4["p65"])).fit(disp=0)
rows = []
for name, mdl in [("모형1", nb), ("모형2(+주행거리)", nb2), ("모형3(고령운전자 사고 사망)", nb3)]:
    ci = mdl.conf_int()
    for k in mdl.params.index:
        if k == "alpha":
            continue
        rows.append({"model": name, "term": k, "coef": mdl.params[k], "IRR": np.exp(mdl.params[k]), "IRR_lo": np.exp(ci.loc[k, 0]),
                     "IRR_hi": np.exp(ci.loc[k, 1]), "p": mdl.pvalues[k], "n": int(mdl.nobs), "pseudo_R2": mdl.prsquared})
reg = pd.DataFrame(rows)
reg.to_csv(TAB / "table_regression_nb.csv", index=False, encoding="utf-8-sig")
R["regression"] = {r["model"] + ":" + r["term"]: {"IRR": round(r["IRR"], 3), "CI": [round(r["IRR_lo"], 3), round(r["IRR_hi"], 3)], "p": round(r["p"], 4)}
                   for r in rows}
R["regression_n"] = {"모형1": int(nb.nobs), "모형2": int(nb2.nobs), "모형3": int(nb3.nobs)}
# 상관 행렬(설명용)
R["spearman_sigungu"] = d[["share65", "bus_board_pc", "vkt_car_private", "death_per100k", "old_death_per100k65_2025", "olddrv_death_per100k65"]].corr(method="spearman").round(2).to_dict()

# ------------------------------------------------------------------ 5. 이동 사각지대 유형화
t65 = d["share65"].quantile(2 / 3)
tbus = d["bus_board_pc"].quantile(1 / 3)
tdeath = d["death_per100k"].quantile(2 / 3)
d["c_aging"] = d["share65"] >= t65
d["c_transit_gap"] = (d["bus_board_pc"] <= tbus) | d["bus_board_pc"].isna()
d["c_risk"] = d["death_per100k"] >= tdeath
d["n_cond"] = d[["c_aging", "c_transit_gap", "c_risk"]].sum(axis=1)
d["blindspot"] = np.where(d["n_cond"] == 3, "3중 사각지대", np.where(d["n_cond"] == 2, "2중", "기타"))
d.loc[d["bus_board_pc"].isna(), "bus_note"] = "교통카드 정류장 자료 없음(공백으로 분류)"
bl = d[d["n_cond"] == 3].sort_values("death_per100k", ascending=False)
cols_out = ["sido", "sgg", "region_type", "pop", "p65", "share65", "bus_board_pc", "death_per100k", "사망자수", "lg_olddrv_death_2025", "olddrv_death_per100k65", "vkt_car_private", "bus_note"]
bl[cols_out].to_csv(TAB / "table_blindspots.csv", index=False, encoding="utf-8-sig")
d.to_csv(PROC / "sigungu_panel_classified.csv", index=False, encoding="utf-8-sig")
R["blindspots"] = {"thresholds": {"share65_top_tertile": round(t65, 2), "bus_board_pc_bottom_tertile": round(tbus, 4),
                                  "death_per100k_top_tertile": round(tdeath, 2)},
                   "n_triple": int((d["n_cond"] == 3).sum()), "n_double": int((d["n_cond"] == 2).sum()),
                   "pop_triple": int(bl["pop"].sum()), "p65_triple": int(bl["p65"].sum()),
                   "deaths_triple": int(bl["사망자수"].sum()), "death_share_triple": round(bl["사망자수"].sum() / d["사망자수"].sum() * 100, 1),
                   "pop_share_triple": round(bl["pop"].sum() / d["pop"].sum() * 100, 1),
                   "death_rate_triple": round(bl["사망자수"].sum() / bl["pop"].sum() * 1e5, 2),
                   "death_rate_rest": round(d.loc[d["n_cond"] < 3, "사망자수"].sum() / d.loc[d["n_cond"] < 3, "pop"].sum() * 1e5, 2),
                   "by_sido": bl.groupby("sido").size().sort_values(ascending=False).to_dict(),
                   "top10": bl[["sido", "sgg", "share65", "bus_board_pc", "death_per100k"]].head(10).round(3).values.tolist()}
# 민감도: 교통카드 정류장 자료가 없는 군을 '공백'으로 간주하지 않으면(관측값으로 확인된 곳만)
bl_obs = bl[bl["bus_board_pc"].notna()]
R["blindspots"]["observed_only"] = {
    "n": int(len(bl_obs)), "nobus": bl.loc[bl["bus_board_pc"].isna(), ["sido", "sgg"]].values.tolist(),
    "pop_share": round(bl_obs["pop"].sum() / d["pop"].sum() * 100, 1),
    "death_share": round(bl_obs["사망자수"].sum() / d["사망자수"].sum() * 100, 1)}
# 고령운전자 가해 사고(2025, 도로교통공단 API)로 본 사각지대 — 분류 기준(전체 사망률)과 겹치는 부분이 있어 '규모' 지표로 해석
rest = d[d["n_cond"] < 3]
R["blindspots"]["olddrv"] = {
    "p65_share_triple": round(bl["p65"].sum() / d["p65"].sum() * 100, 1),
    "olddrv_death_share_of_national": round(bl["lg_olddrv_death_2025"].sum() / d["lg_olddrv_death_2025"].sum() * 100, 1),
    "olddrv_deaths_triple": int(bl["lg_olddrv_death_2025"].sum()),
    "olddrv_death_rate_triple": round(bl["lg_olddrv_death_2025"].sum() / bl["p65"].sum() * 1e5, 2),
    "olddrv_death_rate_rest": round(rest["lg_olddrv_death_2025"].sum() / rest["p65"].sum() * 1e5, 2),
    "olddrv_acc_rate_triple": round(bl["lg_olddrv_acc_2025"].sum() / bl["p65"].sum() * 1000, 2),
    "olddrv_acc_rate_rest": round(rest["lg_olddrv_acc_2025"].sum() / rest["p65"].sum() * 1000, 2),
    "olddrv_share_of_deaths_triple": round(bl["lg_olddrv_death_2025"].sum() / bl["사망자수"].sum() * 100, 1),
    "olddrv_share_of_deaths_rest": round(rest["lg_olddrv_death_2025"].sum() / rest["사망자수"].sum() * 100, 1),
    "olddrv_deaths_2024_triple": int(bl["lg_olddrv_death_2024"].sum()),
}
_rt = d.groupby("region_type")[["lg_olddrv_death_2025", "사망자수", "p65", "lg_olddrv_acc_2025"]].sum()
R["olddrv_by_region_type"] = {k: {"share_of_deaths": round(v["lg_olddrv_death_2025"] / v["사망자수"] * 100, 1),
                                  "death_per100k65": round(v["lg_olddrv_death_2025"] / v["p65"] * 1e5, 2),
                                  "acc_per1k65": round(v["lg_olddrv_acc_2025"] / v["p65"] * 1000, 2)} for k, v in _rt.iterrows()}
R["olddrv_national"] = {"deaths_2025": int(d["lg_olddrv_death_2025"].sum()), "deaths_2024": int(d["lg_olddrv_death_2024"].sum()),
                        "acc_2025": int(d["lg_olddrv_acc_2025"].sum()), "acc_2024": int(d["lg_olddrv_acc_2024"].sum()),
                        "old_deaths_2025": int(d["lg_old_death_2025"].sum()),
                        "sgg_matched": int(d["lg_all_death_2025"].notna().sum()),
                        "sgg_death_match_file": int((d["lg_all_death_2025"] == d["사망자수"]).sum())}
# 시도: 반납률(2024)과 고령운전자 사고율(2024, 65세 이상 1천 명당)
rho_o, p_o = stats.spearmanr(s["return_rate_2024_per1k65"], s["olddrv_death_per100k65_2024"])
rho_oa, p_oa = stats.spearmanr(s["return_rate_2024_per1k65"], s["olddrv_acc_per1k65_2024"])
R["returns"]["spearman_return_vs_olddrv_death_2024"] = [round(rho_o, 2), round(p_o, 4)]
R["returns"]["spearman_return_vs_olddrv_acc_2024"] = [round(rho_oa, 2), round(p_oa, 4)]

# 지도: 버스정류장 좌표(TAGO 2025)를 점으로 찍어 국토 형상 표현, 사각지대 시군구의 정류장을 강조
idx = json.loads((RAW / "index.json").read_text(encoding="utf-8"))
F = {i["name"]: RAW / i["file"] for i in idx}
stops = pd.read_csv(F["2025정류장현황(EUCKR)_20251209.csv"], dtype=str, usecols=["위도", "경도", "도시명"])
stops["lat"] = pd.to_numeric(stops["위도"], errors="coerce")
stops["lon"] = pd.to_numeric(stops["경도"], errors="coerce")
stops = stops[(stops["lat"].between(33, 39)) & (stops["lon"].between(124, 132))]
SIDO_FULL = {"서울특별시": "서울", "부산광역시": "부산", "대구광역시": "대구", "인천광역시": "인천", "광주광역시": "광주", "대전광역시": "대전",
             "울산광역시": "울산", "세종특별자치시": "세종", "경기도": "경기", "강원특별자치도": "강원", "강원도": "강원", "충청북도": "충북",
             "충청남도": "충남", "전북특별자치도": "전북", "전라북도": "전북", "전라남도": "전남", "경상북도": "경북", "경상남도": "경남",
             "제주특별자치도": "제주"}
def split_city(n):
    parts = str(n).split()
    sido = SIDO_FULL.get(parts[0], parts[0]) if parts else None
    sgg = re.sub(r"\s+", "", parts[1]) if len(parts) > 1 else None
    return sido, sgg
sp = stops["도시명"].map(split_city)
stops["sido"] = [a for a, b in sp]
stops["sgg"] = [b for a, b in sp]
stops = stops.merge(d[["sido", "sgg", "blindspot", "n_cond"]], on=["sido", "sgg"], how="left")
fig, ax = plt.subplots(figsize=(5.6, 6.6))
base = stops[stops["n_cond"].fillna(0) < 2]
ax.scatter(base["lon"], base["lat"], s=0.15, color="#cbd5e1", linewidths=0, rasterized=True, label="그 외(조건 1개 이하, 또는 특별·광역시라 구별 미분류)")
two = stops[stops["n_cond"] == 2]
ax.scatter(two["lon"], two["lat"], s=0.35, color=ORANGE, linewidths=0, rasterized=True, label="2중(고령화·대중교통 공백·사망률 중 2개)")
three = stops[stops["n_cond"] == 3]
ax.scatter(three["lon"], three["lat"], s=0.45, color=ACCENT, linewidths=0, rasterized=True, label="3중 이동 사각지대")
ax.set_aspect(1.2)
ax.set_xlim(125.0, 130.0)
ax.set_ylim(33.1, 38.7)
ax.axis("off")
lg = ax.legend(loc="lower right", markerscale=18, fontsize=8, frameon=False)
ax.set_title(f"그림 4. 이동 사각지대 시군구({R['blindspots']['n_triple']}곳)의 버스정류장 분포", loc="left", fontsize=10.5)
fig.text(0.02, 0.01, "점 = 버스정류장 1개(국토교통부 전국 버스정류장 위치정보 2025, TAGO 연계 지역).\n"
         "3중 = 65세 이상 비율 상위 1/3 + 1인당 버스 승차 하위 1/3(교통카드 자료가 없는 군은 공백으로 간주) + 인구 10만 명당 사망 상위 1/3.\n"
         "특별·광역시는 TAGO 도시명이 시 단위라 구별 구분이 표시되지 않음.", fontsize=6.3, color=MUTED)
fig.tight_layout(rect=(0, 0.05, 1, 1))
fig.savefig(FIG / "fig4_blindspot_map.png")
plt.close(fig)
R["map_note"] = {"stops_plotted": int(len(stops)), "stops_in_triple": int(len(three)), "stops_unmatched_city": int(stops["n_cond"].isna().sum())}

# ------------------------------------------------------------------ 6. 시나리오: 반납률 격차 해소 → 회피 주행거리·CO2
# 가정(보고서에 명시): (A) 전국 평균 미만 시도가 전국 평균 반납률(2024)에 도달,
# (B) 반납자 1명당 회피 승용차 주행 = 해당 시도 비사업용 승용차 대당 일평균 주행거리(2019)의 30~70%(중앙 50%),
# (C) 배출계수 0.15~0.21 kgCO2/km(중앙 0.18) — IPCC 2006 휘발유 기본계수(69,300 kgCO2/TJ)와 실도로 연비 범위(11~15 km/L)로 환산한 가정치,
# (D) 대체 이동수단(DRT·택시 등)의 배출은 차감하지 않은 총량(gross) — 순감축은 더 작음.
vk_sido = d.groupby("sido").apply(lambda x: np.average(x["vkt_car_private"].dropna(), weights=x.loc[x["vkt_car_private"].notna(), "pop"])
                                  if x["vkt_car_private"].notna().any() else np.nan, include_groups=False)
s["vkt_car_private"] = s["sido"].map(vk_sido)
s["vkt_car_private"] = s["vkt_car_private"].fillna(d["vkt_car_private"].median())
below = s[s["return_rate_2024_per1k65"] < nat_rate_2024].copy()
below["add_returns"] = (nat_rate_2024 - below["return_rate_2024_per1k65"]) * below["p65_2024"] / 1000
scen = {}
for lab, frac, ef in [("low", 0.3, 0.15), ("mid", 0.5, 0.18), ("high", 0.7, 0.21)]:
    km = (below["add_returns"] * below["vkt_car_private"] * frac * 365).sum()
    scen[lab] = {"avoided_vkm_million": round(km / 1e6, 1), "tCO2": round(km * ef / 1000, 0)}
R["scenario"] = {"sido_below_avg": below["sido"].tolist(), "additional_returns_per_year": int(round(below["add_returns"].sum())),
                 "by_sido": below.set_index("sido")["add_returns"].round(0).astype(int).to_dict(), "range": scen,
                 "assumptions": ["전국 평균 미만 시도가 전국 평균 반납률(2024, 2024.6 65세 이상 인구 기준)에 도달",
                                 "반납자 1인당 회피 승용차 주행 = 시도 비사업용 승용차 대당 일평균 주행거리(2019)의 30/50/70%",
                                 "배출계수 0.15/0.18/0.21 kgCO2/km(가정치, IPCC 2006 휘발유 기본계수와 연비 범위로 환산)",
                                 "대체 이동수단 배출 미차감(총량) — 순감축은 이보다 작음", "1회성 효과가 아니라 연간 흐름(매년 추가 반납분 누적 효과는 미산정)"]}
pd.DataFrame(below[["sido", "p65_2024", "return_rate_2024_per1k65", "add_returns", "vkt_car_private"]]).to_csv(TAB / "table_scenario.csv", index=False, encoding="utf-8-sig")

(OUTD / "results.json").write_text(json.dumps(R, ensure_ascii=False, indent=1, default=float), encoding="utf-8")
print(json.dumps(R, ensure_ascii=False, indent=1, default=float)[:6000])
print(reg.round(3).to_string())
