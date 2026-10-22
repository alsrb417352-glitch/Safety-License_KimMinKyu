"""분석보고서 PDF — 공모전 배포 양식(교통 제안서/붙임2-분석보고서최종.hwp)에 맞춘 판.

양식 그대로: 머리말 주최 로고, 녹색 띠 제목(‘- AI와 함께하는 … 공모전 -’ / ‘분석보고서’),
2열 표(회색 항목 칸 22mm + 내용 칸 126mm)와 항목 순서(이름/팀명 → 주제 → 분석 배경 및 목적 → 활용 데이터
→ 분석과정 및 방법 → AI 기술 활용 → 분석 내용 및 결과 → 정책제안 및 기대효과 → 분석도구 및 참고문헌
→ 분석결과 이미지), ‘활용 데이터’ 칸 안의 목록 표(활용 데이터(명)·제공기관(명)·출처[플랫폼(명)·URL]),
쪽 설정(A4, 위 20mm+머리말 15mm, 좌우 30mm, 아래 15mm+꼬리말 15mm), 글꼴(나눔바른고딕).
양식 유의사항의 ‘제시한 항목 외 추가 내용은 별도 제목’에 따라 ‘분석의 한계’ 칸을 따로 두었다.

모든 수치는 outputs/results.json·results_busan.json·verification.json·tables에서 읽어 채운다(손으로 옮겨 적지 않음).
사용: python report/build_report_form.py [--name "이름/팀명"] [--code-url https://github.com/...]
출력: report/분석보고서_양식.pdf, 제출용 report/<팀명>_분석보고서.pdf (Playwright Chromium 필요)
기존 자유 형식 보고서는 report/build_report.py(→ report/분석보고서.pdf)로 그대로 만들 수 있다.
"""
from __future__ import annotations

import argparse
import base64
import json
import shutil
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
ASSETS = Path(__file__).resolve().parent / "assets"
R = json.loads((ROOT / "outputs" / "results.json").read_text(encoding="utf-8"))
FIG = ROOT / "outputs" / "figures"
TAB = ROOT / "outputs" / "tables"
calls = [json.loads(l) for f in ("tool_calls.jsonl", "tool_calls_api.jsonl") if (ROOT / "logs" / f).exists()
         for l in (ROOT / "logs" / f).read_text(encoding="utf-8").splitlines() if l.strip()]

ap = argparse.ArgumentParser()
ap.add_argument("--name", default="김민규 (팀명: 안전 면허)")
ap.add_argument("--team", default="안전 면허", help="제출 파일명(팀명_분석보고서.pdf)에 쓸 팀명")
ap.add_argument("--code-url", default="https://github.com/alsrb417352-glitch/elderly-mobility-blindspot_KimMinKyu")
ap.add_argument("--out", default=str(ROOT / "report" / "분석보고서_양식.pdf"))
args = ap.parse_args()


def b64(p: Path) -> str:
    return "data:image/png;base64," + base64.b64encode(p.read_bytes()).decode()


def img(name: str) -> str:
    return b64(FIG / name)


A, RT, Q, B, S = R["age"], R["returns"], R["quintiles"], R["blindspots"], R["scenario"]
reg = pd.read_csv(TAB / "table_regression_nb.csv")


def irr(model, term):
    return reg[(reg.model == model) & (reg.term == term)].iloc[0]


r_s65 = irr("모형2(+주행거리)", "share65")
r_vkt = irr("모형2(+주행거리)", "vkt_car_private")
r_bus1 = irr("모형1", "lbus")
r_bus2 = irr("모형2(+주행거리)", "lbus")
r_od_bus = irr("모형3(고령운전자 사고 사망)", "lbus")
r_od_vkt = irr("모형3(고령운전자 사고 사망)", "vkt_car_private")
bl = pd.read_csv(TAB / "table_blindspots.csv")
top = bl.head(10)
n_calls = len(calls)
tools_used = sorted({c["tool"] for c in calls})
mid = S["range"]["mid"]
lo, hi = S["range"]["low"], S["range"]["high"]
ret_by_year = RT["by_year_65plus"]
_sp = pd.read_csv(ROOT / "data" / "processed" / "sido_panel.csv").sort_values("return_rate_2024_per1k65", ascending=False)
TOP3 = _sp["sido"].head(3).tolist()
BOT6 = _sp["sido"].tail(6).tolist()[::-1]
V = json.loads((ROOT / "outputs" / "verification.json").read_text(encoding="utf-8"))
BU = json.loads((ROOT / "outputs" / "results_busan.json").read_text(encoding="utf-8"))
OBS = B["olddrv"]
ORT = R["olddrv_by_region_type"]
DB, BG, BS, PH, PJ, SF = BU["duribal"], BU["busan_gu"], BU["busan_sido"], BU["ped_hotspots"], BU["projection"], BU["subway_free"]
OD = V["older_drivers"]
VC = {r["항목"]: (r["초안(2026.9 인구 파일)"], r["검증(KOSIS API 2025.6·2024.6)"]) for r in V["denominator"]["comparison"]}
LG = V.get("lgstat") or {}
by_sido = ", ".join(f"{k} {v}" for k, v in B["by_sido"].items())
PILOT_SIDO = "·".join(k for k, _ in sorted(B["by_sido"].items(), key=lambda kv: -kv[1])[:4])   # 사각지대가 많은 시도 4곳
PILOT_EX = "·".join(top["sgg"].head(3).str.replace(r"[군시구]$", "", regex=True))               # 사망률 상위 사각지대 3곳

