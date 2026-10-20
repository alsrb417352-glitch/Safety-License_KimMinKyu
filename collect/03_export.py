"""수집한 표 버전을 rdhub export 도구로 CSV(+manifest·출처)로 내보내고 data/raw 로 복사한다."""
import json, os, shutil, time
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent
os.environ.setdefault("RDHUB_HOME", str(ROOT / ".rdhub"))
from rdhub.services import Hub
hub = Hub()
state = json.loads((ROOT / "logs/collected.json").read_text(encoding="utf-8"))
tvs = {}
for it in state["items"]:
    for jb in it.get("jobs", []):
        for t in jb["tables"]:
            tvs[t] = it["variable"]
r = hub.call("export", {"table_version_ids": list(tvs), "format": "csv", "purpose": "internal"}, actor="ai:claude(cloud-session)")
print(r["ok"], r["status"], [ (c["table_version_id"][-8:], c["rows_written"], c["row_count_ok"], c["value_mismatches"]) for c in r["data"]["checks"]])
src = Path(os.environ["RDHUB_HOME"]) / r["data"]["output_handle"]
dst = ROOT / "data" / "raw"
if dst.exists(): shutil.rmtree(dst)
shutil.copytree(src, dst)
m = json.loads((dst / "manifest.json").read_text(encoding="utf-8"))
index = [{"table_version_id": t["table_version_id"], "variable": tvs[t["table_version_id"]], "file": t["file"], "name": t["name"], "rows": t["rows"],
          "source_url": t["source_url"], "citation_ko": t["citation_ko"], "raw_sha256": t["raw_sha256"]} for t in m["tables"]]
(dst / "index.json").write_text(json.dumps(index, ensure_ascii=False, indent=1), encoding="utf-8")
for i in index: print(i["variable"], i["file"], i["rows"], i["name"])
