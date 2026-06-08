import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture()
def client() -> TestClient:
    return TestClient(app)


@pytest.mark.parametrize(
    "origin",
    ["http://localhost:3000", "http://localhost:3100", "http://127.0.0.1:3100"],
)
def test_cors_preflight_allows_local_frontend_ports(
    client: TestClient, origin: str
) -> None:
    response = client.options(
        "/import/game",
        headers={
            "Origin": origin,
            "Access-Control-Request-Method": "POST",
        },
    )
    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == origin


def test_cors_does_not_allow_unknown_origin(client: TestClient) -> None:
    response = client.options(
        "/import/game",
        headers={
            "Origin": "http://evil.example",
            "Access-Control-Request-Method": "POST",
        },
    )
    assert "access-control-allow-origin" not in response.headers
