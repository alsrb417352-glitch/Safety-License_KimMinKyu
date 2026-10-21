"""API 교차검증: 등록 인증키로 받은 API 자료로 보고서 핵심 수치를 다시 확인한다.

1) 분모 시점 검증 — 초안(2026.9 인구 파일) vs KOSIS OpenAPI(2025.6·2024.6 주민등록인구) 결과 비교
2) 공공데이터포털 OpenAPI '지자체별 대상 교통사고 통계'(도로교통공단)로 시군구 사망자·고령 관련 사고 대조

입력: outputs_file2026/results.json(초안 방식), outputs/results.json(KOSIS 방식), data/raw/koroad_api/KoROAD_lgStat_2024_2025.csv
출력: outputs/verification.json, outputs/tables/table_verification.csv
"""
from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
A = json.loads((ROOT / "outputs_file2026" / "results.json").read_text(encoding="utf-8"))
B = json.loads((ROOT / "outputs" / "results.json").read_text(encoding="utf-8"))
build = json.loads((ROOT / "data" / "processed" / "build_log.json").read_text(encoding="utf-8"))

ITEMS = [
    ("65세 이상 인구 비중(%)", ("age", "share_pop_65plus")),
    ("65세 이상 교통사고 사망률(10만 명당)", ("age", "rate_65plus")),
    ("65세 미만 교통사고 사망률(10만 명당)", ("age", "rate_under65")),
    ("65세 이상/미만 사망률 배수", ("age", "ratio_65_vs_under65")),
    ("65세 이상 사망자 비중(%)", ("age", "share_deaths_65plus")),
    ("전국 반납률(65세 이상 1천 명당, 2024)", ("returns", "national_rate_2024_per1k65")),
    ("반납률 최고·최저 배수", ("returns", "gap_ratio_max_min")),
    ("반납률–버스 이용 스피어만 ρ", ("returns", "spearman_bus_vs_return", 0)),
    ("반납률–버스 이용 p", ("returns", "spearman_bus_vs_return", 1)),
    ("버스 이용 1분위/5분위 사망률 배수", ("quintiles", "ratio_q1_q5")),
    ("하위 40% 시군구 사망 비중(%)", ("quintiles", "death_share_q1q2")),
    ("3중 사각지대 시군구 수", ("blindspots", "n_triple")),
    ("3중 사각지대 인구 비중(%)", ("blindspots", "pop_share_triple")),
    ("3중 사각지대 사망 비중(%)", ("blindspots", "death_share_triple")),
    ("시나리오 추가 반납(건/년)", ("scenario", "additional_returns_per_year")),
    ("시나리오 CO₂ 중앙값(톤/년)", ("scenario", "range", "mid", "tCO2")),
]


def get(d, path):
    for p in path:
        d = d[p]
    return d


rows = []
for name, path in ITEMS:
    a, b = get(A, path), get(B, path)
    rows.append({"항목": name, "초안(2026.9 인구 파일)": a, "검증(KOSIS API 2025.6·2024.6)": b,
                 "변화": None if not isinstance(a, (int, float)) else round(b - a, 4)})
T = pd.DataFrame(rows)
(ROOT / "outputs" / "tables").mkdir(parents=True, exist_ok=True)
T.to_csv(ROOT / "outputs" / "tables" / "table_verification.csv", index=False, encoding="utf-8-sig")

kosis_note = next((n for n in build["notes"] if "KOSIS" in n), "")
V = {
    "denominator": {
        "source": "KOSIS OpenAPI 101/DT_1B04006 행정구역(시군구)별/1세별 주민등록인구(총인구수), 2025.6·2024.6",
        "build_note": kosis_note,
        "comparison": rows,
        "conclusions_unchanged": all([
            B["returns"]["spearman_bus_vs_return"][1] < 0.05,
            B["quintiles"]["ratio_q1_q5"] > 3,
            B["blindspots"]["death_share_triple"] > 3 * B["blindspots"]["pop_share_triple"],
            B["age"]["ratio_65_vs_under65"] > 4,
        ]),
    }
}