# 활용 데이터 목록(양식 내부 표: 활용 데이터(명) · 제공기관(명) · 출처[플랫폼(명) · URL])
DATA_ROWS = [
    ("시도 시군구별 교통사고 통계(2025)", "한국도로교통공단", "공공데이터포털", "https://www.data.go.kr/data/15070297/fileData.do"),
    ("사상자 연령층별 성별 교통사고 통계(2025)", "한국도로교통공단", "공공데이터포털", "https://www.data.go.kr/data/15070293/fileData.do"),
    ("시도 경찰청별 고령운전자 자진반납 현황(2015~2024)", "경찰청", "공공데이터포털", "https://www.data.go.kr/data/15065567/fileData.do"),
    ("행정구역(시군구)별/1세별 주민등록인구(2024.6·2025.6)", "행정안전부", "KOSIS OpenAPI", "https://kosis.kr/statHtml/statHtml.do?orgId=101&tblId=DT_1B04006"),
    ("가해자 연령층별 교통사고(2015~2025)", "경찰청", "KOSIS OpenAPI", "https://kosis.kr/statHtml/statHtml.do?orgId=132&tblId=DT_V_MOTA_021"),
    ("지자체별 대상 교통사고 통계(2024·2025)", "한국도로교통공단", "공공데이터포털 OpenAPI", "https://www.data.go.kr/data/15056770/openapi.do"),
    ("보행노인 교통사고 다발지역(2023~2025)", "한국도로교통공단", "공공데이터포털 OpenAPI", "https://www.data.go.kr/data/15057666/openapi.do"),
    ("성 및 연령별 추계인구(중위, 2022~2072)", "통계청", "KOSIS", "https://kosis.kr/statHtml/statHtml.do?orgId=101&tblId=DT_1BPA001"),
    ("시군구별 정류장평균이용량(2025, 교통카드)", "국토교통부", "공공데이터포털", "https://www.data.go.kr/data/15162142/fileData.do"),
    ("전국 버스정류장 위치정보(2025)", "국토교통부", "공공데이터포털", "https://www.data.go.kr/data/15067528/fileData.do"),
    ("용도별 차종별 시군구별 일평균 자동차 주행거리(2019)", "한국교통안전공단", "공공데이터포털", "https://www.data.go.kr/data/15088483/fileData.do"),
    ("부산도시철도 월별 역별 권종별 승하차(2014~2024)", "부산교통공사", "부산 Big-데이터웨이브", "https://data.busan.go.kr/bdip/opendata/detail.do?publicdatapk=15128561"),
    ("부산 교통약자 이동지원 차량 운영현황(2025.5)", "부산시설공단", "부산 Big-데이터웨이브", "https://data.busan.go.kr/bdip/opendata/detail.do?publicdatapk=15147515"),
    ("전국 노인·장애인 보호구역 표준데이터(부산)", "부산 각 구군", "부산 Big-데이터웨이브", "https://data.busan.go.kr/bdip/opendata/detail.do?publicdatapk=15034532"),
    ("지역별(행정동) 성별 연령별 주민등록 인구수(2026.9.30)", "행정안전부", "공공데이터포털", "https://www.data.go.kr/data/15097972/fileData.do"),
]
CIRC = "①②③④⑤⑥⑦⑧⑨⑩⑪⑫⑬⑭⑮"
N_API = sum(1 for r in DATA_ROWS if "OpenAPI" in r[2])
N_BUSAN = sum(1 for r in DATA_ROWS if "Big-데이터웨이브" in r[2])
N_FILE = len(DATA_ROWS) - N_API - N_BUSAN
data_rows_html = "\n".join(
    f"<tr><td>{CIRC[i]} {n}</td><td>{o}</td><td>{p}</td><td class='url'>{u}</td></tr>"
    for i, (n, o, p, u) in enumerate(DATA_ROWS))
top_rows = "\n".join(
    f"<tr><td>{i + 1}</td><td class='l'>{r.sido} {r.sgg}</td><td>{r.share65:.1f}%</td>"
    f"<td>{('없음' if pd.isna(r.bus_board_pc) else f'{r.bus_board_pc:.3f}')}</td><td>{r.death_per100k:.1f}</td><td>{int(r.lg_olddrv_death_2025)}</td></tr>"
    for i, r in top.reset_index(drop=True).iterrows())

CODE_LINK = (f'<a href="{args.code_url}" style="color:#1d4ed8;text-decoration:none">{args.code_url}</a>'
             if args.code_url.startswith("http") else args.code_url)
FONT_DIR = (ASSETS / "fonts").resolve().as_uri()
LOGO_FOREST = b64(ASSETS / "form" / "logo_forest.png")
LOGO_HANI = b64(ASSETS / "form" / "logo_hani.png")

