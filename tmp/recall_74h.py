#!/usr/bin/env python3
"""Post a recall to local server and find memories older than 74 hours.
Saves outputs under tmp/:
 - recall_9696_the.json
 - old_memories_9696_74h.json
 - old_memories_9696_74h.txt
 - audit_remembers_>=74h.json
 - hippocampus_memories_>=74h.json
"""
import datetime
import json
import sys
import time
from pathlib import Path
from urllib import error, request

TMP = Path("tmp")
TMP.mkdir(exist_ok=True)
RECALL_OUT = TMP / "recall_9696_the.json"
RECALL_PAYLOAD = {"query": "the", "top_k": 1000}
HEADERS = {"Content-Type": "application/json"}
URL = "http://127.0.0.1:9696/recall"
CUTOFF = time.time() - 74 * 3600

print(
    "cutoff epoch:",
    int(CUTOFF),
    "UTC iso:",
    datetime.datetime.utcfromtimestamp(int(CUTOFF)).isoformat() + "Z",
)

# helper timestamp extractor


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


def find_old_in_obj(obj):
    matches = []

    def walk(o):
        if isinstance(o, dict):
            for k, v in o.items():
                if k and any(
                    tok in k.lower()
                    for tok in ("time", "when", "timestamp", "created", "date", "ts")
                ):
                    t = extract_timestamp(v)
                    if t is not None and t <= CUTOFF:
                        matches.append({"dict": o, "key": k, "ts": t})
                        # don't break entirely; still descend
                # descend
                walk(v)
        elif isinstance(o, list):
            for it in o:
                walk(it)

    walk(obj)
    return matches


# POST recall using urllib
req = request.Request(
    URL, data=json.dumps(RECALL_PAYLOAD).encode("utf-8"), headers=HEADERS, method="POST"
)
try:
    with request.urlopen(req, timeout=30) as resp:
        status = resp.getcode()
        body = resp.read()
        try:
            body_text = body.decode("utf-8")
        except Exception:
            body_text = repr(body[:200])
        RECALL_OUT.write_text(body_text)
        print("POST", URL, "status", status)
except error.HTTPError as e:
    body = e.read()
    try:
        body_text = body.decode("utf-8")
    except Exception:
        body_text = repr(body[:200])
    RECALL_OUT.write_text(body_text)
    print("POST", URL, "HTTPError", e.code)
    print("response body saved to", RECALL_OUT)
except Exception as e:
    print("POST failed:", e)
    sys.exit(1)

# parse recall output if JSON
try:
    recall_data = json.loads(RECALL_OUT.read_text())
except Exception as e:
    print("Failed to parse recall JSON:", e)
    recall_data = None

old_matches = []
if recall_data is not None:
    old_matches = find_old_in_obj(recall_data)
    # dedupe
    unique = []
    seen = set()
    for m in old_matches:
        d = m["dict"]
        idv = None
        for key in ("id", "uid", "memory_id", "coord"):
            if key in d:
                idv = d.get(key)
                break
        key = str(idv) if idv is not None else json.dumps(d, sort_keys=True)
        if key in seen:
            continue
        seen.add(key)
        unique.append(
            {
                "id": idv,
                "timestamp": m["ts"],
                "timestamp_iso": datetime.datetime.utcfromtimestamp(
                    int(m["ts"])
                ).isoformat()
                + "Z",
                "payload": d,
            }
        )
    (TMP / "old_memories_9696_74h.json").write_text(json.dumps(unique, indent=2))
    txt = TMP / "old_memories_9696_74h.txt"
    with txt.open("w") as f:
        f.write(
            f"Found {len(unique)} memory-like dicts older than 74 hours (cutoff epoch={int(CUTOFF)})\n"
        )
        for i, u in enumerate(unique[:200], start=1):
            f.write(
                f'[{i}] id={u["id"]} ts={int(u["timestamp"])} iso={u["timestamp_iso"]}\n'
            )
            p = u["payload"]
            preview = None
            for k in (
                "text",
                "content",
                "memo",
                "note",
                "body",
                "payload",
                "what",
                "task",
            ):
                if k in p and isinstance(p[k], str):
                    preview = p[k][:200]
                    break
            if preview:
                f.write("    preview: " + preview.replace("\n", " ") + "\n")
    print("Found", len(unique), "old items in recall output; saved JSON and TXT")
