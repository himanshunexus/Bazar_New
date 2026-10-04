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
