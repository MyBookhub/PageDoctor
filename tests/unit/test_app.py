from fastapi import FastAPI
from fastapi.testclient import TestClient

from fakes.web import build_fake_web
from pagedoctor.app.main import create_app


def test_create_app_returns_fastapi() -> None:
    assert isinstance(create_app(build_fake_web().container), FastAPI)


def test_healthz_reports_ok() -> None:
    with TestClient(create_app(build_fake_web().container)) as client:
        response = client.get("/healthz")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
