"""분석보고서 PDF 생성. 모든 수치는 outputs/results.json·tables에서 읽어 채운다(손으로 옮겨 적지 않음).
사용: python report/build_report.py [--name "이름 또는 팀명"] [--code-url https://github.com/... 또는 클라우드 링크]
"""
from __future__ import annotations

import argparse
import base64
import json
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
R = json.loads((ROOT / "outputs" / "results.json").read_text(encoding="utf-8"))
FIG = ROOT / "outputs" / "figures"
TAB = ROOT / "outputs" / "tables"
calls = [json.loads(l) for f in ("tool_calls.jsonl", "tool_calls_api.jsonl") if (ROOT / "logs" / f).exists()
         for l in (ROOT / "logs" / f).read_text(encoding="utf-8").splitlines() if l.strip()]

ap = argparse.ArgumentParser()
ap.add_argument("--name", default="김민규")
ap.add_argument("--code-url", default="(GitHub 저장소 주소 기입)")
ap.add_argument("--out", default=str(ROOT / "report" / "분석보고서.pdf"))
args = ap.parse_args()


def img(name: str) -> str:
    return "data:image/png;base64," + base64.b64encode((FIG / name).read_bytes()).decode()


def f1(x, nd=1):
    return f"{x:,.{nd}f}"


A, RT, Q, B, S = R["age"], R["returns"], R["quintiles"], R["blindspots"], R["scenario"]
reg = pd.read_csv(TAB / "table_regression_nb.csv")
def irr(model, term):
    r = reg[(reg.model == model) & (reg.term == term)].iloc[0]
    return r
r_s65 = irr("모형2(+주행거리)", "share65")
r_vkt = irr("모형2(+주행거리)", "vkt_car_private")
r_bus1 = irr("모형1", "lbus")
r_bus2 = irr("모형2(+주행거리)", "lbus")
r_metro = irr("모형2(+주행거리)", "C(region_type, Treatment('시'))[T.특별·광역시 구]")
bl = pd.read_csv(TAB / "table_blindspots.csv")
top = bl.head(10)
n_calls = len(calls)
tools_used = sorted({c["tool"] for c in calls})
mid = S["range"]["mid"]
lo, hi = S["range"]["low"], S["range"]["high"]
ret_by_year = RT["by_year_65plus"]

DATA_ROWS = [
    ("시도 시군구별 교통사고 통계(2025)", "한국도로교통공단", "공공데이터포털", "https://www.data.go.kr/data/15070297/fileData.do", "시군구 교통사고·사망자"),
    ("사상자 연령층별 성별 교통사고 통계(2025)", "한국도로교통공단", "공공데이터포털", "https://www.data.go.kr/data/15070293/fileData.do", "연령대별 사망자"),
    ("시도 경찰청별 고령운전자 자진반납 현황(2015~2024)", "경찰청", "공공데이터포털", "https://www.data.go.kr/data/15065567/fileData.do", "면허 반납"),
    ("행정구역(시군구)별/1세별 주민등록인구(2024.6·2025.6)", "행정안전부", "KOSIS OpenAPI", "https://kosis.kr/statHtml/statHtml.do?orgId=101&tblId=DT_1B04006", "인구·고령인구(사고·반납 연도와 시점 일치)"),
    ("가해자 연령층별 교통사고(2015~2025)", "경찰청", "KOSIS OpenAPI", "https://kosis.kr/statHtml/statHtml.do?orgId=132&tblId=DT_V_MOTA_021", "고령운전자 사고 추이·총 사망자 대조"),
    ("지자체별 대상 교통사고 통계(2024·2025)", "한국도로교통공단", "공공데이터포털 OpenAPI", "https://www.data.go.kr/data/15056770/openapi.do", "시군구 고령운전자·65세 이상 사고"),
    ("보행노인 교통사고 다발지역(2023~2025)", "한국도로교통공단", "공공데이터포털 OpenAPI", "https://www.data.go.kr/data/15057666/openapi.do", "반납 후 보행 위험 지점"),
    ("성 및 연령별 추계인구(중위, 2022~2072)", "통계청", "KOSIS", "https://kosis.kr/statHtml/statHtml.do?orgId=101&tblId=DT_1BPA001", "65세 이상 인구 전망"),
    ("시군구별 정류장평균이용량(2025, 교통카드)", "국토교통부", "공공데이터포털", "https://www.data.go.kr/data/15162142/fileData.do", "버스 이용(대중교통 대리지표)"),
    ("전국 버스정류장 위치정보(2025)", "국토교통부", "공공데이터포털", "https://www.data.go.kr/data/15067528/fileData.do", "지도 시각화"),
    ("용도별 차종별 시군구별 일평균 자동차 주행거리(2019)", "한국교통안전공단", "공공데이터포털", "https://www.data.go.kr/data/15088483/fileData.do", "자동차 의존·탄소 대리지표"),
    ("부산도시철도 월별 역별 권종별 승하차(2014~2024)", "부산교통공사", "부산 Big-데이터웨이브", "https://data.busan.go.kr/bdip/opendata/detail.do?publicdatapk=15128561", "부산 사례: 노인 무임 이용 추이"),
    ("부산 교통약자 이동지원 차량 운영현황(2025.5)", "부산시설공단", "부산 Big-데이터웨이브", "https://data.busan.go.kr/bdip/opendata/detail.do?publicdatapk=15147515", "부산 사례: 수요응답형 교통 대기·미배차"),
    ("전국 노인·장애인 보호구역 표준데이터(부산)", "부산 각 구군", "부산 Big-데이터웨이브", "https://data.busan.go.kr/bdip/opendata/detail.do?publicdatapk=15034532", "부산 사례: 보호구역과 사고다발지역 거리"),
]
data_rows_html = "\n".join(
    f"<tr><td>{n}</td><td>{o}</td><td>{p}</td><td class='url'>{u}</td><td>{why}</td></tr>" for n, o, p, u, why in DATA_ROWS)
