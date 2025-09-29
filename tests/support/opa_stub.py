from __future__ import annotations
from fastapi import FastAPI
import threading
import uvicorn

app = FastAPI()

@app.get('/health')
async def health():
    return {'ok': True}

# OPA allow-all stub
@app.post('/v1/data/somabrain/auth/allow')
async def allow():
    return {'result': True}

@app.get('/v1/data/somabrain/auth/allow')
async def allow_get():
    return {'result': True}

def run_opa_stub(host='127.0.0.1', port=8181):
    config = uvicorn.Config(app, host=host, port=port, log_level='warning')
    server = uvicorn.Server(config)
    t = threading.Thread(target=server.run, daemon=True)
    t.start()
    return server, t
