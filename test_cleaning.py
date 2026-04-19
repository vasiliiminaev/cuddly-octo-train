"""Unit tests for cleaning helpers — runnable without Playwright."""
from app.cleaning import parse_price, parse_size, parse_int, collapse_whitespace


def test_parse_price_es():
    assert parse_price("120.000 €") == 120000.0
    assert parse_price("1.250.000 €") == 1250000.0


def test_parse_price_en():
    assert parse_price("€1,250,000") == 1250000.0
    assert parse_price("$199,500") == 199500.0


def test_parse_price_decimals():
    assert parse_price("1.250,50 €") == 1250.5
    assert parse_price("1,250.50") == 1250.5


def test_parse_size():
    assert parse_size("60 m²") == 60.0
    assert parse_size("1,200 sqft") == 111.5  # converted
    assert parse_size("85") == 85.0


def test_parse_int():
    assert parse_int("3 habitaciones") == 3
    assert parse_int(None) is None


def test_collapse_whitespace():
    assert collapse_whitespace("  hello   world  ") == "hello world"
    assert collapse_whitespace("") is None
