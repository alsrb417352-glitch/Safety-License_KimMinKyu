# 운전대를 놓은 노인은 어디로 가는가

**AI와 함께하는 교통문제 해결을 위한 데이터 분석 공모전** 분석 코드·데이터 저장소.
고령운전자 면허 반납의 지역 격차와 '이동 사각지대'(고령화·대중교통 공백·높은 교통사고 사망률이 겹친 시군구)를 공공데이터로 진단합니다.

## 핵심 결과
- 2025년 교통사고 사망자 2,549명 중 65세 이상 1,378명(54.1%). 인구 비중은 20.6%(2025.6), 10만 명당 사망률은 65세 미만의 4.53배.
- 65세 이상 운전자가 낸 사고의 사망자 비중 17.6%(2015) → 33.1%(2025).
- 65세 이상 면허 자진반납 1,415건(2015) → 114,436건(2024). 시도별 반납률 최대 1.97배 차이(부산 14.4 vs 전남 7.3, 65세 이상 1천 명당). 1인당 버스 이용과 순위상관 ρ=0.7(p=0.002).
- 1인당 버스 승차 하위 20% 시군구의 교통사고 사망률은 상위 20%의 5.8배.
- 3중 이동 사각지대 46개 시군구: 인구 4.1%, 교통사고 사망 16.5%.
- (도로교통공단 API) 버스 이용 하위 20% 시군구의 고령운전자 가해 사고는 65세 이상 1천 명당 4.21건으로 상위 20%(4.17건)와 같지만, 사망은 65세 이상 10만 명당 21.15명 대 3.73명(5.68배). 사각지대는 65세 이상 인구의 7.7%, 고령운전자 사고 사망의 23.6%.
- 시도 반납률이 높을수록 고령운전자 사고 사망률(2024)이 낮음(ρ=-0.66, p=0.0038). 반납률 1위 부산이 최저(3.15명, 전국 7.62명).
- 부산 사례: 도시철도 승차 중 무임 비중 25.8%(2014) → 34.1%(2024). 교통약자 특별교통수단 두리발(2025.5) 37,194건 중 미배차 9.4%, 대기 중위 42.4분. 보행노인 사고다발지역 781곳 중 129곳이 부산.

## 재현 방법
```bash
pip install -r requirements.txt
python analysis/01_build_panel.py     # data/raw → data/processed (행정구역 정합 규칙·미매칭 로그 포함)
python analysis/02_analysis.py        # 그림·표·results.json
POP_SOURCE=file2026 python analysis/01_build_panel.py && POP_SOURCE=file2026 python analysis/02_analysis.py   # 초안 방식(2026.9 인구) 비교본 → outputs_file2026/
python analysis/03_verify.py          # API 교차검증: 초안 vs KOSIS 분모, 경찰청 통계·도로교통공단 API와 사망자 대조 → outputs/verification.json
python analysis/04_busan_case.py      # 부산 사례(무임 비중·두리발·보행노인 다발지역), 65세 이상 인구 전망 → outputs/results_busan.json, 그림 5
python report/build_report_form.py --code-url "코드 링크"   # 공모전 양식(교통 제안서/붙임2) 분석보고서 → report/분석보고서_양식.pdf, 제출용 report/안전 면허_분석보고서.pdf (Playwright Chromium 필요)
python report/build_report.py --code-url "코드 링크"        # (참고) 이전 자유 형식 보고서 → report/분석보고서.pdf
```
`data/raw_api/`에는 등록 인증키로 KOSIS OpenAPI를 호출해 받은 자료(내보내기 원본·manifest)가, `data/raw/koroad_api/`에는 공공데이터포털 활용신청 인증키로 받은 도로교통공단 API 자료가, `data/raw/busan_bigdatawave/`에는 부산 Big-데이터웨이브 교통 자료 32종이, `data/raw/kosis_projection/`에는 통계청 장래인구추계가, `data/raw/`에는 수집한 공공데이터 원자료(CSV)와 `index.json`(자료명·원 URL·SHA-256·인용), `manifest.json`(내보내기 검사 결과)이 있습니다.