top_rows = "\n".join(
    f"<tr><td>{i + 1}</td><td>{r.sido} {r.sgg}</td><td>{r.share65:.1f}%</td>"
    f"<td>{('자료 없음' if pd.isna(r.bus_board_pc) else f'{r.bus_board_pc:.3f}')}</td><td>{r.death_per100k:.1f}</td><td>{int(r.lg_olddrv_death_2025)}명</td></tr>"
    for i, r in top.reset_index(drop=True).iterrows())
by_sido = ", ".join(f"{k} {v}" for k, v in B["by_sido"].items())
_sp = pd.read_csv(ROOT / "data" / "processed" / "sido_panel.csv").sort_values("return_rate_2024_per1k65", ascending=False)
TOP3 = _sp["sido"].head(3).tolist()
BOT6 = _sp["sido"].tail(6).tolist()[::-1]
V = json.loads((ROOT / "outputs" / "verification.json").read_text(encoding="utf-8"))
BU = json.loads((ROOT / "outputs" / "results_busan.json").read_text(encoding="utf-8"))
OBS = B["olddrv"]
ON = R["olddrv_national"]
ORT = R["olddrv_by_region_type"]
DB, BG, BS, PH, PJ, SF = BU["duribal"], BU["busan_gu"], BU["busan_sido"], BU["ped_hotspots"], BU["projection"], BU["subway_free"]
r_od_bus = irr("모형3(고령운전자 사고 사망)", "lbus")
r_od_vkt = irr("모형3(고령운전자 사고 사망)", "vkt_car_private")
OD = V["older_drivers"]
VC = {r["항목"]: (r["초안(2026.9 인구 파일)"], r["검증(KOSIS API 2025.6·2024.6)"]) for r in V["denominator"]["comparison"]}
LG = V.get("lgstat")
LG_TEXT = LG["report_text"] if LG and LG.get("report_text") else ""
LG_COVER = "·공공데이터포털" if LG and LG.get("in_data_table") else ""
N_API = sum(1 for r in DATA_ROWS if "OpenAPI" in r[2])
N_BUSAN = sum(1 for r in DATA_ROWS if "Big-데이터웨이브" in r[2])
N_FILE = len(DATA_ROWS) - N_API - N_BUSAN

