"""경로 ③ 웹 검색 기반 수집: AI 클라이언트(Claude)의 웹 검색 결과를 허브에 가져와(import_search_results)
허브가 직접 원문·기관·원출처를 확인(inspect_source)하고 표·파일을 수집한다.
서버 측 검색 제공자(네이버·Brave) 키가 없어 search_web은 '검색 미설정'으로 기록된다(정직한 차단 기록)."""
import json, os, sys, time
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent
os.environ.setdefault("RDHUB_HOME", str(ROOT / ".rdhub"))
from rdhub.services import Hub
hub = Hub()
LOG = ROOT / "logs" / "tool_calls.jsonl"
def call(tool, **args):
    t=time.time(); res = hub.call(tool, args, actor="ai:claude(cloud-session)")
    with open(LOG, "a", encoding="utf-8") as f:
        f.write(json.dumps({"at": time.strftime("%Y-%m-%dT%H:%M:%S%z"), "tool": tool, "args": args, "ok": res["ok"], "target_id": res.get("target_id"),
                            "status": res.get("status"), "error": res.get("error"), "elapsed_s": round(time.time()-t,2)}, ensure_ascii=False) + "\n")
    return res
state = json.loads((ROOT/"logs/collected.json").read_text(encoding="utf-8"))
req = state["request_id"]
mode = sys.argv[1]
if mode == "search_web":
    r = call("search_web", query="노인보호구역 지정 현황 시도별", request_id=req)
    print(json.dumps({k: r.get(k) for k in ("ok","status","error")}, ensure_ascii=False)[:600])
elif mode == "import":
    results = json.loads(Path(sys.argv[2]).read_text(encoding="utf-8"))
    r = call("import_search_results", query=sys.argv[3], provider="claude.ai WebSearch", results=results,
             searched_at=time.strftime("%Y-%m-%dT%H:%M:%S%z"), request_id=req)
    print(json.dumps(r["data"], ensure_ascii=False, indent=1)[:3000])
elif mode == "inspect":
    r = call("inspect_source", candidate_id=sys.argv[2], request_id=req)
    if not r["ok"]: print(json.dumps(r["error"], ensure_ascii=False)); sys.exit()
    d = r["data"]; j = d["judgment"]
    print(r["target_id"], json.dumps(r["status"], ensure_ascii=False))
    print(" origin:", json.dumps(j["origin"], ensure_ascii=False)[:400]); print(" dates:", json.dumps(j["dates"], ensure_ascii=False)[:400])
    print(" terms:", j["terms"]["license_name"], j["terms"]["flags"]["redistribution"], j["terms"]["basis"][:2])
    print(" trace:", json.dumps(d.get("origin_trace"), ensure_ascii=False)[:1200]); print(" registry:", d.get("registry_link"))
    for c in d["download_candidates"][:25]: print("  ", c["candidate_id"], c["kind"], c["guessed_format"], c["location"], (c["url"] or "")[:100], (c["link_text_untrusted"] or "")[:50], c.get("table_hint"))
    print(" untrusted title:", r.get("untrusted",{}).get("title"))
elif mode == "inspect_url":
    r = call("inspect_source", url=sys.argv[2], request_id=req)
    if not r["ok"]: print(json.dumps(r["error"], ensure_ascii=False)); sys.exit()
    d = r["data"]; j = d["judgment"]
    print(r["target_id"], json.dumps(r["status"], ensure_ascii=False)); print(" origin:", json.dumps(j["origin"], ensure_ascii=False)[:300])
    for c in d["download_candidates"][:30]: print("  ", c["candidate_id"], c["kind"], c["guessed_format"], c["location"], (c["url"] or "")[:100], (c["link_text_untrusted"] or "")[:50], c.get("table_hint"))
elif mode == "collect":
    var = sys.argv[3]
    r = call("collect", target_id=sys.argv[2], request_id=req, variable=var)
    res = (r["data"] or {}).get("result") or {}
    print(r["target_id"], r["status"], json.dumps(res, ensure_ascii=False)[:1500], (r["data"] or {}).get("error"))
    for t in (res.get("extraction") or {}).get("tables", []):
        call("update_request", request_id=req, variable_updates=[{"name": var, "add_table_version": t["table_version_id"], "status": "acquired"}])
