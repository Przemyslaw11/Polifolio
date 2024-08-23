from frontend.streamlit_app import fetch_portfolio, fetch_stock_price
import requests
import pytest


def test_fetch_portfolio(mocker):
    mock_response = mocker.Mock()
    mock_response.json.return_value = {"total_value": 1000}
    mocker.patch("requests.get", return_value=mock_response)

    result = fetch_portfolio()
    assert result["total_value"] == 1000


def test_fetch_stock_price(mocker):
    mock_response = mocker.Mock()
    mock_response.json.return_value = {"price": "150.00"}
    mocker.patch("requests.get", return_value=mock_response)

    result = fetch_stock_price()
    assert result["price"] == "150.00"


def test_fetch_portfolio_request_exception(mocker):
    mocker.patch("requests.get", side_effect=requests.exceptions.RequestException)

    with pytest.raises(requests.exceptions.RequestException):
        fetch_portfolio()


def test_fetch_stock_price_request_exception(mocker):
    mocker.patch("requests.get", side_effect=requests.exceptions.RequestException)

    with pytest.raises(requests.exceptions.RequestException):
        fetch_stock_price()