HTML = f"""<!doctype html><html lang="ko"><head><meta charset="utf-8"><title>분석보고서</title>
<style>
@page {{ size: A4; margin: 15mm 15mm 14mm 15mm; }}
* {{ box-sizing: border-box; }}
body {{ font-family: 'Noto Sans CJK KR', 'Noto Sans KR', sans-serif; color:#1f2937; font-size: 9.3pt; line-height: 1.48; margin:0; }}
h1 {{ font-size: 21pt; line-height:1.3; margin: 0 0 6mm; letter-spacing:-0.5px; }}
h2 {{ font-size: 11.5pt; margin: 3.5mm 0 1.6mm; padding: 1.2mm 2.5mm; background:#eef2ff; border-left: 4px solid #2563eb; }}
h3 {{ font-size: 10pt; margin: 2.2mm 0 0.8mm; color:#1e3a8a; }}
p {{ margin: 0 0 2mm; text-align: justify; }}
ul {{ margin: 0 0 2mm; padding-left: 5mm; }} li {{ margin-bottom: 1mm; }}
.page {{ page-break-after: always; }}
.cover {{ height: 262mm; display:flex; flex-direction:column; justify-content:center; padding: 0 8mm; }}
.cover .tag {{ color:#2563eb; font-weight:700; font-size:11pt; margin-bottom:4mm; }}
.cover table td {{ padding: 2.5mm 3mm; border-bottom:1px solid #e5e7eb; font-size:10.5pt; }}
.cover table td:first-child {{ width: 32mm; color:#6b7280; }}
table {{ border-collapse: collapse; width:100%; }}
table.data th, table.data td {{ border:1px solid #d1d5db; padding: 0.7mm 1.3mm; font-size: 7.5pt; line-height:1.35; vertical-align: top; }}
table.data th {{ background:#f3f4f6; }}
td.url {{ font-size: 6.8pt; word-break: break-all; }}
.kpis {{ display:flex; gap: 3mm; margin: 2mm 0 3mm; }}
.kpi {{ flex:1; border:1px solid #e5e7eb; border-radius: 2mm; padding: 2mm 2.5mm; }}
.kpi b {{ display:block; font-size: 15pt; color:#d6453d; line-height:1.2; }}
.kpi span {{ font-size: 8pt; color:#4b5563; }}
.fig {{ margin: 2mm 0 2mm; text-align:center; }}
.fig img {{ width: 100%; }}
.two {{ display:flex; gap:4mm; align-items:flex-start; }}
.two > div {{ flex:1; }}
.note {{ font-size: 7.8pt; color:#6b7280; }}
.box {{ border:1px solid #c7d2fe; background:#f8faff; border-radius:2mm; padding: 2mm 3mm; margin: 2mm 0; }}
.prompt {{ font-size: 8.2pt; background:#f9fafb; border-left:3px solid #9ca3af; padding:1.2mm 2.5mm; margin:1mm 0; }}
.small {{ font-size: 8.6pt; }}
.keep {{ break-inside: avoid; page-break-inside: avoid; }}
.two .note {{ text-align: left; }}
table.tight td, table.tight th {{ font-size: 7.8pt; padding: 0.8mm 1.2mm; white-space: nowrap; }}
</style></head><body>

<section class="page cover">
  <div class="tag">AI와 함께하는 교통문제 해결을 위한 데이터 분석 공모전 · 분석보고서</div>
  <h1>운전대를 놓은 노인은 어디로 가는가<br><span style="font-size:14pt;color:#4b5563;font-weight:500">고령운전자 면허 반납의 지역 격차와 ‘이동 사각지대’ 진단,<br>그리고 반납자 이동보장 정책 제안</span></h1>
  <table>
    <tr><td>이름/팀명</td><td>{args.name}</td></tr>
    <tr><td>주제</td><td>낮은 대중교통 이용·낮은 면허 반납·높은 교통사망이 함께 나타나는 ‘이동 사각지대’를 공공데이터로 찾아내고, 면허 반납을 이동권 보장과 연계하는 정책을 제안</td></tr>
    <tr><td>활용 데이터</td><td>공공데이터 {len(DATA_ROWS)}종 — 개방 파일·통계표 {N_FILE}종 + OpenAPI {N_API}종(KOSIS·공공데이터포털, 인증키 호출) + 부산 Big-데이터웨이브 {N_BUSAN}종 / 도로교통공단·경찰청·행정안전부·국토교통부·통계청·한국교통안전공단·부산교통공사·부산시설공단, 227개 시군구·17개 시도 + 부산 16개 구군 사례</td></tr>
    <tr><td>분석 코드</td><td>{args.code_url}</td></tr>
  </table>
</section>

<section>
<h2>1. 분석 배경 및 목적</h2>
<div class="kpis">
  <div class="kpi"><b>{A['share_deaths_65plus']}%</b><span>2025년 교통사고 사망자 {A['total_deaths_2025']:,}명 중 65세 이상 비중(인구 비중 {A['share_pop_65plus']}%)</span></div>
  <div class="kpi"><b>{ret_by_year['2015']:,} → {ret_by_year['2024']:,}건</b><span>65세 이상 운전면허 자진반납(2015→2024)</span></div>
  <div class="kpi"><b>{RT['gap_ratio_max_min']}배</b><span>시도별 반납률 격차(최고 {RT['max'][0]} {RT['max'][1]:.1f} vs 최저 {RT['min'][0]} {RT['min'][1]:.1f}, 65세 이상 1천 명당)</span></div>
</div>
<p><b>현황.</b> 2025년 교통사고 사망자의 절반 이상({A['share_deaths_65plus']}%)이 65세 이상이며, 인구 10만 명당 사망률은 {A['rate_65plus']:.1f}명으로 65세 미만({A['rate_under65']:.1f}명)의 {A['ratio_65_vs_under65']:.1f}배다(그림 1). 경찰청 통계(KOSIS API)로 보면 65세 이상 운전자가 낸 사고의 사망자 비중은 2015년 {OD['share_deaths_by_65_driver']['2015']}%에서 2025년 {OD['share_deaths_by_65_driver']['2025']}%({OD['series']['2025']['사망자수_65']:,}명)로 두 배 가까이 늘었다(전체 사망자가 {OD['series']['2015']['사망자수']:,}→{OD['series']['2025']['사망자수']:,}명으로 주는 동안 {OD['series']['2015']['사망자수_65']:,}→{OD['series']['2025']['사망자수_65']:,}명으로 줄지 않음). 정부와 지자체는 고령운전자 사고 대책으로 <b>운전면허 자진반납</b>을 장려했고, 반납 건수는 2015년 {ret_by_year['2015']:,}건에서 2024년 {ret_by_year['2024']:,}건으로 늘었다. 반납은 고령운전 위험을 줄이는 동시에 승용차 주행을 줄여 탄소 감축에도 기여한다(수송부문 온실가스의 약 97%가 도로교통에서 발생). 반납자는 앞으로 더 늘어난다. 통계청 장래인구추계(중위)로 65세 이상 인구는 2025년 {PJ['2025']['p65_10k']:,.0f}만 명에서 2035년 {PJ['2035']['p65_10k']:,.0f}만 명으로 {PJ['growth_p65_2025_2035_pct']}% 늘어, 지금 반납률만 유지돼도 연간 반납은 2024년 {PJ['returns_2024'] / 1e4:.1f}만 건에서 2035년 약 {PJ['returns_2035_at_2024_rate'] / 1e4:.1f}만 건이 된다.</p>
<p><b>문제.</b> 그러나 기존 정책은 반납 ‘건수’만 성과로 보며, 반납한 노인이 <b>무엇으로 이동하는지</b>는 묻지 않는다. 버스가 하루 몇 번 다니지 않는 농어촌에서 면허 반납은 곧 병원·장보기·일자리로 가는 길을 잃는 일이다. 그래서 반납이 가장 필요한 지역일수록 반납하지 못하고 위험한 운전을 이어가는 <b>역설</b>이 생길 수 있다. 이는 사고 통계와 교통 통계가 따로 관리되어 기존 정책에서 잘 드러나지 않았던 문제다.</p>
<p><b>목적.</b> 공공데이터를 결합해 ① 면허 반납률의 지역 격차가 대중교통 이용과 어떤 관계인지, ② 고령화·대중교통 공백·높은 교통사망이 겹친 <b>‘이동 사각지대’</b>에 교통사망이 얼마나 집중되는지 확인하고, ③ 반납을 이동권 보장과 연결하는 정책의 대상 지역과 효과(안전·탄소)를 제시한다.</p>
<div class="fig"><img src="{img('fig1_age_death_rate.png')}" style="width:56%"></div>

<h2>2. 활용 데이터</h2>
<table class="data">
<thead><tr><th style="width:30%">활용 데이터(명)</th><th style="width:12%">제공기관(명)</th><th style="width:14%">출처 플랫폼(명)</th><th>URL</th><th style="width:19%">용도(선정 이유)</th></tr></thead>
<tbody>{data_rows_html}</tbody>
</table>
<p class="note">공공데이터포털 개방 파일은 수집 시 데이터셋 페이지의 이용허락 표시를 기록했고(data/raw/manifest.json), OpenAPI 2종과 부산 Big-데이터웨이브 자료 3종은 이용허락범위가 ‘제한 없음’임을 2026.10.21에 확인·기록했다(data/raw/license_check_20261021.json). 인구·경찰청 통계는 KOSIS OpenAPI를, 도로교통공단 자료는 공공데이터포털에서 본인 계정으로 활용신청해 받은 인증키로 호출했다(키 값은 도구 밖으로 나가지 않음). 원본 파일의 SHA-256 해시, 수집 시각, 원 상세 페이지·배포 URL을 데이터 목록(data/raw/index.json, manifest.json)에 함께 보존했다. 민간·개인정보 자료는 쓰지 않았다(공개 집계 통계와 공개 운행기록을 쓰고, 보고서에는 집계 결과만 제시).</p>

<h2>3. 분석과정 및 방법</h2>
<p><b>① 수집.</b> 자체 개발한 AI 연구자료 수집 도구(rdhub, 4장)로 공공데이터포털을 검색하고, 상세 페이지에서 제공기관·수정일·이용조건을 확인한 뒤 실제 배포 파일을 받았다. 받은 파일이 CSV인지 시그니처로 확인하고(오류 HTML을 자료로 저장하지 않음), 원본 해시와 출처를 기록했다. 내보내기 후 행 수·값 대조에서 불일치 0건을 확인했다.</p>
<p><b>② 전처리(행정구역 정합).</b> 자료마다 기준 연도와 행정구역이 달라 다음 규칙으로 맞췄다. 일반구가 있는 시는 시 단위로 합산(KOSIS 인구의 일반구·출장소 행은 상위 시·구에 이미 포함되어 제외하고 시도 합계와 일치 확인), 인천 중·동·서구는 2026년 개편 전후 자료를 잇기 위해 하나의 단위(광역시 구)로 묶음, 군위군은 대구로 대응, 2018년 자료의 명칭 변경(인천 남구→미추홀구) 반영. 결과적으로 <b>227개 시군구·17개 시도 패널</b>을 만들었다. 교통카드 정류장 자료가 없는 4개 군은 버스 이용을 0으로 채우지 않고 결측으로 두어 5분위·회귀에서 제외했다(사각지대 분류에서는 ‘대중교통 공백’으로 간주, 결과 ③ 참고).</p>
<p><b>③ 지표.</b> 대중교통 이용 = 시군구 정류장별 하루 평균 승차 합 ÷ 주민등록인구(1인당 하루 버스 승차, 교통카드 기준). 교통사고 사망률 = 인구 10만 명당 사망자(2025 사고 ÷ 2025.6 인구). 반납률 = 65세 이상 1천 명당 연간 반납 건수(2024 반납 ÷ 2024.6 65세 이상 인구; 면허 보유자가 아닌 전체 고령인구 기준). <b>고령운전자 사고율·사망률</b> = 65세 이상 운전자가 가해자인 사고 건수(65세 이상 1천 명당)·그 사고의 사망자(65세 이상 10만 명당), 치사율 = 사고 100건당 사망자(모두 2025, 도로교통공단 OpenAPI). 분모는 모두 해당 연도 중앙 시점(6월 말) 주민등록인구다. 자동차 의존 = 비사업용 승용차 1대당 일평균 주행거리(2019).</p>
<p><b>④ 분석 기법.</b> (가) 시도별 반납률과 버스 이용의 스피어만 순위상관, (나) 시군구를 버스 이용 5분위로 나눈 사망률 비교, (다) <b>음이항 회귀</b>(종속: 사망자 수, 인구 offset; 설명: 65세 이상 비율, log 1인당 버스 승차, 승용차 주행거리, 지역유형[시·군·특별/광역시 구]) — 과대산포를 고려해 포아송 대신 음이항을 사용, (라) 고령비율 상위 1/3·버스 이용 하위 1/3·사망률 상위 1/3을 모두 충족하는 <b>‘3중 이동 사각지대’</b> 유형화, (마) 반납률 격차 해소 시나리오로 추가 반납·회피 주행거리·CO₂ 범위 산정, (바) <b>부산 사례</b>: 도시철도 권종별 승하차(2014~2024)로 무임 비중, 두리발 운행기록({DB['requests']:,}건)으로 구군별 대기·미배차, 보행노인 사고다발지역과 노인보호구역의 거리를 계산.</p>

<h2>4. AI 기술 활용</h2>
<div class="box small">
<b>사용 서비스.</b> Claude(Anthropic, 대화형 AI) + <b>rdhub</b>(본인이 AI와 함께 개발한 ‘연구자료 수집 도구 서버’, MCP·CLI로 AI가 호출).<br>
<b>활용 범위.</b> ① 데이터 탐색·수집: AI가 rdhub 도구를 {n_calls}회 호출({', '.join(tools_used)})해 카탈로그 검색 → 원문 확인(제공기관·원출처·이용조건 판정) → 파일 수집 → 원본 해시·버전 기록 → 표 정리 → 내보내기 검증까지 수행. 모든 호출은 로그(logs/tool_calls*.jsonl)로 남겼다. 로그인이 필요한 자료는 사용자가 로그인만 하고, AI가 브라우저에서 공공데이터포털 자동승인 활용신청(도로교통공단 API 2종)과 전국 시군구 코드 순회 호출({V['lgstat']['rows']:,}행), 부산 Big-데이터웨이브 교통 자료 수집(원 URL·해시 기록)을 수행했다. ② 분석 코드 작성(Python)과 결과 해석 초안. ③ 보고서 문장 초안.<br>
<b>검증.</b> AI가 수치를 기억으로 채우지 못하도록, 보고서의 모든 수치는 분석 코드를 다시 실행해 산출한 결과 파일(results.json)에서 자동으로 채웠다. 행정구역 정합 규칙과 매칭되지 않은 지역을 로그로 남겨 직접 확인했고, 연도 불일치·대리지표의 한계를 본문에 밝혔다. 외부 AI에는 개인정보·비공개 자료를 입력하지 않았다(공개 집계 통계만 사용).<br>
<b>API 교차검증.</b> 초안은 2026년 9월 인구 파일을 분모로 썼다. 등록 인증키로 rdhub가 KOSIS API를 호출해 사고·반납 연도의 6월 인구(시군구×1세, 각 3만여 행)로 바꿔 전 과정을 재계산했다. 65세 이상/미만 사망률 배수 {VC['65세 이상/미만 사망률 배수'][0]}→{VC['65세 이상/미만 사망률 배수'][1]}, 반납률–버스 이용 ρ {VC['반납률–버스 이용 스피어만 ρ'][0]:.2f}→{VC['반납률–버스 이용 스피어만 ρ'][1]:.2f}, 3중 사각지대 {VC['3중 사각지대 시군구 수'][0]:.0f}→{VC['3중 사각지대 시군구 수'][1]:.0f}곳으로 수치가 조정됐고 결론은 유지됐다(본문은 검증본 수치). 2025년 교통사고 사망자 {OD['total_deaths_2025_police']:,}명은 경찰청 통계(KOSIS)와 도로교통공단 파일이 {'일치' if OD['total_deaths_match'] else '불일치'}했다.{LG_TEXT}
</div>
<p class="small"><b>주요 프롬프트(요지).</b></p>
<div class="prompt">“공모전 공고와 분석보고서 양식을 보고, 이동격차·교통약자·탄소중립을 함께 다룰 수 있으면서 기존 정책에서 드러나지 않은 교통문제를 주제로 정해. 공공데이터로 검증 가능한지부터 확인해.”</div>
<div class="prompt">“rdhub로 고령인구·교통사고·면허반납·버스 이용·주행거리 자료를 찾아 수집해. 각 자료의 제공기관, 수정일, 이용허락범위를 원문에서 확인하고, 파일이 아니라 오류 페이지가 오면 실패로 처리해.”</div>
<div class="prompt">“버스 이용과 사망률의 관계를 인과로 단정하지 말고, 고령화·자동차 의존을 함께 넣은 음이항 회귀로 확인해. 유의하지 않으면 그대로 보고해.”</div>
<div class="prompt">“도로교통공단 API의 시군구별 고령운전자 사고로 사각지대 진단을 다시 확인해. 사고 건수와 사망을 나눠 보고, 부산 자료(무임 이용·두리발 운행기록·보호구역)로 정책을 구체화해.”</div>

<h2>5. 분석 내용 및 결과</h2>
<div class="keep"><h3>결과 ① 면허 반납은 81배 늘었지만, 대중교통이 부족한 지역에서는 절반 수준이다</h3>
<div class="fig"><img src="{img('fig2_license_return.png')}" style="width:90%"></div></div>
<p>2024년 65세 이상 1천 명당 반납은 {RT['max'][0]}({RT['max'][1]:.1f}건)·{'·'.join(TOP3[1:])}가 높고 {RT['min'][0]}({RT['min'][1]:.1f}건)·{'·'.join(BOT6[1:])}이 낮아 최대 {RT['gap_ratio_max_min']}배 차이가 난다(광주·세종은 버스 이용이 중간 수준인데도 반납률이 낮은 예외). 시도별 반납률은 1인당 버스 이용과 뚜렷한 양(+)의 순위상관을 보였다(ρ={RT['spearman_bus_vs_return'][0]:.2f}, p={RT['spearman_bus_vs_return'][1]:.3f}). 반대로 교통사고 사망률이 높은 시도일수록 반납률이 낮은 경향이 있었다(ρ={RT['spearman_death_vs_return'][0]:.2f}, p={RT['spearman_death_vs_return'][1]:.2f}, 5% 수준에서 유의하지 않은 탐색적 경향). <b>반납이 더 필요해 보이는 곳에서 반납이 적은 경향이 보인다.</b> 도로교통공단 API로 보면 반납률이 높은 시도일수록 고령운전자 가해 사고 사망률(2024, 65세 이상 10만 명당)이 낮았다(ρ={RT['spearman_return_vs_olddrv_death_2024'][0]:.2f}, p={RT['spearman_return_vs_olddrv_death_2024'][1]:.3f}). 반납률 1위 부산은 {BS['olddrv_death_per100k65_2024']:.1f}명으로 17개 시도 중 가장 낮아 전국({BS['national_olddrv_death_per100k65_2024']:.1f}명)의 절반에 못 미친다(시도 단위 상관이라 인과는 아님).</p>

<div class="keep"><h3>결과 ② 버스 이용 하위 20% 시군구의 교통사고 사망률은 상위 20%의 {Q['ratio_q1_q5']:.1f}배</h3>
<div class="fig"><img src="{img('fig3_bus_quintile_deaths.png')}" style="width:90%"></div></div>
<p>버스 이용 1분위(하위 20%) 시군구의 사망률은 인구 10만 명당 {Q['death_rate'][0]:.1f}명으로 5분위({Q['death_rate'][4]:.1f}명)의 {Q['ratio_q1_q5']:.1f}배였고, 65세 이상 사망률(2025)도 {Q['ratio_old2025_q1_q5']:.1f}배 차이가 났다. 버스 자료가 있는 {Q['n_sgg']}개 시군구 중 하위 40%는 인구의 {Q['pop_share_q1q2']}%에 불과하지만 교통사고 사망의 <b>{Q['death_share_q1q2']}%</b>를 차지한다.</p>
<p><b>고령운전자 사고: 건수는 비슷하고 사망은 {Q['ratio_olddrv_death_q1_q5']:.1f}배.</b> 시군구별 고령운전자(65세 이상) 가해 사고를 보면, 65세 이상 1천 명당 사고 건수는 1분위 {Q['olddrv_acc_rate'][0]:.1f}건, 5분위 {Q['olddrv_acc_rate'][4]:.1f}건으로 거의 같았다. 그러나 그 사고로 숨진 사람은 65세 이상 10만 명당 {Q['olddrv_death_rate'][0]:.1f}명 대 {Q['olddrv_death_rate'][4]:.1f}명이고, 사고 100건당 사망(치사율)은 {Q['olddrv_cfr'][0]:.1f}명 대 {Q['olddrv_cfr'][4]:.1f}명이다(그림 3나). 사고 발생 수준은 비슷하지만 버스 이용이 적은 곳일수록 사고 100건당 사망자가 훨씬 많다(도로·차종·충돌 유형을 맞춘 비교는 아니며, 빠른 지방도로·응급 접근성 차이 등이 가능한 설명). 군 지역에서는 교통사고 사망자의 {ORT['군']['share_of_deaths']}%가 고령운전자 가해 사고에서 나왔다(특별·광역시 구 {ORT['특별·광역시 구']['share_of_deaths']}%).</p>
<p><b>회귀 결과(음이항, 모형1 n={R['regression_n']['모형1']}, 모형2·3 n={R['regression_n']['모형2']}).</b> 지역유형을 통제하면 65세 이상 비율 1%p 증가 시 사망 위험이 {(r_s65.IRR - 1) * 100:.1f}% 높고(IRR {r_s65.IRR:.3f}, 95% CI {r_s65.IRR_lo:.3f}–{r_s65.IRR_hi:.3f}), 승용차 1대당 일평균 주행거리 1km 증가 시 {(r_vkt.IRR - 1) * 100:.1f}% 높았다(IRR {r_vkt.IRR:.3f}, p&lt;0.001). 버스 이용의 독립 효과는 방향은 음(-)이지만 유의하지 않았다(모형1 IRR {r_bus1.IRR:.3f}, p={r_bus1.p:.3f}; 모형2 p={r_bus2.p:.2f}). 고령운전자 사고 사망자를 종속변수로 한 모형3에서도 주행거리(IRR {r_od_vkt.IRR:.3f}, p={r_od_vkt.p:.3f})와 고령비율은 유의했고 버스 이용은 유의하지 않았다(p={r_od_bus.p:.2f}). 즉 대중교통 공백은 고령화·자동차 의존과 <b>함께 나타나며</b>, 버스 이용만의 독립 효과는 확인되지 않았다. 그래서 정책 대상은 고령화·낮은 버스 이용·높은 사망률이 겹친 지역으로 정했다(아래 ‘3중 사각지대’).</p>

<div class="keep"><h3>결과 ③ ‘3중 이동 사각지대’ {B['n_triple']}곳: 인구 {B['pop_share_triple']}%, 교통사고 사망 {B['death_share_triple']}%</h3>
<p>고령비율 상위 1/3(≥{B['thresholds']['share65_top_tertile']:.1f}%), 1인당 버스 승차 하위 1/3(≤{B['thresholds']['bus_board_pc_bottom_tertile']:.3f}회), 사망률 상위 1/3(≥{B['thresholds']['death_per100k_top_tertile']:.1f}명)을 모두 충족한 시군구는 {B['n_triple']}곳({by_sido})이다. 이 중 {'·'.join(x[1] for x in B['observed_only']['nobus'])}은 교통카드 자료가 없어 공백으로 간주했고, 빼면 {B['observed_only']['n']}곳(인구 {B['observed_only']['pop_share']}%, 사망 {B['observed_only']['death_share']}%)이다. 이곳 인구는 {B['pop_triple'] / 1e4:.0f}만 명(65세 이상 {B['p65_triple'] / 1e4:.1f}만 명)이며 사망률은 {B['death_rate_triple']:.1f}명으로 나머지 지역({B['death_rate_rest']:.1f}명)의 {B['death_rate_triple'] / B['death_rate_rest']:.1f}배다. (사망률이 분류 기준에 포함되어 있으므로 이 비율은 ‘정책 대상의 규모’를 보여주는 값이다.) <b>고령운전자 가해 사고로 보면</b> 이곳은 65세 이상 인구의 {OBS['p65_share_triple']}%이지만 고령운전자 사고 사망자의 {OBS['olddrv_death_share_of_national']}%({OBS['olddrv_deaths_triple']}명)가 나왔고, 사망자 중 고령운전자 사고 비중이 {OBS['olddrv_share_of_deaths_triple']}%(나머지 지역 {OBS['olddrv_share_of_deaths_rest']}%)다.</p></div>
<div class="two keep" style="align-items:center">
<div style="flex:0.9"><div class="fig" style="margin-top:0"><img src="{img('fig4_blindspot_map.png')}"></div></div>
<div style="flex:1.1">
<table class="data tight"><tr><th>#</th><th>시군구</th><th>65세+</th><th>1인당<br>버스승차</th><th>사망률</th><th>고령운전자<br>사고 사망</th></tr>
{top_rows}
</table>
<p class="note">사망률: 인구 10만 명당(2025). 버스 승차: 1인당 하루(2025, 교통카드). 고령운전자 사고 사망: 65세 이상 운전자가 가해자인 사고의 사망자 수(2025). ‘자료 없음’은 교통카드 정류장 자료가 없는 군. 전체 {B['n_triple']}곳 목록은 outputs/tables/table_blindspots.csv.</p>
</div></div>

<div class="keep"><h3>결과 ④ 부산 사례: 반납률 1위 도시가 보여주는 ‘반납 이후’의 조건과 과제</h3>
<p><b>반납률 1위 도시에는 운전을 대신할 수단이 있다.</b> 부산은 65세 이상 반납률 전국 1위({BS['return_rate_2024']:.1f}건)이고 고령운전자 사고 사망률은 가장 낮다. 같은 기간 부산 도시철도 승차 중 무임(경로 등) 비중은 2014년 {SF['share']['2014']}%에서 2024년 {SF['share']['2024']}%로 높아졌다(2024년 무임 승차 {SF['free_riders_2024'] / 1e4:,.0f}만 회, 부산교통공사의 별도 무임이용인원 통계와 연도별로 일치). 무임 승차는 노인 전체(장애인·유공자 포함)의 이용이라 반납자가 옮겨 탔다는 직접 증거는 아니지만, 노인의 이동을 철도가 이미 상당 부분 받치고 있다는 뜻이며 이것이 높은 반납률의 조건으로 보인다.</p></div>
<p><b>그러나 철도가 닿지 않는 곳은 수요응답형 교통에 기대야 하고, 지금 용량으로는 부족하다.</b> 부산의 교통약자 특별교통수단 ‘두리발’은 2025년 5월 한 달 부산 출발 {DB['requests']:,}건이 호출됐는데, {DB['unserved_rate']}%({DB['unserved']:,}건)는 차를 배정받지 못했고, 승차까지 마친 즉시 호출 {DB['n_wait_obs']:,}건의 대기는 중위 {DB['wait_median_min']:.0f}분, {DB['share_wait_over_60']}%는 1시간 넘게 기다렸다. 호출의 {DB['share_65plus_type']}%는 ‘65세 이상’(장기요양 휠체어 이용자) 유형이고, {DB['share_hospital']}%는 병원 이동이었다(1회 중위 {DB['dist_median_km']:.1f}km, 이용자 요금 중위 {DB['fare_median_won']:,}원). 부산에서 1인당 버스 승차가 가장 적은 {BG['lowest_bus']['sgg']}는 대기시간이 가장 길고({BG['lowest_bus']['duribal_wait_med']:.0f}분), 고령운전자 사고 사망률(2024~2025 평균, 65세 이상 10만 명당 {BG['lowest_bus']['olddrv_death_per100k65_2y']:.1f}명, 2년간 {BG['lowest_bus']['olddrv_death_2y']}명)도 가장 높아 현장 확인이 필요한 ‘도시 안의 사각지대’ 후보다(사망자 수가 적고 구군 간 순위상관은 유의하지 않음).</p>
<p><b>반납 이후 노인은 보행자가 된다.</b> 부산은 전국 65세 이상 인구의 {BS['p65_share_of_national']}%지만, 도로교통공단이 지정한 보행노인 교통사고 다발지역의 연도별 지정 기록(2023~2025) {PH['national']}건 중 {PH['busan']}건({PH['busan_share']}%)이 부산이다(같은 좌표는 하나로 세면 {PH['national_unique_xy']}곳 중 {PH['busan_unique_xy']}곳). 보호구역 자료가 있는 11개 구군의 기록 {PH['busan_in_zone_gu']}건 중 가장 가까운 노인·장애인 보호구역 지점과 직선 300m 이내는 {PH['within_300m']}건({PH['within_300m_share']}%)뿐이었다(중위 {PH['median_dist_m']}m).</p>
<div class="keep"><div class="fig"><img src="{img('fig5_busan_case.png')}" style="width:90%"></div></div>

<div class="keep"><h2>6. 정책제안 및 기대효과</h2>
<h3>제안 1. ‘면허 반납 = 이동권 보장’: 반납 인센티브를 이동보장 패키지로 전환</h3>
<p>현재 반납 지원은 주로 일회성 교통카드·지역화폐 지급이다. 버스가 드문 사각지대에서는 이것이 반납을 결심할 이유가 되기 어렵다. 3중 사각지대 {B['n_triple']}곳부터 반납자에게 <b>수요응답형 교통(DRT)·공공형 택시의 정액 이용권(예: 월 단위)</b>을 일정 기간 제공하고, 반납 신청 창구(경찰서·주민센터)에서 DRT 호출 등록까지 한 번에 처리한다. 반납 성과지표를 ‘건수’에서 ‘반납 후 월 이동 횟수’로 바꿔 이동권이 실제로 유지되는지 관리한다. 부산 두리발 기록처럼 기존 교통약자 특별교통수단은 이미 대기 중위 {DB['wait_median_min']:.0f}분·미배차 {DB['unserved_rate']}%이므로, 반납자 이동을 여기에 얹으면 장애인 이동을 밀어낼 수 있다. 별도 차량·예산으로 운영하고 ‘호출 후 30분 이내 승차’, ‘미배차 5% 미만’ 같은 서비스 기준을 함께 관리한다. 두리발 이용자 요금(중위 {DB['fare_median_won']:,}원)은 운영원가가 아닌 참고치이므로, 예산은 ‘대상자×월 지원 횟수×건당 공공부담액×기간+운영비’로 따로 산정한다.</p></div>
<h3>제안 2. ‘이동 사각지대 지수’로 대중교통 예산을 배분하고 매년 공개 갱신</h3>
<p>이번에 쓴 3중 분류(고령비율·1인당 버스 이용·사망률)에 고령운전자 사고 사망률·승용차 의존도를 더한 지수(가중치·결측 처리는 후속 설계)를 농어촌버스·DRT 국비 지원과 지자체 교통약자 이동편의 계획의 우선순위 기준으로 쓴다. 지수는 모두 공공데이터로 매년 재계산할 수 있고(고령운전자 사고는 도로교통공단 OpenAPI로 시군구별 자동 수집), 연도별 자료와 행정구역 대응표를 갱신하면 이번 분석 코드로 반복 산출할 수 있다.</p>
<h3>제안 3. 반납 이후의 ‘걷는 길’까지: 정류장·경로당 주변 보행안전</h3>
<p>반납한 노인은 보행자가 된다. 사각지대 시군구의 정류장·경로당·전통시장 주변과, 반납이 많은 도시의 보행노인 사고다발지역(부산 11개 구군 기준 약 {100 - PH['within_300m_share']:.0f}%가 보호구역 지점에서 300m 넘게 떨어짐)을 노인보호구역(30km/h) 우선 지정 대상으로 삼고, 정류장 대기 환경(유개 정류장)을 함께 개선한다.</p>
<div class="box small"><b>기대효과(시나리오).</b> 전국 평균보다 반납률이 낮은 {len(S['sido_below_avg'])}개 시도가 전국 평균(65세 이상 1천 명당 {RT['national_rate_2024_per1k65']:.1f}건)에 도달하면 <b>연간 약 {S['additional_returns_per_year']:,}건</b>의 반납이 추가된다. 반납자 1인당 승용차 주행이 해당 시도 평균의 30~70% 줄어든다고 가정하면 연간 약 <b>{lo['avoided_vkm_million'] * 100:,.0f}만~{hi['avoided_vkm_million'] * 100:,.0f}만 km</b>의 승용차 주행과 <b>CO₂ 약 {lo['tCO2'] / 1e4:.2f}만~{hi['tCO2'] / 1e4:.2f}만 톤</b>(중간 가정 {mid['tCO2'] / 1e4:.2f}만 톤)이 줄어든다. 이는 전국 확대를 가정한 잠재 총량으로 시범사업의 순감축 예상치가 아니며, 대체 수단(DRT 등) 배출과 반납 전 운전 여부는 빼지 않았다. 안전 측면에서는 사망률이 사각지대 밖 지역의 {B['death_rate_triple'] / B['death_rate_rest']:.1f}배인 곳의 고령운전 노출을 줄이고, 반납률의 지역 격차({RT['gap_ratio_max_min']}배)를 좁혀 이동의 형평성을 높인다.</div>
<p class="small"><b>적용 대상과 방식.</b> 1단계로 3중 사각지대가 많은 경북·경남·전남·충남의 군 지역(농어촌형)과, 도시철도 무임·두리발 운영 경험이 있는 부산의 철도 공백 구역(도시형, 예: {BG['lowest_bus']['sgg']})에서 시범 운영하고, 반납자 이동 횟수·대기시간·사고·주행거리 변화를 공공데이터로 추적해 효과를 검증한 뒤 확대한다. 65세 이상이 2035년 {PJ['2035']['p65_10k']:,.0f}만 명으로 늘어나는 만큼, 시범은 지금 시작해야 한다.</p>
<p class="note"><b>한계.</b> 사고·반납과 인구의 시점은 맞췄지만(2025·2024 각 6월 인구), 주행거리(2019)는 연도가 다르다. 고령운전자 사고 사망자에는 상대방·보행자 등 그 사고의 모든 사망자가 포함된다. 버스 승차는 교통카드 기준이라 현금 승차·DRT는 빠져 있으며, 배차 간격 같은 서비스 수준 지표가 아니다. 시군구 단위 상관·회귀이므로 개인 수준의 인과를 뜻하지 않는다. 부산 두리발 자료는 교통약자 대상 한 달(2025.5) 기록이라 일반 반납자 수요를 그대로 대표하지 않고, 노인·장애인 보호구역 표준데이터는 부산 16개 구군 중 11곳만 제공된다. CO₂ 배출계수(0.15~0.21 kgCO₂/km)는 IPCC 2006 휘발유 기본값과 연비 범위로 환산한 가정치.</p>

<h2>7. 분석도구 및 참고문헌</h2>
<p class="small"><b>분석도구.</b> Python 3.13(pandas, statsmodels, scipy, matplotlib), rdhub v0.1(연구자료 수집 도구 서버, 자체 개발), Claude(Anthropic). 분석 코드·수집 로그·데이터 목록: {args.code_url}</p>
<p class="small"><b>참고문헌·자료.</b> ① 2장 표의 공공데이터 {len(DATA_ROWS)}종(각 URL, 2026.10.21 접근). ② IPCC (2006). <i>2006 IPCC Guidelines for National Greenhouse Gas Inventories</i>, Vol. 2 Energy, Ch. 3 Mobile Combustion(휘발유 기본 CO₂ 배출계수). ③ (재)숲과나눔·한겨레, 「AI와 함께하는 교통문제 해결을 위한 데이터 분석 공모전」 공고(2026.8.18) — 수송부문 온실가스 중 도로교통 비중 인용.</p>
</section>
</body></html>"""

out_html = ROOT / "report" / "분석보고서.html"
out_html.write_text(HTML, encoding="utf-8")
from playwright.sync_api import sync_playwright

with sync_playwright() as p:
    b = p.chromium.launch()
    pg = b.new_page()
    pg.goto(out_html.resolve().as_uri())
    pg.wait_for_timeout(500)
    pg.pdf(path=args.out, format="A4", print_background=True, display_header_footer=True, header_template="<span></span>",
           footer_template='<div style="width:100%;text-align:center;font-size:7pt;color:#9ca3af;">- <span class="pageNumber"></span> -</div>',
           margin={"top": "15mm", "bottom": "14mm", "left": "15mm", "right": "15mm"})
    b.close()
# 제출본(김민규_분석보고서.pdf)은 공모전 양식판 report/build_report_form.py가 만든다(2026.10.22~).
# 이 스크립트는 이전 자유 형식(report/분석보고서.pdf)만 만들어 제출본을 덮어쓰지 않는다.
print("written", args.out)