# ---- KOSIS OpenAPI 132/DT_V_MOTA_021 가해자 연령층별 교통사고(경찰청): 2025 총 사망자 대조 + 고령운전자 추이
MO = ROOT / "data" / "raw_api" / "kosis_mota" / "tbl_01a15d9a412808ad94f23fe8.csv"
if MO.exists():
    mo = pd.read_csv(MO, dtype=str)
    mo["DT"] = pd.to_numeric(mo["DT"])
    mo = mo[mo["C2_NM"] == "전체"]
    pv = mo.pivot_table(index=["PRD_DE", "ITM_NM"], columns="C1_NM", values="DT", aggfunc="sum")
    pv["total"] = pv.sum(axis=1)
    pv["d65"] = pv["65-70세"] + pv["71세이상"]
    yrs = sorted({i[0] for i in pv.index})
    series = {y: {"사고건수_65": int(pv.loc[(y, "사고건수"), "d65"]), "사고건수": int(pv.loc[(y, "사고건수"), "total"]),
                  "사망자수_65": int(pv.loc[(y, "사망자수"), "d65"]), "사망자수": int(pv.loc[(y, "사망자수"), "total"])} for y in yrs}
    age_file = pd.read_csv(ROOT / "data" / "processed" / "age_deaths_2025.csv")
    V["older_drivers"] = {
        "source": "KOSIS OpenAPI 132/DT_V_MOTA_021 가해자 연령층별 교통사고(경찰청), 연간·월 전체, 65세 이상=65-70세+71세이상",
        "series": series,
        "total_deaths_2025_police": series["2025"]["사망자수"],
        "total_deaths_2025_koroad_file": int(age_file["사망자수"].sum()),
        "total_deaths_match": series["2025"]["사망자수"] == int(age_file["사망자수"].sum()),
        "share_deaths_by_65_driver": {y: round(v["사망자수_65"] / v["사망자수"] * 100, 1) for y, v in series.items()},
        "share_acc_by_65_driver": {y: round(v["사고건수_65"] / v["사고건수"] * 100, 1) for y, v in series.items()},
    }
    od = V["older_drivers"]
    print("2025 사망자: 경찰청(KOSIS)", od["total_deaths_2025_police"], "/ 도로교통공단 파일", od["total_deaths_2025_koroad_file"], "일치" if od["total_deaths_match"] else "불일치")
    print("65세+ 운전자 가해 사고 사망 비중:", od["share_deaths_by_65_driver"])

# ---- 공공데이터포털 OpenAPI(도로교통공단 지자체별 대상 교통사고 통계, 15056770) 대조
LG = ROOT / "data" / "raw" / "koroad_api" / "KoROAD_lgStat_2024_2025.csv"
if LG.exists():
    pan = pd.read_csv(ROOT / "data" / "processed" / "sigungu_panel.csv")
    m = pan.dropna(subset=["lg_all_death_2025"])
    n_death = int((m["lg_all_death_2025"] == m["사망자수"]).sum())
    n_acc = int((m["lg_all_acc_2025"] == m["사고건수"]).sum())
    od25 = int(pan["lg_olddrv_death_2025"].sum())
    old25 = int(pan["lg_old_death_2025"].sum())
    age_file = pd.read_csv(ROOT / "data" / "processed" / "age_deaths_2025.csv")
    d65_file = int(age_file.loc[age_file["사상자연령층"] == "65세이상", "사망자수"].iloc[0])
    police_od = V.get("older_drivers", {}).get("series", {}).get("2025", {}).get("사망자수_65")
    V["lgstat"] = {
        "source": "공공데이터포털 OpenAPI 15056770 한국도로교통공단_지자체별 대상 교통사고 통계(2024·2025), 본인 개발계정 활용신청",
        "file": str(LG.relative_to(ROOT)), "rows": int(len(pd.read_csv(LG, dtype=str))),
        "sgg_compared": int(len(m)), "sgg_death_match": n_death, "sgg_acc_match": n_acc,
        "olddrv_deaths_2025_api": od25, "olddrv_deaths_2025_police": police_od, "olddrv_match_police": police_od == od25,
        "old_deaths_2025_api": old25, "deaths_65plus_2025_age_file": d65_file, "old_match_age_file": old25 == d65_file,
        "in_data_table": True,
    }
    V["lgstat"]["report_text"] = (
        f" 공공데이터포털 OpenAPI(도로교통공단 지자체별 대상 교통사고 통계, 활용신청 인증키)로 받은 시군구별 2025년 사망자·사고건수는 개방 파일과 "
        f"{n_death}/{len(m)}개 시군구에서 일치했고, 고령운전자 가해 사고 사망자 {od25:,}명은 경찰청 통계와"
        f"{'' if police_od == od25 else ' 다르게'}, 65세 이상 사망자 {old25:,}명은 연령별 통계와 {'같았다' if old25 == d65_file else '달랐다'}.")
    print(V["lgstat"])
(ROOT / "outputs" / "verification.json").write_text(json.dumps(V, ensure_ascii=False, indent=1, default=float), encoding="utf-8")
print(T.to_string())
print("conclusions_unchanged:", V["denominator"]["conclusions_unchanged"])
