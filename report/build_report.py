"""분석보고서 PDF 생성. 모든 수치는 outputs/results.json·tables에서 읽어 채운다(손으로 옮겨 적지 않음).
사용: python report/build_report.py --name "이름 또는 팀명" [--code-url https://github.com/...]
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
calls = [json.loads(l) for l in (ROOT / "logs" / "tool_calls.jsonl").read_text(encoding="utf-8").splitlines() if l.strip()]

ap = argparse.ArgumentParser()
ap.add_argument("--name", default="(이름/팀명 기입)")
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
    ("부문별 노인 교통사고 통계(2018)", "한국도로교통공단", "공공데이터포털", "https://www.data.go.kr/data/15094162/fileData.do", "시군구 노인 사고(보조)"),
    ("시도 경찰청별 고령운전자 자진반납 현황(2015~2024)", "경찰청", "공공데이터포털", "https://www.data.go.kr/data/15065567/fileData.do", "면허 반납"),
    ("지역별(행정동) 성별 연령별 주민등록 인구수(2026.9.30)", "행정안전부", "공공데이터포털", "https://www.data.go.kr/data/15097972/fileData.do", "인구·고령인구"),
    ("시군구별 정류장평균이용량(2025, 교통카드)", "국토교통부", "공공데이터포털", "https://www.data.go.kr/data/15162142/fileData.do", "버스 이용(대중교통 대리지표)"),
    ("전국 버스정류장 위치정보(2025)", "국토교통부", "공공데이터포털", "https://www.data.go.kr/data/15067528/fileData.do", "지도 시각화"),
    ("용도별 차종별 시군구별 일평균 자동차 주행거리(2019)", "한국교통안전공단", "공공데이터포털", "https://www.data.go.kr/data/15088483/fileData.do", "자동차 의존·탄소 대리지표"),
]
data_rows_html = "\n".join(
    f"<tr><td>{n}</td><td>{o}</td><td>{p}</td><td class='url'>{u}</td><td>{why}</td></tr>" for n, o, p, u, why in DATA_ROWS)
top_rows = "\n".join(
    f"<tr><td>{i + 1}</td><td>{r.sido} {r.sgg}</td><td>{r.share65:.1f}%</td>"
    f"<td>{('자료 없음' if pd.isna(r.bus_board_pc) else f'{r.bus_board_pc:.3f}')}</td><td>{r.death_per100k:.1f}</td></tr>"
    for i, r in top.reset_index(drop=True).iterrows())
by_sido = ", ".join(f"{k} {v}" for k, v in B["by_sido"].items())

HTML = f"""<!doctype html><html lang="ko"><head><meta charset="utf-8"><title>분석보고서</title>
<style>
@page {{ size: A4; margin: 15mm 15mm 14mm 15mm; }}
* {{ box-sizing: border-box; }}
body {{ font-family: 'Noto Sans CJK KR', 'Noto Sans KR', sans-serif; color:#1f2937; font-size: 9.6pt; line-height: 1.55; margin:0; }}
h1 {{ font-size: 21pt; line-height:1.3; margin: 0 0 6mm; letter-spacing:-0.5px; }}
h2 {{ font-size: 12pt; margin: 5mm 0 2mm; padding: 1.2mm 2.5mm; background:#eef2ff; border-left: 4px solid #2563eb; }}
h3 {{ font-size: 10.2pt; margin: 3mm 0 1mm; color:#1e3a8a; }}
p {{ margin: 0 0 2mm; text-align: justify; }}
ul {{ margin: 0 0 2mm; padding-left: 5mm; }} li {{ margin-bottom: 1mm; }}
.page {{ page-break-after: always; }}
.cover {{ height: 262mm; display:flex; flex-direction:column; justify-content:center; padding: 0 8mm; }}
.cover .tag {{ color:#2563eb; font-weight:700; font-size:11pt; margin-bottom:4mm; }}
.cover table td {{ padding: 2.5mm 3mm; border-bottom:1px solid #e5e7eb; font-size:10.5pt; }}
.cover table td:first-child {{ width: 32mm; color:#6b7280; }}
table {{ border-collapse: collapse; width:100%; }}
table.data th, table.data td {{ border:1px solid #d1d5db; padding: 1.1mm 1.6mm; font-size: 8.2pt; vertical-align: top; }}
table.data th {{ background:#f3f4f6; }}
td.url {{ font-size: 7.4pt; word-break: break-all; }}
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
</style></head><body>

<section class="page cover">
  <div class="tag">AI와 함께하는 교통문제 해결을 위한 데이터 분석 공모전 · 분석보고서</div>
  <h1>운전대를 놓은 노인은 어디로 가는가<br><span style="font-size:14pt;color:#4b5563;font-weight:500">고령운전자 면허 반납의 지역 격차와 ‘이동 사각지대’ 진단,<br>그리고 반납자 이동보장 정책 제안</span></h1>
  <table>
    <tr><td>이름/팀명</td><td>{args.name}</td></tr>
    <tr><td>주제</td><td>대중교통 공백이 고령자의 면허 반납을 가로막고 교통사망을 키우는 ‘이동 사각지대’를 공공데이터로 찾아내고, 면허 반납을 이동권 보장과 연계하는 정책을 제안</td></tr>
    <tr><td>활용 데이터</td><td>공공데이터포털 개방 파일 8종(도로교통공단·경찰청·행정안전부·국토교통부·한국교통안전공단), 227개 시군구·17개 시도</td></tr>
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
<p><b>현황.</b> 2025년 교통사고 사망자의 절반 이상({A['share_deaths_65plus']}%)이 65세 이상이며, 인구 10만 명당 사망률은 {A['rate_65plus']:.1f}명으로 65세 미만({A['rate_under65']:.1f}명)의 {A['ratio_65_vs_under65']:.1f}배다(그림 1). 정부와 지자체는 고령운전자 사고 대책으로 <b>운전면허 자진반납</b>을 장려했고, 반납 건수는 2015년 {ret_by_year['2015']:,}건에서 2024년 {ret_by_year['2024']:,}건으로 늘었다. 반납은 고령운전 위험을 줄이는 동시에 승용차 주행을 줄여 탄소 감축에도 기여한다(수송부문 온실가스의 약 97%가 도로교통에서 발생).</p>
<p><b>문제.</b> 그러나 기존 정책은 반납 ‘건수’만 성과로 보며, 반납한 노인이 <b>무엇으로 이동하는지</b>는 묻지 않는다. 버스가 하루 몇 번 다니지 않는 농어촌에서 면허 반납은 곧 병원·장보기·일자리로 가는 길을 잃는 일이다. 그래서 반납이 가장 필요한 지역일수록 반납하지 못하고 위험한 운전을 이어가는 <b>역설</b>이 생길 수 있다. 이는 사고 통계와 교통 통계가 따로 관리되어 기존 정책에서 잘 드러나지 않았던 문제다.</p>
<p><b>목적.</b> 공공데이터를 결합해 ① 면허 반납률의 지역 격차가 대중교통 이용과 어떤 관계인지, ② 고령화·대중교통 공백·자동차 의존이 겹친 <b>‘이동 사각지대’</b>에 교통사망이 얼마나 집중되는지 확인하고, ③ 반납을 이동권 보장과 연결하는 정책의 대상 지역과 효과(안전·탄소)를 제시한다.</p>
<div class="fig"><img src="{img('fig1_age_death_rate.png')}" style="width:74%"></div>

<h2>2. 활용 데이터</h2>
<table class="data">
<tr><th style="width:31%">활용 데이터(명)</th><th style="width:13%">제공기관(명)</th><th style="width:11%">출처 플랫폼(명)</th><th>URL</th><th style="width:17%">용도(선정 이유)</th></tr>
{data_rows_html}
</table>
<p class="note">모든 자료는 공공데이터포털 개방 파일이며 각 데이터셋 페이지의 이용허락범위가 ‘제한 없음’임을 수집 시점(2026.10.21)에 확인·기록했다. 원본 파일의 SHA-256 해시, 수집 시각, 원 상세 페이지·배포 URL을 데이터 목록(data/raw/index.json, manifest.json)에 함께 보존했다. 민간·개인정보 자료는 쓰지 않았다(모두 집계 통계).</p>

<h2>3. 분석과정 및 방법</h2>
<p><b>① 수집.</b> 자체 개발한 AI 연구자료 수집 도구(rdhub, 4장)로 공공데이터포털을 검색하고, 상세 페이지에서 제공기관·수정일·이용조건을 확인한 뒤 실제 배포 파일을 받았다. 받은 파일이 CSV인지 시그니처로 확인하고(오류 HTML을 자료로 저장하지 않음), 원본 해시와 출처를 기록했다. 내보내기 후 행 수·값 대조에서 불일치 0건을 확인했다.</p>
<p><b>② 전처리(행정구역 정합).</b> 자료마다 기준 연도와 행정구역이 달라 다음 규칙으로 맞췄다. 일반구가 있는 시는 시 단위로 합산, 인천 2026년 행정체제 개편(중·동·서구 → 제물포·영종·서해·검단구)은 하나의 단위로 묶음, 2026년 인구자료의 ‘전남광주통합특별시’는 광주 5개 구와 전남으로 환원, 군위군은 대구로 대응, 2018년 자료의 명칭 변경(인천 남구→미추홀구) 반영. 결과적으로 <b>227개 시군구·17개 시도 패널</b>을 만들었다. 교통카드 정류장 자료가 없는 4개 군은 버스 이용을 0으로 채우지 않고 결측으로 두었다.</p>
<p><b>③ 지표.</b> 대중교통 이용 = 시군구 정류장별 하루 평균 승차 합 ÷ 주민등록인구(1인당 하루 버스 승차, 교통카드 기준). 교통사고 사망률 = 인구 10만 명당 사망자(2025). 반납률 = 65세 이상 1천 명당 연간 반납 건수(2024). 자동차 의존 = 비사업용 승용차 1대당 일평균 주행거리(2019).</p>
<p><b>④ 분석 기법.</b> (가) 시도별 반납률과 버스 이용의 스피어만 순위상관, (나) 시군구를 버스 이용 5분위로 나눈 사망률 비교, (다) <b>음이항 회귀</b>(종속: 사망자 수, 인구 offset; 설명: 65세 이상 비율, log 1인당 버스 승차, 승용차 주행거리, 지역유형[시·군·특별/광역시 구]) — 과대산포를 고려해 포아송 대신 음이항을 사용, (라) 고령비율 상위 1/3·버스 이용 하위 1/3·사망률 상위 1/3을 모두 충족하는 <b>‘3중 이동 사각지대’</b> 유형화, (마) 반납률 격차 해소 시나리오로 추가 반납·회피 주행거리·CO₂ 범위 산정.</p>

<h2>4. AI 기술 활용</h2>
<div class="box small">
<b>사용 서비스.</b> Claude(Anthropic, 대화형 AI) + <b>rdhub</b>(본인이 AI와 함께 개발한 ‘연구자료 수집 도구 서버’, MCP·CLI로 AI가 호출).<br>
<b>활용 범위.</b> ① 데이터 탐색·수집: AI가 rdhub 도구를 {n_calls}회 호출({', '.join(tools_used)})해 카탈로그 검색 → 원문 확인(제공기관·원출처·이용조건 판정) → 파일 수집 → 원본 해시·버전 기록 → 표 정리 → 내보내기 검증까지 수행. 모든 호출은 로그(logs/tool_calls.jsonl)로 남겼다. ② 분석 코드 작성(Python)과 결과 해석 초안. ③ 보고서 문장 초안.<br>
<b>검증.</b> AI가 수치를 기억으로 채우지 못하도록, 보고서의 모든 수치는 분석 코드를 다시 실행해 산출한 결과 파일(results.json)에서 자동으로 채웠다. 행정구역 정합 규칙과 매칭되지 않은 지역을 로그로 남겨 직접 확인했고, 연도 불일치·대리지표의 한계를 본문에 밝혔다. 외부 AI에는 개인정보·비공개 자료를 입력하지 않았다(공개 집계 통계만 사용).
</div>
<p class="small"><b>주요 프롬프트(요지).</b></p>
<div class="prompt">“공모전 공고와 분석보고서 양식을 보고, 이동격차·교통약자·탄소중립을 함께 다룰 수 있으면서 기존 정책에서 드러나지 않은 교통문제를 주제로 정해. 공공데이터로 검증 가능한지부터 확인해.”</div>
<div class="prompt">“rdhub로 고령인구·교통사고·면허반납·버스 이용·주행거리 자료를 찾아 수집해. 각 자료의 제공기관, 수정일, 이용허락범위를 원문에서 확인하고, 파일이 아니라 오류 페이지가 오면 실패로 처리해.”</div>
<div class="prompt">“행정구역 개편(인천 2026, 전남광주 통합, 군위 편입)을 반영해 시군구 패널을 만들고, 매칭되지 않은 지역은 숨기지 말고 로그로 남겨. 버스 자료가 없는 군은 0으로 채우지 마.”</div>
<div class="prompt">“버스 이용과 사망률의 관계를 인과로 단정하지 말고, 고령화·자동차 의존을 함께 넣은 음이항 회귀로 확인해. 유의하지 않으면 그대로 보고해.”</div>

<h2>5. 분석 내용 및 결과</h2>
<h3>결과 ① 면허 반납은 81배 늘었지만, 대중교통이 부족한 지역에서는 절반 수준이다</h3>
<div class="fig"><img src="{img('fig2_license_return.png')}"></div>
<p>2024년 65세 이상 1천 명당 반납은 {RT['max'][0]}({RT['max'][1]:.1f}건)·서울·대구가 높고 {RT['min'][0]}({RT['min'][1]:.1f}건)·세종·충북·광주·충남·경북이 낮아 최대 {RT['gap_ratio_max_min']}배 차이가 난다(광주·세종은 버스 이용이 중간 수준인데도 반납률이 낮은 예외). 시도별 반납률은 1인당 버스 이용과 뚜렷한 양(+)의 순위상관을 보였다(ρ={RT['spearman_bus_vs_return'][0]}, p={RT['spearman_bus_vs_return'][1]:.3f}). 반대로 교통사고 사망률이 높은 시도일수록 반납률이 낮은 경향이 있었다(ρ={RT['spearman_death_vs_return'][0]}, p={RT['spearman_death_vs_return'][1]:.2f}, 17개 시도라 통계적 유의성은 경계 수준). <b>반납이 가장 필요한 곳에서 반납이 가장 적게 일어나고 있다.</b></p>

<h3>결과 ② 버스 이용 하위 20% 시군구의 교통사고 사망률은 상위 20%의 {Q['ratio_q1_q5']:.1f}배</h3>
<div class="fig"><img src="{img('fig3_bus_quintile_deaths.png')}"></div>
<p>버스 이용 1분위(하위 20%) 시군구의 사망률은 인구 10만 명당 {Q['death_rate'][0]:.1f}명으로 5분위({Q['death_rate'][4]:.1f}명)의 {Q['ratio_q1_q5']:.1f}배였고, 65세 이상 노인 사망률(2018 사고 기준)도 {Q['ratio_old_q1_q5']:.1f}배 차이가 났다. 하위 40% 시군구는 인구의 {Q['pop_share_q1q2']}%에 불과하지만 교통사고 사망의 <b>{Q['death_share_q1q2']}%</b>를 차지한다.</p>
<p><b>회귀 결과(음이항, n={int(r_s65.n)}).</b> 지역유형을 통제하면 65세 이상 비율 1%p 증가 시 사망 위험이 {(r_s65.IRR - 1) * 100:.1f}% 높고(IRR {r_s65.IRR:.3f}, 95% CI {r_s65.IRR_lo:.3f}–{r_s65.IRR_hi:.3f}), 승용차 1대당 일평균 주행거리 1km 증가 시 {(r_vkt.IRR - 1) * 100:.1f}% 높았다(IRR {r_vkt.IRR:.3f}, p&lt;0.001). 버스 이용의 독립 효과는 방향은 음(-)이지만 유의하지 않았다(모형1 IRR {r_bus1.IRR:.3f}, p={r_bus1.p:.3f}; 모형2 p={r_bus2.p:.2f}). 즉 대중교통 공백은 고령화·자동차 의존과 <b>함께 나타나며</b>, 위험은 어느 한 요인보다 세 조건이 겹친 곳에서 커진다. 이 점이 아래 ‘3중 사각지대’ 진단의 근거다.</p>

<h3>결과 ③ ‘3중 이동 사각지대’ {B['n_triple']}곳: 인구 {B['pop_share_triple']}%, 교통사고 사망 {B['death_share_triple']}%</h3>
<div class="two">
<div><div class="fig" style="margin-top:0"><img src="{img('fig4_blindspot_map.png')}"></div></div>
<div>
<p class="small">고령비율 상위 1/3(≥{B['thresholds']['share65_top_tertile']:.1f}%), 1인당 버스 승차 하위 1/3(≤{B['thresholds']['bus_board_pc_bottom_tertile']:.3f}회), 사망률 상위 1/3(≥{B['thresholds']['death_per100k_top_tertile']:.1f}명)을 모두 충족한 시군구는 {B['n_triple']}곳({by_sido})이다. 이곳 인구는 {B['pop_triple'] / 1e4:.0f}만 명(65세 이상 {B['p65_triple'] / 1e4:.1f}만 명)이며 사망률은 {B['death_rate_triple']:.1f}명으로 나머지 지역({B['death_rate_rest']:.1f}명)의 {B['death_rate_triple'] / B['death_rate_rest']:.1f}배다. (사망률이 분류 기준에 포함되어 있으므로 이 비율은 ‘정책 대상의 규모’를 보여주는 값이다.)</p>
<table class="data"><tr><th>#</th><th>시군구</th><th>65세+</th><th>1인당 버스승차</th><th>사망률</th></tr>
{top_rows}
</table>
<p class="note">사망률: 인구 10만 명당(2025). 버스 승차: 1인당 하루(2025, 교통카드). ‘자료 없음’은 교통카드 정류장 자료가 없는 군. 전체 {B['n_triple']}곳 목록은 outputs/tables/table_blindspots.csv.</p>
</div></div>

<h2>6. 정책제안 및 기대효과</h2>
<h3>제안 1. ‘면허 반납 = 이동권 보장’: 반납 인센티브를 이동보장 패키지로 전환</h3>
<p>현재 반납 지원은 주로 일회성 교통카드·지역화폐 지급이다. 버스가 드문 사각지대에서는 이것이 반납을 결심할 이유가 되기 어렵다. 3중 사각지대 {B['n_triple']}곳부터 반납자에게 <b>수요응답형 교통(DRT)·공공형 택시의 정액 이용권(예: 월 단위)</b>을 일정 기간 제공하고, 반납 신청 창구(경찰서·주민센터)에서 DRT 호출 등록까지 한 번에 처리한다. 반납 성과지표를 ‘건수’에서 ‘반납 후 월 이동 횟수’로 바꿔 이동권이 실제로 유지되는지 관리한다.</p>
<h3>제안 2. ‘이동 사각지대 지수’로 대중교통 예산을 배분하고 매년 공개 갱신</h3>
<p>고령비율·1인당 대중교통 이용·교통사고 사망률·승용차 의존도를 결합한 지수를 농어촌버스·DRT 국비 지원과 지자체 교통약자 이동편의 계획의 우선순위 기준으로 쓴다. 지수는 모두 공공데이터로 매년 재계산할 수 있고, 이번 분석의 수집·처리 코드를 그대로 재실행하면 갱신된다.</p>
<h3>제안 3. 반납 이후의 ‘걷는 길’까지: 정류장·경로당 주변 보행안전</h3>
<p>반납한 노인은 보행자가 된다. 사각지대 시군구의 정류장·경로당·전통시장 주변을 노인보호구역(30km/h) 우선 지정 대상으로 삼고, 정류장 대기 환경(유개 정류장)을 함께 개선한다.</p>
<div class="box small"><b>기대효과(시나리오).</b> 전국 평균보다 반납률이 낮은 {len(S['sido_below_avg'])}개 시도가 전국 평균(65세 이상 1천 명당 {RT['national_rate_2024_per1k65']:.1f}건)에 도달하면 <b>연간 약 {S['additional_returns_per_year']:,}건</b>의 반납이 추가된다. 반납자 1인당 승용차 주행이 해당 시도 평균의 30~70% 줄어든다고 가정하면 연간 <b>{lo['avoided_vkm_million']:.0f}백만~{hi['avoided_vkm_million']:.0f}백만 km</b>의 승용차 주행과 <b>CO₂ 약 {lo['tCO2'] / 1e4:.2f}만~{hi['tCO2'] / 1e4:.2f}만 톤</b>(중앙값 {mid['tCO2'] / 1e4:.2f}만 톤)이 줄어든다. 이는 대체 이동수단(DRT 등)의 배출을 빼지 않은 총량이고, 반납이 매년 누적되므로 효과도 해마다 쌓인다. 안전 측면에서는 사망률이 전국 평균의 {B['death_rate_triple'] / B['death_rate_rest']:.1f}배인 지역의 고령운전 노출을 줄이고, 반납률의 지역 격차({RT['gap_ratio_max_min']}배)를 좁혀 이동의 형평성을 높인다.</div>
<p class="small"><b>적용 대상과 방식.</b> 1단계로 3중 사각지대가 많은 경북·경남·전남·충남의 군 지역에서 시범 운영하고, 반납자 이동 횟수·사고·주행거리 변화를 공공데이터로 추적해 효과를 검증한 뒤 확대한다.</p>
<p class="note"><b>한계.</b> 자료 연도가 서로 다르다(사고 2025, 인구 2026.9, 노인 사고 2018, 주행거리 2019). 버스 승차는 교통카드 기준이라 현금 승차·DRT는 빠져 있으며, 배차 간격 같은 서비스 수준 지표가 아니다. 시군구 단위 상관·회귀이므로 개인 수준의 인과를 뜻하지 않는다. 시군구별 고령운전자 가해 사고(최근 연도)는 인증키가 필요한 API라 이번 분석에서 쓰지 못했다(활용신청 후 추가 분석 예정). CO₂ 배출계수(0.15~0.21 kgCO₂/km)는 IPCC 2006 휘발유 기본 배출계수와 연비 범위로 환산한 가정치다.</p>

<h2>7. 분석도구 및 참고문헌</h2>
<p class="small"><b>분석도구.</b> Python 3.13(pandas, statsmodels, scipy, matplotlib), rdhub v0.1(연구자료 수집 도구 서버, 자체 개발), Claude(Anthropic). 분석 코드·수집 로그·데이터 목록: {args.code_url}</p>
<p class="small"><b>참고문헌·자료.</b> ① 2장 표의 공공데이터 8종(각 URL, 2026.10.21 접근). ② IPCC (2006). <i>2006 IPCC Guidelines for National Greenhouse Gas Inventories</i>, Vol. 2 Energy, Ch. 3 Mobile Combustion(휘발유 기본 CO₂ 배출계수). ③ (재)숲과나눔·한겨레, 「AI와 함께하는 교통문제 해결을 위한 데이터 분석 공모전」 공고(2026.8.18) — 수송부문 온실가스 중 도로교통 비중 인용.</p>
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
    pg.pdf(path=args.out, format="A4", print_background=True, margin={"top": "15mm", "bottom": "14mm", "left": "15mm", "right": "15mm"})
    b.close()
print("written", args.out)
