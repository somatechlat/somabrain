#!/bin/bash
set -euo pipefail
mkdir -p tmp
CUTOFF=$(python3 - <<'PY'
import time
print(int(time.time() - 73*3600))
PY
)
echo "Cutoff_epoch:$CUTOFF" > tmp/cutoff.txt
echo "Cutoff epoch (73h ago): $CUTOFF"

# Query both instances and save raw JSON
curl -sS -X POST 'http://127.0.0.1:9696/recall' -H 'Content-Type: application/json' -d '{"query":"the","top_k":1000}' -o tmp/recall_9696_any.json || true
curl -sS -X POST 'http://127.0.0.1:9797/recall' -H 'Content-Type: application/json' -d '{"query":"the","top_k":1000}' -o tmp/recall_9797_any.json || true

# Filter for old memories and write a report
python3 - <<'PY' > tmp/old_memories_report.txt
import json,os
from datetime import datetime

def parse_ts(v):
    if v is None:
        return None
    try:
        if isinstance(v,(int,float)):
            return float(v)
        s=str(v)
        try:
            return float(s)
        except:
            pass
        try:
            if s.endswith('Z'):
                s=s[:-1]
            dt=datetime.fromisoformat(s)
            return dt.timestamp()
        except Exception:
            return None
    except Exception:
        return None

cutoff=int(open('tmp/cutoff.txt').read().strip().split(':')[-1])
out=[]
for path in ['tmp/recall_9696_any.json','tmp/recall_9797_any.json']:
    if not os.path.exists(path):
        out.append(f'FILE_MISSING: {path}')
        continue
    with open(path,'r') as f:
        try:
            obj=json.load(f)
        except Exception as e:
            out.append(f'FAILED_PARSE: {path}: {e}')
            continue
    memories = obj.get('memory') or obj.get('memory', [])
    if not memories:
        out.append(f'NO_MEMORIES_KEY in {path}; top-level keys: {list(obj.keys())}')
        continue
    found=0
    out.append(f'--- {path} ---')
    for i,m in enumerate(memories):
        ts=None
        if isinstance(m,dict):
            cand = [m.get('timestamp'), (m.get('payload') or {}).get('timestamp'), m.get('when'), (m.get('payload') or {}).get('when'), (m.get('payload') or {}).get('when_iso')]
            for c in cand:
                t=parse_ts(c)
                if t is not None:
                    ts=t; break
        if ts is None:
            # deep search
            def find_ts(obj):
                if isinstance(obj,dict):
                    for k,v in obj.items():
                        if 'timestamp' in k.lower() and isinstance(v,(int,float,str)):
                            t=parse_ts(v)
                            if t is not None:
                                return t
                        r=find_ts(v)
                        if r is not None:
                            return r
                if isinstance(obj,list):
                    for it in obj:
                        r=find_ts(it)
                        if r is not None:
                            return r
                return None
            ts=find_ts(m)
        if ts is None:
            continue
        if ts <= cutoff:
            found+=1
            iso=datetime.utcfromtimestamp(ts).isoformat()+'Z'
            summary = m.get('task') if isinstance(m,dict) else None
            if not summary:
                summary = (m.get('payload') or {}).get('task') if isinstance(m,dict) else None
            out.append(f'[{i}] ts={int(ts)} ({iso}) summary={summary} payload_keys={list(m.keys()) if isinstance(m,dict) else type(m)}')
    out.append(f'Found {found} memories older than cutoff in {path}')
with open('tmp/old_memories_report.txt','w') as rf:
    rf.write('\n'.join(out))
print('\n'.join(out))
PY

ls -l tmp/recall_*.json tmp/old_memories_report.txt tmp/cutoff.txt || true