CSS = f"""
@font-face {{ font-family: 'NBG'; font-weight: 400; src: local('NanumBarunGothic'), local('나눔바른고딕'), url('{FONT_DIR}/NanumBarunGothic.woff2') format('woff2'); }}
@font-face {{ font-family: 'NBG'; font-weight: 700; src: local('NanumBarunGothic Bold'), local('NanumBarunGothicBold'), local('나눔바른고딕 Bold'), url('{FONT_DIR}/NanumBarunGothicBold.woff2') format('woff2'); }}
@page {{ size: A4; margin: 35mm 30mm 30mm 30mm; }}
* {{ box-sizing: border-box; -webkit-print-color-adjust: exact; print-color-adjust: exact; }}
html, body {{ margin: 0; padding: 0; }}
body {{ font-family: 'NBG', 'Noto Sans CJK KR', sans-serif; color: #000; font-size: 8.9pt; line-height: 1.5; width: 150mm; }}
b {{ font-weight: 700; }}
p {{ margin: 0 0 1.4mm; text-align: justify; word-break: normal; overflow-wrap: anywhere; }}
/* 양식 제목 띠(1열 3행 표: 녹색 띠 / 제목 / 녹색 띠) */
.formhead {{ width: 150mm; border-collapse: collapse; margin: 0 0 4mm; }}
.formhead td {{ padding: 0.49mm; text-align: center; }}
.formhead .bar1 {{ background: #83b582; height: 3.0mm; }}
.formhead .bar2 {{ background: #83b582; height: 3.5mm; }}
.formhead .ttl {{ height: 14.8mm; }}
.formhead .t1 {{ font-size: 13pt; font-weight: 700; line-height: 1.6; }}
.formhead .t2 {{ font-size: 16pt; font-weight: 700; line-height: 1.6; }}
/* 본표(2열: 항목 22.09mm + 내용 125.92mm). 쪽이 넘어가는 칸도 한글처럼 쪽마다 테두리를 닫도록
   표는 오른쪽·아래, 칸은 위·왼쪽 선을 맡고 box-decoration-break: clone으로 조각마다 다시 그린다. */
table.form {{ width: 148mm; border-collapse: separate; border-spacing: 0; table-layout: fixed;
  border-right: 0.12mm solid #000; border-bottom: 0.12mm solid #000; -webkit-box-decoration-break: clone; box-decoration-break: clone; }}
table.form > tbody > tr > td {{ border-top: 0.12mm solid #000; border-left: 0.12mm solid #000; padding: 0.5mm 1.8mm; vertical-align: middle;
  -webkit-box-decoration-break: clone; box-decoration-break: clone; }}
table.form > tbody > tr > td.k {{ width: 22.09mm; background: #f2f2f2; text-align: center; font-size: 11pt; line-height: 1.5; word-break: keep-all; }}
table.form > tbody > tr > td.k.top {{ vertical-align: top; padding-top: 2.5mm; }}
table.form > tbody > tr > td.v {{ width: 125.92mm; padding: 1.6mm 1.8mm 1.2mm; }}
.ttlrow td.v {{ font-size: 11pt; }}
h4 {{ font-size: 9.4pt; margin: 1.6mm 0 0.6mm; color: #000; }}
h4:first-child {{ margin-top: 0.4mm; }}
.lead {{ font-weight: 700; }}
ul {{ margin: 0 0 1.4mm; padding-left: 4mm; }} li {{ margin-bottom: 0.6mm; text-align: justify; }}
.kpis {{ display: flex; gap: 2mm; margin: 0.6mm 0 2mm; }}
.kpi {{ flex: 1; border: 0.2mm solid #b9cdb8; background: #f6faf5; padding: 1.4mm 2mm; }}
.kpi b {{ display: block; font-size: 11.5pt; color: #c0392b; line-height: 1.25; white-space: nowrap; }}
.kpi span {{ font-size: 7.2pt; color: #333; line-height: 1.35; display: block; }}
/* 활용 데이터 내부 표(양식: 활용 데이터(명) · 제공기관(명) · 출처[플랫폼(명) · URL]) */
table.data {{ width: 121mm; border-collapse: collapse; table-layout: fixed; margin: 1mm 0 1.2mm; }}
table.data th, table.data td {{ border: 0.12mm solid #000; padding: 0.45mm 1mm; font-size: 7.1pt; line-height: 1.32; vertical-align: middle; word-break: keep-all; overflow-wrap: anywhere; }}
table.data th {{ background: #f2f2f2; font-weight: 700; text-align: center; }}
table.data td.url {{ font-size: 6.3pt; word-break: break-all; }}
.note {{ font-size: 7.4pt; color: #333; line-height: 1.42; text-align: left; }}
.box {{ border: 0.2mm solid #b9cdb8; background: #f6faf5; padding: 1.4mm 2.2mm; margin: 1.2mm 0; }}
.prompt {{ font-size: 7.8pt; background: #f4f4f4; border-left: 0.6mm solid #83b582; padding: 0.7mm 2mm; margin: 0.8mm 0; line-height: 1.42; }}
.fig {{ margin: 1.2mm 0 2.4mm; text-align: center; break-inside: avoid; }}
.fig img {{ width: 100%; display: block; }}
.figcap {{ font-size: 7.2pt; color: #333; text-align: left; margin-top: 0.6mm; }}
.two {{ display: flex; gap: 2.5mm; align-items: flex-start; break-inside: avoid; }}
table.tight {{ width: 100%; border-collapse: collapse; }}
table.tight th, table.tight td {{ border: 0.12mm solid #555; font-size: 6.7pt; padding: 0.45mm 0.7mm; text-align: center; line-height: 1.3; }}
table.tight th {{ background: #f2f2f2; }}
table.tight td.l {{ text-align: left; white-space: nowrap; }}
.keep {{ break-inside: avoid; }}
tr.keeprow {{ break-inside: avoid; }}
.refs {{ font-size: 8pt; }}
.refs p {{ text-align: left; }}
.refs ol {{ margin: 0.4mm 0 0; padding-left: 4.5mm; }}
"""

