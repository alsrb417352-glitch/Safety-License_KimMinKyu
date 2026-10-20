"""공모전 분석 자료 수집 — rdhub(연구자료 수집 도구 서버)의 도구 호출로만 수집한다.

흐름: 연구 요청서 생성 → 공공데이터포털 카탈로그 검색(search_datasets) → 후보 원문 확인(inspect_source)
      → 파일 후보 수집(collect) → 요청서 변수에 표 버전 연결(update_request)
모든 도구 호출과 결과를 logs/tool_calls.jsonl 에 남긴다(보고서 'AI 기술 활용'의 근거).
"""
from __future__ import annotations

import json
import os
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
os.environ.setdefault("RDHUB_HOME", str(ROOT / ".rdhub"))
from rdhub.services import Hub  # noqa: E402

LOG = ROOT / "logs" / "tool_calls.jsonl"
LOG.parent.mkdir(parents=True, exist_ok=True)
STATE = ROOT / "logs" / "collected.json"

hub = Hub()


def call(tool: str, **args):
    t = time.time()
    res = hub.call(tool, args, actor="ai:claude(cloud-session)")
    with open(LOG, "a", encoding="utf-8") as f:
        f.write(json.dumps({"at": time.strftime("%Y-%m-%dT%H:%M:%S%z"), "tool": tool, "args": args, "ok": res["ok"],
                            "target_id": res.get("target_id"), "status": res.get("status"), "error": res.get("error"),
                            "elapsed_s": round(time.time() - t, 2)}, ensure_ascii=False) + "\n")
    return res


REQUEST = dict(
    title="운전대를 놓은 노인은 어디로 가는가: 고령자 면허반납·대중교통 공백·보행안전의 엇박자",
    question="대중교통이 부족하고 자동차 의존이 큰 지역일수록 고령자의 교통사고 피해가 크고 면허 반납이 어려우며, "
             "노인보호구역 등 보행 안전망은 어린이보호구역에 비해 부족한가?",
    period="최신 공개 연도(2023~2025) — 연도는 자료별로 다르며 각 자료의 기준시점을 따로 기록(가정)",
    region="전국 시군구(행정구역 변경분은 자료별 표기 그대로 보존 후 분석 단계에서 대응)",
    unit="시군구-연도(일부 자료는 시도-연도)",
    variables=[
        {"name": "노인교통사고", "definition": "65세 이상 사상자가 발생한 교통사고 건수·사망자수(시군구)", "direct_or_proxy": "direct"},
        {"name": "고령운전자사고", "definition": "65세 이상 운전자가 가해자인 교통사고(시군구 또는 시도)", "direct_or_proxy": "direct"},
        {"name": "전체교통사고", "definition": "시군구별 전체 교통사고·사망자", "direct_or_proxy": "direct"},
        {"name": "고령인구", "definition": "시군구별 65세 이상 주민등록인구", "direct_or_proxy": "direct"},
        {"name": "면허반납", "definition": "고령운전자 운전면허 자진반납 건수(시도·연도)", "direct_or_proxy": "direct"},
        {"name": "고령면허소지자", "definition": "65세 이상 운전면허 소지자 수(시도)", "direct_or_proxy": "direct"},
        {"name": "노인보호구역", "definition": "노인·장애인 보호구역 지정 위치·수(시군구)", "direct_or_proxy": "direct"},
        {"name": "어린이보호구역", "definition": "어린이보호구역 지정 수(시군구)", "direct_or_proxy": "direct"},
        {"name": "대중교통공급", "definition": "버스정류장 수·정류장 평균 이용량(시군구)", "direct_or_proxy": "proxy",
         "measure": "대중교통 서비스 수준의 대리지표(배차간격·노선 수 아님)"},
        {"name": "자동차주행거리", "definition": "시군구별 일평균 자동차 주행거리(승용) 및 승용차 CO2 배출계수(표시연비)", "direct_or_proxy": "proxy",
         "measure": "자동차 의존·수송 탄소배출의 대리지표"},
    ],
    assumptions=["기간 미지정 → 각 자료의 최신 공개 연도 사용, 연도 불일치는 한계로 명시",
                 "버스정류장 수는 대중교통 서비스 수준의 대리지표(배차·노선 정보 미반영)"],
)

