import pytest
from fastapi.testclient import TestClient
from src.main import app

client = TestClient(app)


def test_search_battery_models():
    response = client.get('/api/v1/battery-models?search=')
    assert response.status_code == 200
    data = response.json()
    assert 'data' in data
    assert isinstance(data['data'], list)


def test_search_battery_models_with_query():
    response = client.get('/api/v1/battery-models?search=Audi')
    assert response.status_code == 200
    data = response.json()
    assert 'data' in data


def test_search_battery_models_without_stats():
    response = client.get('/api/v1/battery-models?search=Audi&include_stats=false')
    assert response.status_code == 200
    data = response.json()
    assert 'data' in data
