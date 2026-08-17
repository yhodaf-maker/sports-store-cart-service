import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from cors_config import add_cors_middleware, parse_allowed_origins


def make_client(origins: str | None) -> TestClient:
    test_app = FastAPI()
    add_cors_middleware(test_app, origins)

    @test_app.get("/resource")
    def resource():
        return {"status": "ok"}

    return TestClient(test_app)


def test_trusted_origin_receives_cors_permission():
    response = make_client("https://shop.example.com").get(
        "/resource", headers={"Origin": "https://shop.example.com"}
    )
    assert response.headers["access-control-allow-origin"] == "https://shop.example.com"


def test_untrusted_origin_is_not_granted_cors_permission():
    response = make_client("https://shop.example.com").get(
        "/resource", headers={"Origin": "https://attacker.example"}
    )
    assert "access-control-allow-origin" not in response.headers


def test_multiple_origins_and_whitespace_are_supported():
    client = make_client(
        "  http://localhost:5173, https://shop.example.com/ , http://localhost:5173 "
    )
    local = client.get("/resource", headers={"Origin": "http://localhost:5173"})
    deployed = client.get("/resource", headers={"Origin": "https://shop.example.com"})
    assert local.headers["access-control-allow-origin"] == "http://localhost:5173"
    assert deployed.headers["access-control-allow-origin"] == "https://shop.example.com"


@pytest.mark.parametrize("raw_value", [None, "", "  ", ", ,"])
def test_empty_configuration_fails_closed(raw_value):
    assert parse_allowed_origins(raw_value) == []


@pytest.mark.parametrize(
    "raw_value",
    ["*", "https://shop.example.com,*", "shop.example.com", "ftp://shop.example.com",
     "https://user:password@shop.example.com", "https://shop.example.com/api",
     "https://shop.example.com?trusted=true", "http://localhost:not-a-port"],
)
def test_wildcard_and_malformed_origins_are_rejected(raw_value):
    with pytest.raises(ValueError, match="ALLOWED_ORIGINS"):
        parse_allowed_origins(raw_value)


def test_cart_preflight_allows_put_and_required_headers():
    response = make_client("http://localhost:5173").options(
        "/resource",
        headers={"Origin": "http://localhost:5173", "Access-Control-Request-Method": "PUT",
                 "Access-Control-Request-Headers": "authorization,content-type"},
    )
    assert response.status_code == 200
    assert "PUT" in response.headers["access-control-allow-methods"]
    assert "authorization" in response.headers["access-control-allow-headers"].lower()
