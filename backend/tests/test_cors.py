from fastapi.testclient import TestClient

from app.main import app


def test_cors_preflight_allows_frontend_origin() -> None:
    client = TestClient(app)
    response = client.options(
        "/import/game",
        headers={
            "Origin": "http://localhost:3000",
            "Access-Control-Request-Method": "POST",
        },
    )
    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == "http://localhost:3000"


def test_cors_does_not_allow_unknown_origin() -> None:
    client = TestClient(app)
    response = client.options(
        "/import/game",
        headers={
            "Origin": "http://evil.example",
            "Access-Control-Request-Method": "POST",
        },
    )
    assert "access-control-allow-origin" not in response.headers