HTML = f"""<!doctype html><html lang="ko"><head><meta charset="utf-8"><title>{args.team}_분석보고서</title>
<style>{CSS}</style></head><body>

<table class="formhead">
  <tr><td class="bar1"></td></tr>
  <tr><td class="ttl"><div class="t1">- AI와 함께하는 교통문제 해결을 위한 데이터 분석 공모전 -</div><div class="t2">분석보고서</div></td></tr>
  <tr><td class="bar2"></td></tr>
</table>

<table class="form"><tbody>

<tr class="ttlrow keeprow"><td class="k">이름/팀명</td><td class="v">{args.name}</td></tr>

<tr class="ttlrow keeprow"><td class="k">주제</td><td class="v"><b>운전대를 놓은 노인은 어디로 가는가</b><br>
<span style="font-size:9.2pt">고령운전자 면허 반납의 지역 격차와 ‘이동 사각지대’ 진단, 그리고 반납자 이동보장 정책 제안</span></td></tr>

<tr><td class="k top">분석 배경<br>및 목적</td><td class="v">
<div class="kpis">
  <div class="kpi"><b>{A['share_deaths_65plus']}%</b><span>2025년 교통사고 사망자 {A['total_deaths_2025']:,}명 중 65세 이상(인구 비중 {A['share_pop_65plus']}%)</span></div>
  <div class="kpi"><b>{ret_by_year['2015']:,}→{ret_by_year['2024']:,}건</b><span>65세 이상 운전면허 자진반납(2015→2024)</span></div>
  <div class="kpi"><b>{RT['gap_ratio_max_min']}배</b><span>시도별 반납률 격차({RT['max'][0]} {RT['max'][1]:.1f} vs {RT['min'][0]} {RT['min'][1]:.1f}, 65세 이상 1천 명당)</span></div>
</div>
<p><span class="lead">현황.</span> 2025년 교통사고 사망자의 절반 이상({A['share_deaths_65plus']}%)이 65세 이상이며, 인구 10만 명당 사망률은 {A['rate_65plus']:.1f}명으로 65세 미만({A['rate_under65']:.1f}명)의 {A['ratio_65_vs_under65']:.1f}배다(그림 1). 65세 이상 운전자가 낸 사고의 사망자 비중은 2015년 {OD['share_deaths_by_65_driver']['2015']}%에서 2025년 {OD['share_deaths_by_65_driver']['2025']}%로 늘었다(경찰청, KOSIS API). 정부·지자체는 대책으로 <b>운전면허 자진반납</b>을 장려했고 반납은 2015년 {ret_by_year['2015']:,}건에서 2024년 {ret_by_year['2024']:,}건으로 늘었다. 65세 이상 인구는 2035년 {PJ['2035']['p65_10k']:,.0f}만 명(2025년 대비 +{PJ['growth_p65_2025_2035_pct']}%)이 되어, 지금 반납률만 유지돼도 연간 반납은 약 {PJ['returns_2035_at_2024_rate'] / 1e4:.1f}만 건으로 늘어난다(통계청 장래인구추계).</p>
<p><span class="lead">문제.</span> 기존 정책은 반납 ‘건수’를 성과로 볼 뿐, 반납한 노인이 <b>무엇으로 이동하는지</b>는 묻지 않는다. 버스가 하루 몇 번 다니지 않는 농어촌에서 반납은 병원·장보기·일자리로 가는 길을 잃는 일이다. 그래서 반납이 가장 필요한 지역일수록 반납하지 못하고 위험한 운전을 이어가는 <b>역설</b>이 생길 수 있다. 사고 통계와 교통 통계가 따로 관리되어 기존 정책에서 잘 드러나지 않았던 문제다.</p>
<p><span class="lead">목적.</span> 공공데이터를 결합해 ① 반납률의 지역 격차가 대중교통 이용과 어떤 관계인지, ② 고령화·대중교통 공백·높은 교통사망이 겹친 <b>‘이동 사각지대’</b>에 사망이 얼마나 집중되는지 확인하고, ③ 반납을 이동권 보장과 연결하는 정책의 대상 지역과 효과(안전·탄소)를 제시한다.</p>
<p><span class="lead">필요성·참여 동기.</span> 반납은 고령운전 위험과 승용차 주행(수송부문 온실가스의 약 97%가 도로교통)을 함께 줄이는 수단이지만, 대안 교통 없이 권하면 이동격차를 키운다. 이동격차·교통약자·탄소중립이 한 지점에서 만나는 문제라고 보고, 흩어진 공공데이터를 직접 만든 AI 자료 수집 도구로 결합해 ‘어디부터 지원해야 하는지’를 숫자로 보여 주고자 참여했다.</p>
</td></tr>

<tr><td class="k top">활용 데이터</td><td class="v">
<p>공공데이터 <b>{len(DATA_ROWS)}종</b>(개방 파일·통계표 {N_FILE}종, OpenAPI {N_API}종, 부산 Big-데이터웨이브 {N_BUSAN}종)을 227개 시군구·17개 시도 단위로 결합하고, 부산 16개 구군을 사례로 분석했다.</p>
<p class="note"><b>선정 이유.</b> ①②⑥ 시군구·연령별 교통사고 사망과 고령운전자 가해 사고를 직접 측정 · ③ 지역별 면허 반납의 공식 통계 · ④⑤ 사고·반납 연도와 시점을 맞춘 인구 분모와 고령운전자 사고 추이(교차검증) · ⑧ 반납 수요 전망 · ⑨⑩ 전국 시군구를 같은 기준으로 비교할 수 있는 대중교통 이용(교통카드)과 지도 · ⑪ 자동차 의존·탄소 대리지표 · ⑦⑫⑬⑭ 반납 이후의 보행 위험과 대체 교통 실태(부산 사례) · ⑮ 초기 계산의 인구 분모(④로 바꾸기 전후 결과 비교).</p>
<table class="data">
<colgroup><col style="width:36.5mm"><col style="width:22.5mm"><col style="width:19mm"><col style="width:43mm"></colgroup>
<thead><tr><th rowspan="2">활용 데이터(명)</th><th rowspan="2">제공기관(명)</th><th colspan="2">출처</th></tr>
<tr><th>플랫폼(명)</th><th>URL</th></tr></thead>
<tbody>{data_rows_html}</tbody>
</table>
<p class="note"><b>수집 방법·이용조건.</b> 개방 파일은 수집 시 데이터셋 페이지의 이용허락 표시를 기록했고(data/raw/manifest.json), OpenAPI 2종(⑥⑦)과 부산 자료 3종은 이용허락범위 ‘제한 없음’을 확인·기록했다(2026.10.21, data/raw/license_check_20261021.json). KOSIS·공공데이터포털 API는 본인 계정으로 발급·활용신청한 인증키로 호출했다. 원본 파일의 SHA-256, 수집 시각, 원 URL을 data/raw/index.json에 보존했다. 개인정보·민간 비공개 자료는 쓰지 않았고 보고서에는 집계 결과만 제시한다.</p>
</td></tr>

<tr><td class="k top">분석과정<br>및 방법</td><td class="v">
<p><span class="lead">① 수집·검증.</span> 자체 개발한 AI 연구자료 수집 도구(rdhub)로 공공데이터포털 등을 검색하고, 상세 페이지에서 제공기관·수정일·이용조건을 확인한 뒤 배포 파일을 받았다. 받은 파일의 형식을 시그니처로 확인해 오류 페이지(HTML)가 자료로 저장되지 않게 했고, 원본 해시와 출처를 기록했다. 내보내기 후 행 수·값 대조에서 불일치는 0건이었다.</p>
<p><span class="lead">② 전처리(행정구역 정합).</span> 자료마다 기준 연도와 행정구역이 달라 규칙을 정해 맞췄다. 일반구가 있는 시는 시 단위로 합산(시도 합계와 일치 확인), 인천 중·동·서구는 2026년 개편 전후 자료를 잇기 위해 한 단위로 묶고, 군위군은 대구로, 옛 명칭(인천 남구→미추홀구)은 새 명칭으로 대응해 <b>227개 시군구·17개 시도 패널</b>을 만들었다. 교통카드 정류장 자료가 없는 4개 군은 0으로 채우지 않고 결측으로 두었다(5분위·회귀에서 제외, 사각지대 분류에서는 ‘공백’으로 간주).</p>
<p><span class="lead">③ 지표.</span> 대중교통 이용 = 정류장별 하루 평균 승차 합 ÷ 주민등록인구(1인당 하루 버스 승차). 교통사고 사망률 = 인구 10만 명당 사망자(2025 사고 ÷ 2025.6 인구). 반납률 = 65세 이상 1천 명당 연간 반납(2024 반납 ÷ 2024.6 65세 이상 인구). 고령운전자 사고율·사망률·치사율 = 65세 이상 운전자가 가해자인 사고 건수(65세 이상 1천 명당)·그 사고의 사망자(65세 이상 10만 명당)·사고 100건당 사망자(2025, 도로교통공단 OpenAPI). 자동차 의존 = 비사업용 승용차 1대당 일평균 주행거리(2019).</p>
<p><span class="lead">④ 분석 기법.</span> (가) 시도별 반납률과 버스 이용의 <b>스피어만 순위상관</b> (나) 시군구를 버스 이용 <b>5분위</b>로 나눈 사망률 비교 (다) <b>음이항 회귀</b>(종속: 사망자 수, 인구 offset / 설명: 65세 이상 비율, log 1인당 버스 승차, 승용차 주행거리, 지역유형) — 과대산포 때문에 포아송 대신 사용 (라) 고령비율 상위 1/3·버스 이용 하위 1/3·사망률 상위 1/3을 모두 충족하는 <b>‘3중 이동 사각지대’</b> 유형화 (마) 반납률 격차 해소 <b>시나리오</b>(추가 반납·회피 주행거리·CO₂ 범위) (바) <b>부산 사례</b>: 도시철도 권종별 승하차(2014~2024)로 무임 비중, 두리발 운행기록 {DB['requests']:,}건으로 구군별 대기·미배차, 보행노인 사고다발지역과 노인보호구역의 거리 계산.</p>
</td></tr>

<tr class="keeprow"><td class="k top">AI 기술<br>활용</td><td class="v">
<p><span class="lead">사용 서비스.</span> Claude(Anthropic, 대화형 AI), ChatGPT(OpenAI, ChatGPT PC 앱·Codex), <b>rdhub</b>(본인이 AI와 함께 개발한 연구자료 수집 도구 서버, MCP·CLI로 AI가 호출).</p>
<p><span class="lead">활용 범위.</span> ① <b>데이터 탐색·수집</b>: AI가 rdhub 도구를 {n_calls}회 호출<span style="font-size:7.4pt">({', '.join(tools_used)})</span>해 카탈로그 검색 → 원문 확인(제공기관·원출처·이용조건) → 파일 수집 → 해시·버전 기록 → 표 정리 → 내보내기 검증을 수행했고, 모든 호출을 로그(logs/tool_calls*.jsonl)로 남겼다. 로그인이 필요한 자료는 사용자가 로그인만 하고, AI가 브라우저에서 공공데이터포털 자동승인 활용신청(도로교통공단 API 2종), 전국 시군구 코드 순회 호출({LG.get('rows', 0):,}행), 부산 Big-데이터웨이브 자료 수집을 수행했다. ② 분석 코드 작성(Python)과 결과 해석 초안(Claude). ③ 보고서 문장 초안(Claude). ④ <b>ChatGPT</b>: 자료 수집 도구 rdhub의 코드 작성 보조(Codex)와 수집할 자료 탐색 보조.</p>
<p><span class="lead">검증.</span> AI가 수치를 기억으로 채우지 못하도록 보고서의 모든 수치는 분석 코드를 다시 실행해 나온 결과 파일(results.json)에서 자동으로 채웠다. 행정구역 정합 규칙과 미매칭 지역은 로그로 남겨 직접 확인했다. 초안은 2026.9 인구 파일을 분모로 썼으나, KOSIS API로 사고·반납 연도의 6월 인구를 받아 전부 재계산했다(65세 이상/미만 사망률 배수 {VC['65세 이상/미만 사망률 배수'][0]}→{VC['65세 이상/미만 사망률 배수'][1]}, 반납률–버스 ρ {VC['반납률–버스 이용 스피어만 ρ'][0]:.2f}→{VC['반납률–버스 이용 스피어만 ρ'][1]:.2f}, 사각지대 {VC['3중 사각지대 시군구 수'][0]:.0f}→{VC['3중 사각지대 시군구 수'][1]:.0f}곳, 결론 유지). 2025년 사망자 {OD['total_deaths_2025_police']:,}명은 경찰청 통계와 도로교통공단 파일이 {'일치' if OD['total_deaths_match'] else '불일치'}했고, API로 받은 시군구 사망자·사고건수는 개방 파일과 {LG.get('sgg_death_match', 0)}/{LG.get('sgg_compared', 0)}곳 일치, 고령운전자 사고 사망자 {LG.get('olddrv_deaths_2025_api', 0):,}명은 경찰청 통계와 {'일치' if LG.get('olddrv_match_police') else '불일치'}했다. 외부 AI 서비스(Claude·ChatGPT)에는 공개 집계 통계·코드·문서만 입력했고 개인정보·비공개 자료는 입력하지 않았으며, 각 서비스의 데이터 저장·학습 활용 조건을 확인한 뒤 사용했다. API 인증키는 PC의 보호 저장소에만 두어 AI에 전달되지 않는다.</p>
<p class="note" style="margin-bottom:0.4mm"><b>주요 프롬프트(요지)</b></p>
<div class="prompt">“공모전 공고와 분석보고서 양식을 보고, 이동격차·교통약자·탄소중립을 함께 다룰 수 있으면서 기존 정책에서 드러나지 않은 교통문제를 주제로 정해. 공공데이터로 검증 가능한지부터 확인해.”</div>
<div class="prompt">“rdhub로 고령인구·교통사고·면허반납·버스 이용·주행거리 자료를 찾아 수집해. 각 자료의 제공기관, 수정일, 이용허락범위를 원문에서 확인하고, 파일이 아니라 오류 페이지가 오면 실패로 처리해.”</div>
<div class="prompt">“버스 이용과 사망률의 관계를 인과로 단정하지 말고, 고령화·자동차 의존을 함께 넣은 음이항 회귀로 확인해. 유의하지 않으면 그대로 보고해.”</div>
<div class="prompt">“도로교통공단 API의 시군구별 고령운전자 사고로 사각지대 진단을 다시 확인해. 사고 건수와 사망을 나눠 보고, 부산 자료(무임 이용·두리발 운행기록·보호구역)로 정책을 구체화해.”</div>
</td></tr>

<tr><td class="k top">분석 내용<br>및 결과</td><td class="v">
<h4>결과 ① 면허 반납은 81배 늘었지만, 대중교통이 부족한 지역에서는 절반 수준이다 (그림 2)</h4>
<p>2024년 65세 이상 1천 명당 반납은 {RT['max'][0]}({RT['max'][1]:.1f}건)·{'·'.join(TOP3[1:])}가 높고 {RT['min'][0]}({RT['min'][1]:.1f}건)·{'·'.join(BOT6[1:])}이 낮아 최대 {RT['gap_ratio_max_min']}배 차이가 난다. 시도별 반납률은 1인당 버스 이용과 뚜렷한 양(+)의 순위상관을 보였고(ρ={RT['spearman_bus_vs_return'][0]:.2f}, p={RT['spearman_bus_vs_return'][1]:.3f}), 교통사고 사망률이 높은 시도일수록 반납률이 낮은 경향이 있었다(ρ={RT['spearman_death_vs_return'][0]:.2f}, p={RT['spearman_death_vs_return'][1]:.2f}, 탐색적). <b>반납이 더 필요해 보이는 곳에서 반납이 적다.</b> 반납률이 높은 시도일수록 고령운전자 가해 사고 사망률(2024)이 낮았고(ρ={RT['spearman_return_vs_olddrv_death_2024'][0]:.2f}, p={RT['spearman_return_vs_olddrv_death_2024'][1]:.3f}), 반납률 1위 부산은 {BS['olddrv_death_per100k65_2024']:.2f}명(65세 이상 10만 명당)으로 17개 시도 중 가장 낮아 전국({BS['national_olddrv_death_per100k65_2024']:.2f}명)의 절반에 못 미쳤다(시도 단위 상관이라 인과는 아님).</p>
<h4>결과 ② 버스 이용 하위 20% 시군구의 교통사고 사망률은 상위 20%의 {Q['ratio_q1_q5']:.1f}배 (그림 3)</h4>
<p>버스 이용 1분위 시군구의 사망률은 인구 10만 명당 {Q['death_rate'][0]:.1f}명으로 5분위({Q['death_rate'][4]:.1f}명)의 {Q['ratio_q1_q5']:.1f}배였다. 하위 40%는 인구의 {Q['pop_share_q1q2']}%지만 교통사고 사망의 <b>{Q['death_share_q1q2']}%</b>를 차지한다. <b>고령운전자 사고는 건수는 비슷하고 사망은 {Q['ratio_olddrv_death_q1_q5']:.1f}배</b>다. 65세 이상 1천 명당 고령운전자 가해 사고는 1분위 {Q['olddrv_acc_rate'][0]:.1f}건, 5분위 {Q['olddrv_acc_rate'][4]:.1f}건으로 거의 같지만, 그 사고의 사망자는 65세 이상 10만 명당 {Q['olddrv_death_rate'][0]:.1f}명 대 {Q['olddrv_death_rate'][4]:.1f}명, 사고 100건당 사망은 {Q['olddrv_cfr'][0]:.1f}명 대 {Q['olddrv_cfr'][4]:.1f}명이었다(도로·차종을 맞춘 비교는 아니며 빠른 지방도로·응급 접근성 차이가 가능한 설명). 군 지역 교통사고 사망자의 {ORT['군']['share_of_deaths']}%가 고령운전자 가해 사고에서 나왔다(특별·광역시 구 {ORT['특별·광역시 구']['share_of_deaths']}%).</p>
<p><b>회귀(음이항, n={R['regression_n']['모형2']}~{R['regression_n']['모형1']}).</b> 지역유형을 통제하면 65세 이상 비율 1%p당 사망 위험이 {(r_s65.IRR - 1) * 100:.1f}%(IRR {r_s65.IRR:.3f}, 95% CI {r_s65.IRR_lo:.3f}–{r_s65.IRR_hi:.3f}), 승용차 1대당 일평균 주행거리 1km당 {(r_vkt.IRR - 1) * 100:.1f}%(IRR {r_vkt.IRR:.3f}, p&lt;0.001) 높았다. 버스 이용의 독립 효과는 음(−)의 방향이지만 유의하지 않았다(모형1 p={r_bus1.p:.3f}, 모형2 p={r_bus2.p:.2f}). 고령운전자 사고 사망을 종속변수로 한 모형3도 주행거리(IRR {r_od_vkt.IRR:.3f}, p={r_od_vkt.p:.3f})와 고령비율만 유의했다(버스 p={r_od_bus.p:.2f}). 즉 대중교통 공백은 고령화·자동차 의존과 <b>함께 나타나므로</b>, 정책 대상은 세 조건이 겹친 지역으로 정했다.</p>
<h4>결과 ③ ‘3중 이동 사각지대’ {B['n_triple']}곳: 인구 {B['pop_share_triple']}%, 교통사고 사망 {B['death_share_triple']}% (그림 4)</h4>
<p>고령비율 상위 1/3(≥{B['thresholds']['share65_top_tertile']:.1f}%)·1인당 버스 승차 하위 1/3(≤{B['thresholds']['bus_board_pc_bottom_tertile']:.3f}회)·사망률 상위 1/3(≥{B['thresholds']['death_per100k_top_tertile']:.1f}명)을 모두 충족한 시군구는 {B['n_triple']}곳({by_sido})이다(교통카드 자료가 없는 {'·'.join(x[1] for x in B['observed_only']['nobus'])}을 빼도 {B['observed_only']['n']}곳, 사망 {B['observed_only']['death_share']}%). 이곳 인구는 {B['pop_triple'] / 1e4:.0f}만 명(65세 이상 {B['p65_triple'] / 1e4:.1f}만 명)이고 사망률은 {B['death_rate_triple']:.1f}명으로 나머지 지역({B['death_rate_rest']:.1f}명)의 {B['death_rate_triple'] / B['death_rate_rest']:.1f}배다(사망률이 분류 기준에 포함되어 있어 ‘정책 대상의 규모’를 보여 주는 값). 고령운전자 가해 사고로 보면 이곳은 65세 이상 인구의 {OBS['p65_share_triple']}%이지만 고령운전자 사고 사망자의 <b>{OBS['olddrv_death_share_of_national']}%</b>({OBS['olddrv_deaths_triple']}명)가 나왔다.</p>
<h4>결과 ④ 부산 사례: 반납률 1위 도시가 보여 주는 ‘반납 이후’의 조건과 과제 (그림 5)</h4>
<p><b>운전을 대신할 수단이 있다.</b> 부산은 반납률 전국 1위({BS['return_rate_2024']:.1f}건)이고, 도시철도 승차 중 무임(경로 등) 비중이 2014년 {SF['share']['2014']}%에서 2024년 {SF['share']['2024']}%로 높아졌다(2024년 {SF['free_riders_2024'] / 1e4:,.0f}만 회). 반납자가 옮겨 탔다는 직접 증거는 아니지만, 노인의 이동을 철도가 이미 받치고 있다는 점이 높은 반납률의 조건으로 보인다. <b>그러나 철도가 닿지 않는 곳의 수요응답형 교통은 부족하다.</b> 교통약자 특별교통수단 ‘두리발’은 2025년 5월 {DB['requests']:,}건이 호출됐고 {DB['unserved_rate']}%({DB['unserved']:,}건)는 배차되지 못했으며, 대기는 중위 {DB['wait_median_min']:.0f}분, {DB['share_wait_over_60']}%는 1시간을 넘었다(호출의 {DB['share_hospital']}%가 병원 이동). 1인당 버스 승차가 가장 적은 {BG['lowest_bus']['sgg']}는 대기({BG['lowest_bus']['duribal_wait_med']:.0f}분)와 고령운전자 사고 사망률(2024~2025 평균 {BG['lowest_bus']['olddrv_death_per100k65_2y']:.1f}명)이 모두 가장 높은 ‘도시 안의 사각지대’ 후보다. <b>반납 이후 노인은 보행자가 된다.</b> 부산은 65세 이상 인구의 {BS['p65_share_of_national']}%지만 보행노인 교통사고 다발지역 지정 기록 {PH['national']}건 중 {PH['busan']}건({PH['busan_share']}%)이 부산이며, 보호구역 자료가 있는 11개 구군 기록 중 노인·장애인 보호구역과 300m 이내는 {PH['within_300m_share']}%뿐이었다(중위 {PH['median_dist_m']}m).</p>
</td></tr>

<tr><td class="k top">정책제안<br>및 기대효과</td><td class="v">
<h4>제안 1. ‘면허 반납 = 이동권 보장’: 반납 인센티브를 이동보장 패키지로 전환</h4>
<p>현재 반납 지원은 주로 일회성 교통카드·지역화폐다. 3중 사각지대 {B['n_triple']}곳부터 반납자에게 <b>수요응답형 교통(DRT)·공공형 택시 정액 이용권</b>(예: 월 단위)을 일정 기간 제공하고, 반납 창구(경찰서·주민센터)에서 DRT 호출 등록까지 한 번에 처리한다. 성과지표는 ‘반납 건수’에서 ‘반납 후 월 이동 횟수’로 바꾼다. 기존 교통약자 특별교통수단은 이미 대기 중위 {DB['wait_median_min']:.0f}분·미배차 {DB['unserved_rate']}%(부산 두리발)이므로, 반납자 이동은 별도 차량·예산으로 운영하고 ‘호출 후 30분 내 승차’, ‘미배차 5% 미만’ 같은 서비스 기준을 함께 관리한다.</p>
<h4>제안 2. ‘이동 사각지대 지수’로 대중교통 예산 배분, 매년 공개 갱신</h4>
<p>3중 분류(고령비율·1인당 버스 이용·사망률)에 고령운전자 사고 사망률·승용차 의존도를 더한 지수를 농어촌버스·DRT 국비 지원과 지자체 교통약자 이동편의 계획의 우선순위 기준으로 쓴다. 모든 지표가 공공데이터(고령운전자 사고는 OpenAPI 자동 수집)라 이번 분석 코드로 매년 재산출할 수 있다.</p>
<h4>제안 3. 반납 이후의 ‘걷는 길’: 정류장·경로당 주변 보행안전</h4>
<p>사각지대 시군구의 정류장·경로당·전통시장 주변과, 보호구역에서 떨어진 보행노인 사고다발지역(부산 11개 구군 기준 약 {100 - PH['within_300m_share']:.0f}%가 300m 밖)을 노인보호구역(30km/h) 우선 지정 대상으로 삼고, 정류장 대기 환경(유개 정류장)을 함께 개선한다.</p>
<div class="box keep"><b>기대효과(시나리오).</b> 전국 평균보다 반납률이 낮은 {len(S['sido_below_avg'])}개 시도가 전국 평균(65세 이상 1천 명당 {RT['national_rate_2024_per1k65']:.1f}건)에 도달하면 <b>연간 약 {S['additional_returns_per_year']:,}건</b>의 반납이 추가된다. 반납자 1인당 승용차 주행이 해당 시도 평균의 30~70% 줄어든다고 가정하면 연간 약 <b>{lo['avoided_vkm_million'] * 100:,.0f}만~{hi['avoided_vkm_million'] * 100:,.0f}만 km</b>의 승용차 주행과 <b>CO₂ 약 {lo['tCO2'] / 1e4:.2f}만~{hi['tCO2'] / 1e4:.2f}만 톤</b>(중간 가정 {mid['tCO2'] / 1e4:.2f}만 톤)이 줄어든다(전국 확대 시 잠재 총량, 대체 수단 배출 미차감). 안전 측면에서는 사망률이 나머지 지역의 {B['death_rate_triple'] / B['death_rate_rest']:.1f}배인 곳의 고령운전 노출을 줄이고, 반납률의 지역 격차({RT['gap_ratio_max_min']}배)를 좁혀 이동의 형평성을 높인다.</div>
<p><span class="lead">적용 대상·사례.</span> 1단계로 3중 사각지대가 많은 {PILOT_SIDO}의 군 지역(농어촌형, 예: {PILOT_EX})과, 도시철도 무임·두리발 운영 경험이 있는 부산의 철도 공백 구역(도시형, 예: {BG['lowest_bus']['sgg']})에서 시범 운영한다. 반납자 이동 횟수·대기시간·사고·주행거리 변화를 공공데이터로 추적해 효과를 검증한 뒤 확대한다.</p>
<p><span class="lead">시사점·파급효과.</span> 반납 정책의 성과를 ‘건수’에서 ‘반납 후 이동 유지’로 바꾸면 안전(고령운전 사고)·탄소(승용차 주행)·이동 형평(교통약자)을 한 정책으로 함께 개선할 수 있다. 지수와 분석 코드는 공공데이터만으로 매년 재산출되므로 다른 지자체의 교통약자 이동편의 계획에도 그대로 옮겨 쓸 수 있다. 65세 이상이 2035년 {PJ['2035']['p65_10k']:,.0f}만 명으로 늘어나는 만큼 시범은 지금 시작해야 한다.</p>
</td></tr>

<tr class="keeprow"><td class="k top">분석의<br>한계</td><td class="v">
<p class="note" style="margin:0">사고·반납과 인구의 시점은 맞췄지만(2025·2024 각 6월 인구) 주행거리(2019)는 연도가 다르다. 고령운전자 사고 사망자에는 상대방·보행자 등 그 사고의 모든 사망자가 포함된다. 버스 승차는 교통카드 기준이라 현금 승차·DRT가 빠져 있고, 배차 간격 같은 서비스 수준 지표가 아니다. 시군구 단위 상관·회귀이므로 개인 수준의 인과를 뜻하지 않는다. 두리발 자료는 교통약자 대상 한 달(2025.5) 기록이라 일반 반납자 수요를 그대로 대표하지 않고, 노인·장애인 보호구역 표준데이터는 부산 16개 구군 중 11곳만 있다. CO₂ 배출계수(0.15~0.21 kgCO₂/km)는 IPCC 2006 휘발유 기본값과 연비 범위로 환산한 가정치다.</p>
</td></tr>

<tr class="keeprow"><td class="k top">분석도구<br>및<br>참고문헌</td><td class="v refs">
<p><b>분석도구.</b> Python 3.13(pandas, statsmodels, scipy, matplotlib), rdhub v0.1(연구자료 수집 도구 서버, 자체 개발), Claude(Anthropic), ChatGPT(OpenAI).<br>
<b>분석 코드·수집 로그·데이터 목록:</b><br>{CODE_LINK}</p>
<p style="margin-bottom:0"><b>참고문헌·자료</b></p>
<ol>
<li>‘활용 데이터’ 표의 공공데이터 {len(DATA_ROWS)}종(각 URL, 2026.10.21 접근).</li>
<li>IPCC (2006). <i>2006 IPCC Guidelines for National Greenhouse Gas Inventories</i>, Vol. 2 Energy, Ch. 3 Mobile Combustion — 휘발유 기본 CO₂ 배출계수.</li>
<li>(재)숲과나눔·한겨레 (2026.8.18). 「AI와 함께하는 교통문제 해결을 위한 데이터 분석 공모전」 공고 — 수송부문 온실가스 중 도로교통 비중.</li>
</ol>
</td></tr>

<tr><td class="k top">분석결과<br>이미지<br>(필수)</td><td class="v">
<div class="fig" style="width:82%;margin-left:auto;margin-right:auto"><img src="{img('fig1_age_death_rate.png')}"></div>
<div class="fig"><img src="{img('fig2_license_return.png')}"></div>
<div class="fig"><img src="{img('fig3_bus_quintile_deaths.png')}"></div>
<div class="two">
  <div style="flex:1"><div class="fig" style="margin:0"><img src="{img('fig4_blindspot_map.png')}"></div></div>
  <div style="flex:1">
    <p class="figcap" style="margin:0 0 0.8mm"><b>표. 3중 이동 사각지대 상위 10곳</b>(사망률 순)</p>
    <table class="tight"><tr><th>#</th><th>시군구</th><th>65세+</th><th>1인당<br>버스승차</th><th>사망률</th><th>고령운전자<br>사고 사망</th></tr>
    {top_rows}
    </table>
    <p class="figcap">사망률: 인구 10만 명당(2025). 버스 승차: 1인당 하루(2025, 교통카드). 고령운전자 사고 사망: 65세 이상 운전자가 가해자인 사고의 사망자 수(명, 2025). ‘없음’은 교통카드 정류장 자료가 없는 군. 전체 {B['n_triple']}곳 목록은 outputs/tables/table_blindspots.csv.</p>
  </div>
</div>
<div class="fig" style="margin-top:2.4mm"><img src="{img('fig5_busan_case.png')}"></div>
</td></tr>

</tbody></table>
</body></html>"""

