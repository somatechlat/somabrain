import datetime
import json
import time
from pathlib import Path

recall_path = Path("tmp/recall_9696_the.json")
out_json = Path("tmp/old_memories_9696_74h.json")
out_txt = Path("tmp/old_memories_report_9696_74h.txt")

if not recall_path.exists():
    print("recall file missing:", recall_path)
    raise SystemExit(1)

data = json.loads(recall_path.read_text())
cutoff_secs = time.time() - 74 * 3600
matches = []


def extract_timestamp(val):
    try:
        if isinstance(val, (int, float)):
            v = float(val)
            if v > 1e12:
                v = v / 1000.0
            return v
        if isinstance(val, str):
            s = val.strip()
            if s.isdigit():
                v = float(s)
                if v > 1e12:
                    v = v / 1000.0
                return v
            try:
                s2 = s.replace("Z", "+00:00")
                dt = datetime.datetime.fromisoformat(s2)
                return dt.timestamp()
            except Exception:
                return None
    except Exception:
        return None
    return None


def walk(obj):
    if isinstance(obj, dict):
        for k, v in obj.items():
            if k and any(
                tok in k.lower()
                for tok in ("time", "when", "timestamp", "created", "date", "ts")
            ):
                t = extract_timestamp(v)
                if t is not None:
                    if t <= cutoff_secs:
                        matches.append({"dict": obj, "key": k, "ts": t})
                    break
        for v in obj.values():
            walk(v)
    elif isinstance(obj, list):
        for item in obj:
            walk(item)


walk(data)

unique = []
seen = set()
for m in matches:
    d = m["dict"]
    idv = d.get("id") or d.get("uid") or d.get("memory_id") or d.get("coord")
    key = str(idv) if idv is not None else json.dumps(d, sort_keys=True)
    if key in seen:
        continue
    seen.add(key)
    unique.append(
        {
            "id": idv,
            "timestamp": m["ts"],
            "timestamp_iso": datetime.datetime.utcfromtimestamp(m["ts"]).isoformat()
            + "Z",
            "payload": d,
        }
    )

out_json.write_text(json.dumps(unique, indent=2))
with out_txt.open("w") as f:
    f.write(
        f"Found {len(unique)} memory-like dicts older than 74 hours (cutoff epoch={int(cutoff_secs)})\n"
    )
    for i, u in enumerate(unique[:200], start=1):
        f.write(
            f'[{i}] id={u["id"]} ts={int(u["timestamp"])} iso={u["timestamp_iso"]}\n'
        )
        p = u["payload"]
        preview = None
        for k in ("text", "content", "memo", "note", "body", "payload", "what", "task"):
            if k in p and isinstance(p[k], str):
                preview = p[k][:200]
                break
        if preview:
            f.write("    preview: " + preview.replace("\n", " ") + "\n")

print("Matches found:", len(unique))
print("Wrote:", out_json, out_txt)
