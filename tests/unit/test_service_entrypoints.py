from fastapi import FastAPI


def test_sa01_create_server_returns_grpc_server():
    from services.sa01 import create_server

    server, port = create_server(max_workers=1)
    try:
        assert port == 50051
    finally:
        server.stop(0)


def test_sah_create_app_returns_fastapi_instance():
    from services.sah import create_app

    app = create_app(
        memory_endpoint="http://localhost:9595",
        auth_endpoint="http://localhost:8080",
        opa_endpoint="http://localhost:8181",
    )
    assert isinstance(app, FastAPI)
    assert app.title == "SomaAgentHub"


def test_smf_create_app_returns_fastapi_instance():
    from services.smf import create_app

    app = create_app(vector_endpoint="http://localhost:6333")
    assert isinstance(app, FastAPI)
    assert app.title == "SomaFractalMemory"