HEADER = f"""<div style="position:relative;width:210mm;height:35mm;margin:0;padding:0;-webkit-print-color-adjust:exact;">
<img src="{LOGO_HANI}" style="position:absolute;left:0.2mm;top:2.2mm;width:21.52mm;height:6.61mm;">
<img src="{LOGO_FOREST}" style="position:absolute;left:136.16mm;top:21.1mm;width:44.95mm;height:8.72mm;">
</div>"""
FOOTER = """<div style="width:210mm;text-align:center;font-size:8pt;color:#555;font-family:'Noto Sans CJK KR',sans-serif;margin-bottom:8mm;">- <span class="pageNumber"></span> -</div>"""

out_html = ROOT / "report" / "분석보고서_양식.html"
out_html.write_text(HTML, encoding="utf-8")
from playwright.sync_api import sync_playwright  # noqa: E402

with sync_playwright() as p:
    b = p.chromium.launch()
    pg = b.new_page()
    pg.goto(out_html.resolve().as_uri())
    pg.evaluate("document.fonts.ready")
    pg.wait_for_timeout(500)
    pg.pdf(path=args.out, format="A4", print_background=True, display_header_footer=True,
           header_template=HEADER, footer_template=FOOTER,
           margin={"top": "35mm", "bottom": "30mm", "left": "30mm", "right": "30mm"})
    b.close()
SUBMIT = ROOT / "report" / f"{args.team}_분석보고서.pdf"   # 제출 파일명 규칙: 팀명(또는 이름)_분석보고서.pdf
if Path(args.out).resolve() != SUBMIT.resolve():
    shutil.copyfile(args.out, SUBMIT)
print("written", args.out, "and", SUBMIT)
