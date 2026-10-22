import pytest
import requests
from django.core.cache import cache

from apps.core import ml_client


@pytest.mark.django_db
def test_open_redirect_blocked(client):
    response = client.post("/accounts/login/?next=https://evil.example", {"username": "x", "password": "y"})
    assert response.status_code == 200


@pytest.mark.django_db
def test_ml_fallback_on_timeout(monkeypatch, product):
    cache.clear()
    monkeypatch.setattr(ml_client.session, "post", lambda *a, **k: (_ for _ in ()).throw(requests.Timeout()))
    ids = ml_client.get_recommendations(1, [product.id], 5)
    assert product.id in ids
    assert cache.get(ml_client.CIRCUIT_KEY) is True


@pytest.mark.django_db
def test_health_check_does_not_expose_database_errors(client, monkeypatch):
    from apps.core import views

    def fail_cursor():
        raise RuntimeError("database password and internal hostname")

    monkeypatch.setattr(views.connection, "cursor", fail_cursor)
    response = client.get("/healthz")

    assert response.status_code == 503
    assert b"database password" not in response.content
    assert b"Service temporarily unavailable" in response.content