## 데이터 (이용허락범위 '제한 없음' 확인 — data/raw/license_check_20261021.json, 2026.10.21 접근)
| 자료 | 제공기관 | URL |
| --- | --- | --- |
| 시도 시군구별 교통사고 통계(2025) | 한국도로교통공단 | https://www.data.go.kr/data/15070297/fileData.do |
| 사상자 연령층별 성별 교통사고 통계(2025) | 한국도로교통공단 | https://www.data.go.kr/data/15070293/fileData.do |
| 부문별 노인 교통사고 통계(2018) — 패널 보조(보고서 본문은 2025 API 자료 사용) | 한국도로교통공단 | https://www.data.go.kr/data/15094162/fileData.do |
| 지자체별 대상 교통사고 통계(2024·2025) — 공공데이터포털 OpenAPI(활용신청) | 한국도로교통공단 | https://www.data.go.kr/data/15056770/openapi.do |
| 보행노인 교통사고 다발지역(2023~2025) — 공공데이터포털 OpenAPI(활용신청) | 한국도로교통공단 | https://www.data.go.kr/data/15057666/openapi.do |
| 성 및 연령별 추계인구(중위) | 통계청 | https://kosis.kr/statHtml/statHtml.do?orgId=101&tblId=DT_1BPA001 |
| 부산도시철도 월별 역별 권종별 승하차(2014~2024) | 부산교통공사 | https://data.busan.go.kr/bdip/opendata/detail.do?publicdatapk=15128561 |
| 부산 교통약자 이동지원 차량 운영현황(2025.5) | 부산시설공단 | https://data.busan.go.kr/bdip/opendata/detail.do?publicdatapk=15147515 |
| 전국 노인·장애인 보호구역 표준데이터(부산) | 부산 각 구군 | https://data.busan.go.kr/bdip/opendata/detail.do?publicdatapk=15034532 |
| 시도 경찰청별 고령운전자 자진반납 현황(2015~2024) | 경찰청 | https://www.data.go.kr/data/15065567/fileData.do |
| 행정구역(시군구)별/1세별 주민등록인구(2024.6·2025.6) — KOSIS OpenAPI(인증키) | 행정안전부 | https://kosis.kr/statHtml/statHtml.do?orgId=101&tblId=DT_1B04006 |
| 가해자 연령층별 교통사고(2015~2025) — KOSIS OpenAPI(인증키) | 경찰청 | https://kosis.kr/statHtml/statHtml.do?orgId=132&tblId=DT_V_MOTA_021 |
| (초안 비교용) 지역별(행정동) 성별 연령별 주민등록 인구수(2026.9.30) | 행정안전부 | https://www.data.go.kr/data/15097972/fileData.do |
| 시군구별 정류장평균이용량(2025) | 국토교통부 | https://www.data.go.kr/data/15162142/fileData.do |
| 전국 버스정류장 위치정보(2025) | 국토교통부 | https://www.data.go.kr/data/15067528/fileData.do |
| 용도별 차종별 시군구별 일평균 자동차 주행거리(2019) | 한국교통안전공단 | https://www.data.go.kr/data/15088483/fileData.do |

## 수집 방법과 AI 활용
- 자료는 자체 개발한 연구자료 수집 도구 서버 **rdhub**(MCP·CLI로 AI가 호출)로 수집했습니다. 카탈로그 검색 → 상세 페이지 원문 확인(제공기관·수정일·이용조건) → 파일 다운로드(형식 시그니처 검증) → 원본 SHA-256·버전 기록 → 표 정리 → 내보내기 검증의 전 과정을 도구 호출로 수행했고, 모든 호출을 `logs/tool_calls.jsonl`에 남겼습니다.
- `collect/` 스크립트는 rdhub가 설치된 환경에서 수집을 재실행합니다(분석만 재현할 때는 필요 없음).
- 분석 코드와 보고서 초안 작성에 Claude(Anthropic)를 사용했습니다. 보고서의 모든 수치는 `outputs/results.json`에서 자동으로 채워지며 AI가 직접 적은 수치는 없습니다.

## API 교차검증
초안은 2026.9 인구 파일을 분모로 썼습니다. rdhub가 사용자 PC 보호 저장소의 KOSIS 인증키로 API를 호출해(키 값은 도구 밖으로 나가지 않음) 사고·반납 연도의 6월 인구로 바꿔 전부 재계산했습니다. 비교표는 `outputs/tables/table_verification.csv`, 결론 유지 여부와 경찰청 통계 대조는 `outputs/verification.json`에 있습니다.

## 한계
사고·반납과 인구의 시점은 맞췄지만(2025·2024 각 6월 인구), 주행거리(2019)는 연도가 다릅니다. 고령운전자 사고 사망자에는 그 사고의 모든 사망자가 포함됩니다. 두리발 자료는 교통약자 대상 한 달 기록이고, 부산 노인보호구역 표준데이터는 11개 구군만 있습니다. 버스 이용은 교통카드 기준입니다. 시군구 단위 분석이므로 개인 수준의 인과를 뜻하지 않습니다. CO₂ 환산은 가정치입니다(보고서 참고).
