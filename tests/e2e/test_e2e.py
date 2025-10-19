import requests


def test_health_endpoint():
    response = requests.get("http://localhost:9696/health")
    assert response.status_code == 200