else:
    print("No recall JSON to scan")

# Scan audit_log.jsonl for remember entries older than cutoff
AUDIT = Path("audit_log.jsonl")
AUD_OUT = TMP / "audit_remembers_>=74h.json"
found = []
if AUDIT.exists():
    with AUDIT.open() as f:
        for line in f:
            try:
                obj = json.loads(line)
            except Exception:
                continue
            ts = None
            for k in ("timestamp", "when", "created", "time"):
                if k in obj:
                    ts = obj[k]
                    break
            if ts is None and "payload" in obj and isinstance(obj["payload"], dict):
                for k in ("timestamp", "when", "created", "time"):
                    if k in obj["payload"]:
                        ts = obj["payload"][k]
                        break
            try:
                if ts is not None:
                    t = float(ts)
                    if t > 1e12:
                        t = t / 1000.0
                    if int(t) <= int(CUTOFF):
                        found.append(obj)
                else:
                    if obj.get("op") == "remember" or obj.get("event") == "remember":
                        found.append(obj)
            except Exception:
                continue
    AUD_OUT.write_text(json.dumps(found[-200:], indent=2))
    print(
        "Audit log: found", len(found), "matching entries; saved last 200 to", AUD_OUT
    )
else:
    print("audit_log.jsonl not present")

# Fetch hippocampus memories
HIP_OUT_RAW = TMP / "hippocampus_memories.json"
HIP_FILTERED = TMP / "hippocampus_memories_>=74h.json"
HIP_URL = "http://127.0.0.1:9696/brain/hippocampus/memories?limit=1000"
try:
    with request.urlopen(HIP_URL, timeout=30) as resp:
        body = resp.read().decode("utf-8")
        HIP_OUT_RAW.write_text(body)
        print("Fetched hippocampus raw, size", len(body))
except Exception as e:
    print("Failed to fetch hippocampus:", e)
    body = None

if HIP_OUT_RAW.exists():
    try:
        hip = json.loads(HIP_OUT_RAW.read_text() or "[]")
    except Exception:
        hip = []
    items = []
    if isinstance(hip, dict) and "memories" in hip:
        candidates = hip["memories"]
    elif isinstance(hip, list):
        candidates = hip
    else:
        candidates = []
    for m in candidates:
        ts = None
        for k in ("timestamp", "when", "created", "time"):
            if k in m:
                ts = m[k]
                break
        if ts is None and "payload" in m and isinstance(m["payload"], dict):
            for k in ("timestamp", "when", "created", "time"):
                if k in m["payload"]:
                    ts = m["payload"][k]
                    break
        try:
            if ts is not None:
                t = float(ts)
                if t > 1e12:
                    t = t / 1000.0
                if int(t) <= int(CUTOFF):
                    items.append(m)
        except Exception:
            continue
    HIP_FILTERED.write_text(json.dumps(items, indent=2))
    print(
        "Hippocampus: total",
        len(candidates),
        "found",
        len(items),
        "older than cutoff; saved to",
        HIP_FILTERED,
    )

print("\nOutputs saved under tmp/:")
for p in (
    "recall_9696_the.json",
    "old_memories_9696_74h.json",
    "old_memories_9696_74h.txt",
    "audit_remembers_>=74h.json",
    "hippocampus_memories_>=74h.json",
    "hippocampus_memories.json",
):
    fp = TMP / p
    if fp.exists():
        print(fp, "-", fp.stat().st_size, "bytes")
    else:
        print(fp, "- missing")
