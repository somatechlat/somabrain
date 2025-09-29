from __future__ import annotations

import threading
import uvicorn
from fastapi import FastAPI, Request
import time
import hashlib

app = FastAPI()
_store: list[dict] = []


def _coord(key: str):
    h = hashlib.blake2b(key.encode(), digest_size=12).digest()
    a = int.from_bytes(h[0:4], 'big')/2**32
    b = int.from_bytes(h[4:8], 'big')/2**32
    c = int.from_bytes(h[8:12], 'big')/2**32
    return [2*a-1, 2*b-1, 2*c-1]

@app.get('/health')
def health():
    return {'ok': True, 'items': len(_store)}

@app.post('/remember')
async def remember(body: dict, request: Request):
    payload = body.get('payload') or {}
    coord = body.get('coord')
    if not coord:
        coord = ','.join(str(x) for x in _coord(str(payload.get('id') or time.time())))
    rec = {'coord': coord, 'payload': payload}
    _store.append(rec)
    return {'coord': coord}

@app.post('/recall')
async def recall(body: dict):
    top_k = int(body.get('top_k') or 3)
    # naive: return most recent
    out = [r['payload'] for r in _store[-top_k:]][::-1]
    return out


def run_memory_server(host='127.0.0.1', port=9595):
    config = uvicorn.Config(app, host=host, port=port, log_level='warning')
    server = uvicorn.Server(config)
    thread = threading.Thread(target=server.run, daemon=True)
    thread.start()
    return server, thread
