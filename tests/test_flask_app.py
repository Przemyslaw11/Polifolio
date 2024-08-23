from flask_app.app import app
import pytest


@pytest.fixture
def client():
    with app.test_client() as client:
        yield client


def test_home_route(client):
    response = client.get("/")
    assert response.status_code == 200
    assert b"Welcome to the Polifolio supported by Flask!" in response.data


def test_portfolio_route(client):
    response = client.get("/portfolio")
    assert response.status_code == 200
    data = response.get_json()
    assert "obligations" in data
    assert "stocks" in data
    assert "total_value" in data
