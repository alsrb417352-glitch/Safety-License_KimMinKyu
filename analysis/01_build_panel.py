"""시군구·시도 분석 패널 구축.

입력: data/raw (rdhub export로 내보낸 원자료 표, index.json에 출처·해시)
출력: data/processed/sigungu_panel.csv, sido_panel.csv, age_deaths_2025.csv, build_log.json

원칙: 원자료 값은 바꾸지 않는다. 행정구역 이름 정규화(공백 제거, 일반구 → 시 통합, 시도 약칭 통일)만 하고 그 규칙을 기록한다.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / "data" / "raw"
OUT = ROOT / "data" / "processed"
OUT.mkdir(parents=True, exist_ok=True)
idx = json.loads((RAW / "index.json").read_text(encoding="utf-8"))
F = {i["name"]: RAW / i["file"] for i in idx}
LOG: dict = {"rules": [], "unmatched": {}, "notes": []}

SIDO_SHORT = {
    "서울특별시": "서울", "부산광역시": "부산", "대구광역시": "대구", "인천광역시": "인천", "광주광역시": "광주", "대전광역시": "대전",
    "울산광역시": "울산", "세종특별자치시": "세종", "경기도": "경기", "강원도": "강원", "강원특별자치도": "강원", "충청북도": "충북",
    "충청남도": "충남", "전라북도": "전북", "전북특별자치도": "전북", "전라남도": "전남", "경상북도": "경북", "경상남도": "경남",
    "제주특별자치도": "제주",
}
GWANGJU_GU = {"동구", "서구", "남구", "북구", "광산구"}


def sido_std(sido: str, sigungu: str | None = None) -> str:
    s = str(sido).strip()
    if s == "전남광주통합특별시":  # 2026년 통합: 분석 기간(2025) 자료와 맞추기 위해 옛 광역 구분으로 환원
        return "광주" if sigungu in GWANGJU_GU else "전남"
    return SIDO_SHORT.get(s, s)


def sgg_std(name: str) -> str:
    n = re.sub(r"\s+", " ", str(name)).strip()
    m = re.match(r"^(\S+시)\s+\S+구$", n)  # 일반구 → 시
    if m:
        return m.group(1)
    return n.replace(" ", "")


INCHEON_OLD = {"중구", "동구", "서구"}
INCHEON_NEW = {"제물포구", "영종구", "서해구", "검단구"}


def incheon_unify(df: pd.DataFrame) -> pd.DataFrame:
    """인천 2026.7 행정체제 개편(중·동·서구 → 제물포·영종·서해·검단구): 기간이 다른 자료를 잇기 위해 하나로 묶음."""
    m = (df["sido"] == "인천") & df["sgg"].isin(INCHEON_OLD | INCHEON_NEW)
    df.loc[m, "sgg"] = "중·동·서구(개편 전후 통합)"
    return df


def num(s: pd.Series) -> pd.Series:
    return pd.to_numeric(s.astype(str).str.replace(",", "").str.strip().replace({"": np.nan, "-": np.nan}), errors="coerce")


LOG["rules"] += [
    "인천 2026.7 개편(중·동·서구 → 제물포·영종·서해·검단구): 모든 자료에서 해당 구를 하나의 단위로 합산",
    "2018 자료의 '창원시(통합)'→창원시, 인천 '남구'→미추홀구(2018.7 명칭 변경)",
    "교통카드 정류장 자료가 없는 군(영양·울릉·진도·함평)은 버스 이용을 0으로 채우지 않고 결측으로 둠",
    "시도명은 약칭(서울·경기 등)으로 통일. '전남광주통합특별시'(2026 인구자료)는 광주 5개 구와 전남으로 환원",
    "일반구가 있는 시(예: 수원시 장안구)는 시 단위로 합산(교통사고 2025 자료의 단위에 맞춤)",
    "시군구 이름의 공백 제거(예: '중 구' → '중구')",
    "대구 군위군은 2023년 경북에서 대구로 편입 — 2018·2019 자료의 경북 군위군을 대구 군위군으로 대응",
]

# ---------------------------------------------------------------- 인구(2026-09-30, 행정동)
pop = pd.read_csv(F["지역별(행정동) 성별 연령별 주민등록 인구수_20260930.csv"], dtype=str)
age_cols = [c for c in pop.columns if re.match(r"^\d+세(이상 )?(남자|여자)$", c)]
def age_of(c): return int(re.match(r"^(\d+)", c).group(1))
for c in age_cols:
    pop[c] = num(pop[c])
pop["계"] = num(pop["계"])
pop["p65"] = pop[[c for c in age_cols if age_of(c) >= 65]].sum(axis=1)
pop["p75"] = pop[[c for c in age_cols if age_of(c) >= 75]].sum(axis=1)
pop["p0_12"] = pop[[c for c in age_cols if age_of(c) <= 12]].sum(axis=1)
chk = (pop[age_cols].sum(axis=1) - pop["계"]).abs().max()
LOG["notes"].append(f"인구: 연령별 합계와 '계' 최대 차이 {chk}")
pop["sido"] = [sido_std(a, b) for a, b in zip(pop["시도명"], pop["시군구명"])]
pop["sgg"] = pop["시군구명"].fillna("").map(sgg_std)
pop.loc[pop["sido"] == "세종", "sgg"] = "세종시"
pop = incheon_unify(pop)
P = pop.groupby(["sido", "sgg"], as_index=False)[["계", "p65", "p75", "p0_12"]].sum().rename(columns={"계": "pop"})
# 연령별 전국 인구(사망률 계산용)
age_nat = {age_of(c): 0 for c in age_cols}
for c in age_cols:
    age_nat[age_of(c)] += pop[c].sum()

# ---------------------------------------------------------------- 교통사고 2025
acc = pd.read_csv(F["한국도로교통공단_시도 시군구별 교통사고(2025).csv"], dtype=str)
acc["sido"] = acc["시도"].map(lambda s: SIDO_SHORT.get(s, s))
acc["sgg"] = acc["시군구"].map(sgg_std)
acc.loc[acc["sido"] == "세종", "sgg"] = "세종시"
for c in ["사고건수", "사망자수", "중상자수", "경상자수", "부상신고자수"]:
    acc[c] = num(acc[c])
acc = incheon_unify(acc)
A = acc.groupby(["sido", "sgg"], as_index=False)[["사고건수", "사망자수", "중상자수"]].sum()

# ---------------------------------------------------------------- 노인 교통사고 2018(시군구) — 연도 불일치, 보조지표
old = pd.read_csv(F["도로교통공단_부문별_노인_교통사고(2018).csv"], dtype=str)
old["sido"] = old["시도"].map(lambda s: SIDO_SHORT.get(s, s))
old["sgg"] = old["시군구"].map(sgg_std)
old.loc[(old["sido"] == "경북") & (old["sgg"] == "군위군"), "sido"] = "대구"
old.loc[old["sido"] == "세종", "sgg"] = "세종시"
old.loc[old["sgg"] == "창원시(통합)", "sgg"] = "창원시"
old.loc[(old["sido"] == "인천") & (old["sgg"] == "남구"), "sgg"] = "미추홀구"  # 2018.7 명칭 변경
for c in ["발생건수", "사망자수", "부상자수", "중상"]:
    old[c] = num(old[c])
old = incheon_unify(old)
O = old.groupby(["sido", "sgg"], as_index=False)[["발생건수", "사망자수", "중상"]].sum().rename(
    columns={"발생건수": "old_acc_2018", "사망자수": "old_death_2018", "중상": "old_serious_2018"})

# ---------------------------------------------------------------- 주행거리 2019(시군구, 대당 일평균 km)
vk = pd.read_csv(F["용도별차종별시군구별 일평균 자동차주행거리(2019년).csv"], dtype=str)
vk["sido"] = vk["시도"].map(lambda s: SIDO_SHORT.get(s, s))
vk["sgg"] = vk["시군구"].map(sgg_std)
vk.loc[(vk["sido"] == "경북") & (vk["sgg"] == "군위군"), "sido"] = "대구"
vk.loc[vk["sido"] == "세종", "sgg"] = "세종시"
vk["vkt_car_private"] = num(vk["비사업용_승용차"])
vk["vkt_all"] = num(vk["전체_계"])
vk = incheon_unify(vk)
V = vk.groupby(["sido", "sgg"], as_index=False)[["vkt_car_private", "vkt_all"]].mean()
LOG["notes"].append("주행거리(2019)는 차량 1대당 일평균 km. 일반구가 있는 시는 구별 값의 단순평균(대수 가중 불가 — 등록대수 미수집)")

# ---------------------------------------------------------------- 버스 정류장 이용(2025, 교통카드)
st = pd.read_csv(F["DM_STTN_USEV_SMY.csv"], dtype=str)
for c in ["평균승차이용량", "평균하차이용량", "평균환승이용량"]:
    st[c] = num(st[c])
st["sido"] = st["시도명"].map(lambda s: SIDO_SHORT.get(s, s))
unalloc = st[(st["시군구명"] == st["시도명"]) & (st["sido"] != "세종")]
LOG["notes"].append(f"정류장 이용: 시군구 미배정(코드 xx000) {len(unalloc)}개 정류장, 승차 {unalloc['평균승차이용량'].sum():.0f}명/일 — 시군구 지표에서 제외(시도 합계에는 포함)")
st_sido = st.groupby("sido", as_index=False).agg(bus_board_sido=("평균승차이용량", "sum"), n_stops_sido=("정류장ID", "nunique"))
st = st[~st.index.isin(unalloc.index)].copy()
st["sgg"] = st["시군구명"].map(sgg_std)
st.loc[st["sido"] == "세종", "sgg"] = "세종시"
st = incheon_unify(st)
B = st.groupby(["sido", "sgg"], as_index=False).agg(n_stops=("정류장ID", "nunique"), bus_board=("평균승차이용량", "sum"))

# ---------------------------------------------------------------- 시군구 패널
D = A.merge(P, on=["sido", "sgg"], how="left", indicator="m_pop")
for name, df in [("bus", B), ("vkt", V), ("old", O)]:
    D = D.merge(df, on=["sido", "sgg"], how="left")
LOG["unmatched"]["accident_without_pop"] = D.loc[D["pop"].isna(), ["sido", "sgg"]].values.tolist()
LOG["unmatched"]["accident_without_bus"] = D.loc[D["n_stops"].isna(), ["sido", "sgg"]].values.tolist()
LOG["unmatched"]["accident_without_vkt"] = D.loc[D["vkt_car_private"].isna(), ["sido", "sgg"]].values.tolist()
LOG["unmatched"]["accident_without_old2018"] = D.loc[D["old_acc_2018"].isna(), ["sido", "sgg"]].values.tolist()
LOG["unmatched"]["pop_without_accident"] = P.merge(A, on=["sido", "sgg"], how="left").query("사고건수 != 사고건수")[["sido", "sgg"]].values.tolist()
D = D.drop(columns=["m_pop"])
METRO = {"서울", "부산", "대구", "인천", "광주", "대전", "울산"}
def rtype(r):
    if r["sido"] in METRO and r["sgg"].endswith("구"):
        return "특별·광역시 구"
    if r["sgg"].endswith("군"):
        return "군"
    return "시"
D["region_type"] = D.apply(rtype, axis=1)
D["share65"] = D["p65"] / D["pop"] * 100
D["death_per100k"] = D["사망자수"] / D["pop"] * 1e5
D["severe_per100k"] = (D["사망자수"] + D["중상자수"]) / D["pop"] * 1e5
D["bus_board_pc"] = D["bus_board"] / D["pop"]  # 1인당 하루 버스 승차(교통카드)
D["stops_per1k"] = D["n_stops"] / D["pop"] * 1000
D["old_death_per100k65"] = D["old_death_2018"] / D["p65"] * 1e5  # 2018 사고 / 2026 인구 — 연도 불일치 주의
D["old_acc_per1k65"] = D["old_acc_2018"] / D["p65"] * 1000
D.to_csv(OUT / "sigungu_panel.csv", index=False, encoding="utf-8-sig")

# ---------------------------------------------------------------- 시도 패널: 면허반납·보호구역·대중교통
ret = pd.read_csv(F["경찰청_시도 경찰청별 고령운전자 자진반납 현황_2015~2024.csv"], dtype=str)
ret["sido"] = ret["지방청"].str.replace("남부|북부", "", regex=True).str.strip()
yrs = list(range(2015, 2025))
for y in yrs:
    ret[f"r65_{y}"] = num(ret[f"{y} 65세 이상"])
    ret[f"rall_{y}"] = num(ret[f"{y} 전체"])
R = ret.groupby("sido", as_index=False)[[f"r65_{y}" for y in yrs] + [f"rall_{y}" for y in yrs]].sum(min_count=1)
R = R[R["sido"].isin(set(SIDO_SHORT.values()))]
LOG["notes"].append("면허반납: 경기남부·경기북부 지방청을 경기로 합산. 세종 포함 여부는 원자료 행 그대로")
kids = pd.read_csv(F["경찰청_시도청별어린이보호구역지정건수_260630.csv"], dtype=str)
kids["sido"] = kids["구분"].str.replace("남부|북부", "", regex=True).str.strip()
kc = [c for c in kids.columns if c not in ("구분", "sido")]
for c in kc:
    kids[c] = num(kids[c])
kids["kids_zones"] = kids[kc].sum(axis=1)
K = kids.groupby("sido", as_index=False)["kids_zones"].sum()
bs = pd.read_csv(F["한국교통안전공단_전국 대중교통 버스정류장 현황(2024년).csv"], dtype=str)
bs["sido"] = bs["구분"].str.strip()
bs["stops_2024"] = num(bs["전체버스정류장"])
bs["sheltered_2024"] = num(bs["유개버스정류장"])
PS = P.groupby("sido", as_index=False)[["pop", "p65", "p75", "p0_12"]].sum()
AS = A.groupby("sido", as_index=False)[["사고건수", "사망자수", "중상자수"]].sum()
S = PS.merge(R, on="sido", how="left").merge(K, on="sido", how="left").merge(bs[["sido", "stops_2024", "sheltered_2024"]], on="sido", how="left") \
      .merge(st_sido, on="sido", how="left").merge(AS, on="sido", how="left")
S["share65"] = S["p65"] / S["pop"] * 100
S["return_rate_2024_per1k65"] = S["r65_2024"] / S["p65"] * 1000
S["return_cum_2019_2024_per1k65"] = S[[f"r65_{y}" for y in range(2019, 2025)]].sum(axis=1) / S["p65"] * 1000
S["bus_board_pc"] = S["bus_board_sido"] / S["pop"]
S["death_per100k"] = S["사망자수"] / S["pop"] * 1e5
S["kids_zones_per10k_child"] = S["kids_zones"] / S["p0_12"] * 1e4
S["sheltered_share"] = S["sheltered_2024"] / S["stops_2024"] * 100
S.to_csv(OUT / "sido_panel.csv", index=False, encoding="utf-8-sig")

# ---------------------------------------------------------------- 연령별 사망(2025, 전국)
ag = pd.read_csv(F["한국도로교통공단_사상자 연령층별 성별 교통사고(2025).csv"], dtype=str)
for c in ["사망자수", "중상자수", "경상자수", "부상신고자수"]:
    ag[c] = num(ag[c])
G = ag.groupby("사상자연령층", as_index=False)[["사망자수", "중상자수"]].sum()
def band_pop(label: str) -> float | None:
    m = re.match(r"^(\d+)-(\d+)세$", label)
    if m:
        lo, hi = int(m.group(1)), int(m.group(2))
        return sum(v for a, v in age_nat.items() if lo <= a <= hi)
    if label.startswith("12세이하"):
        return sum(v for a, v in age_nat.items() if a <= 12)
    m = re.match(r"^(\d+)세이상", label)
    if m:
        return sum(v for a, v in age_nat.items() if a >= int(m.group(1)))
    return None
G["pop_2026"] = G["사상자연령층"].map(band_pop)
G["death_per100k"] = G["사망자수"] / G["pop_2026"] * 1e5
G.to_csv(OUT / "age_deaths_2025.csv", index=False, encoding="utf-8-sig")
LOG["notes"].append("연령별 사망률: 2025 사망자 / 2026-09 주민등록인구(연령대) — 분모 시점 차이 9개월")
LOG["counts"] = {"sigungu_rows": len(D), "sido_rows": len(S)}
(OUT / "build_log.json").write_text(json.dumps(LOG, ensure_ascii=False, indent=1), encoding="utf-8")
print(json.dumps(LOG, ensure_ascii=False, indent=1)[:3000])
print(G)