# (변수, 카탈로그 검색어, 선택할 상세 페이지 URL 끝부분)
TARGETS = [
    ("노인교통사고", "부문별 노인 교통사고 통계", "/data/15094162/fileData.do"),
    ("고령운전자사고", "65세이상 노인 및 노인운전자 교통사고 통계", "/data/15094173/fileData.do"),
    ("전체교통사고", "시도 시군구별 교통사고 통계", "/data/15070297/fileData.do"),
    ("고령인구", "지역별 연령별 주민등록 인구현황", "/data/3033304/fileData.do"),
    ("면허반납", "시도 경찰청별 고령운전자 자진반납 현황", "/data/15065567/fileData.do"),
    ("면허반납", "운전면허 자진반납 연령별 시도청별 취소처분현황", "/data/15114381/fileData.do"),
    ("고령면허소지자", "운전면허소지자 연령별 현황", "/data/15048426/fileData.do"),
    ("노인보호구역", "전국노인장애인보호구역정보", "/data/15118670/fileData.do"),
    ("어린이보호구역", "어린이보호구역 지정 건수 현황", "/data/15038624/fileData.do"),
    ("대중교통공급", "전국 대중교통 버스정류장 현황", "/data/15066754/fileData.do"),
    ("대중교통공급", "시군구별 정류장평균이용량", "/data/15162142/fileData.do"),
    ("자동차주행거리", "용도별 차종별 시군구별 일평균 자동차 주행거리", "/data/15088483/fileData.do"),
    ("노인교통사고", "사상자 연령층별 성별 교통사고 통계", "/data/15070293/fileData.do"),
    ("고령인구", "지역별(행정동) 성별 연령별 주민등록 인구수", "/data/15097972/fileData.do"),
    ("대중교통공급", "전국 버스정류장 위치정보", "/data/15067528/fileData.do"),
    ("자동차주행거리", "자동차 표시연비 정보", "/data/15083023/fileData.do"),
]


def main() -> None:
    state = json.loads(STATE.read_text(encoding="utf-8")) if STATE.exists() else {"items": []}
    if not state.get("request_id"):
        r = call("create_request", **REQUEST)
        state["request_id"] = r["target_id"]
        state["collection_id"] = r["data"]["collection_id"]
    req = state["request_id"]
    done = {(it["variable"], it["page"]) for it in state["items"] if it.get("ok")}
    for var, query, page_suffix in TARGETS:
        if (var, page_suffix) in done:
            continue
        item = {"variable": var, "query": query, "page": page_suffix, "ok": False}
        s = call("search_datasets", query=query, scope=["datagokr_catalog"], max_results=10, request_id=req)
        sec = s["data"].get("datagokr_catalog", {})
        item["search_run_id"] = sec.get("search_run_id")
        cand = next((c for c in sec.get("results", []) if c["url"].endswith(page_suffix)), None)
        if not cand:
            item["error"] = "카탈로그 검색 결과에 대상 페이지 없음"
            state["items"].append(item)
            continue
        item["search_candidate_id"] = cand["candidate_id"]
        ins = call("inspect_source", candidate_id=cand["candidate_id"], request_id=req)
        if not ins["ok"]:
            item["error"] = ins.get("error")
            state["items"].append(item)
            continue
        item["source_id"] = ins["target_id"]
        jd = ins["data"]["judgment"]
        item["judgment"] = {"org_identity": jd["org_identity"]["status"], "origin": jd["origin"]["status"], "producer": jd["origin"]["producer"],
                            "published": jd["dates"]["published"], "modified": jd["dates"]["modified"],
                            "license": jd["terms"]["license_name"], "redistribution": jd["terms"]["flags"]["redistribution"]}
        dls = [c for c in ins["data"]["download_candidates"] if c["location"] == "jsonld.distribution"]
        item["download_candidates"] = [c["candidate_id"] for c in dls]
        item["jobs"] = []
        for dc in dls:
            j = call("collect", target_id=dc["candidate_id"], request_id=req, variable=var)
            if j["status"].get("job") in ("failed", "partial") and j["data"].get("idempotent_reuse"):
                j = call("retry_job", job_id=j["target_id"])
            res = (j["data"] or {}).get("result") or {}
            item["jobs"].append({"job_id": j["target_id"], "status": j["status"].get("job"), "raw_version_id": res.get("raw_version_id"),
                                 "format": res.get("detected_format"), "extraction": (res.get("extraction") or {}).get("status"),
                                 "tables": [t["table_version_id"] for t in (res.get("extraction") or {}).get("tables", [])],
                                 "error": (j["data"] or {}).get("error")})
            for tv in item["jobs"][-1]["tables"]:
                call("update_request", request_id=req, variable_updates=[{"name": var, "add_table_version": tv, "status": "acquired"}])
        item["ok"] = any(jb["tables"] for jb in item["jobs"])
        state["items"].append(item)
        STATE.write_text(json.dumps(state, ensure_ascii=False, indent=1), encoding="utf-8")
    STATE.write_text(json.dumps(state, ensure_ascii=False, indent=1), encoding="utf-8")
    for it in state["items"]:
        print(("OK " if it["ok"] else "-- ") + it["variable"], it["page"], [(jb["format"], jb["extraction"], jb["tables"][:3]) for jb in it.get("jobs", [])],
              it.get("error") or "")


if __name__ == "__main__":
    main()
