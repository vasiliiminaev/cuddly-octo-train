"""Helpers to normalize scraped strings into typed values."""
import re
from typing import Optional


def parse_price(text: Optional[str]) -> Optional[float]:
    """'120.000 €' → 120000.0  |  '€1,250,000' → 1250000.0"""
    if not text:
        return None
    cleaned = re.sub(r"[^0-9,.\s]", "", text).strip()
    if not cleaned:
        return None
    # Remove thousands separators (both . and ,) heuristically
    if "," in cleaned and "." in cleaned:
        # Assume the rightmost is the decimal separator
        if cleaned.rfind(",") > cleaned.rfind("."):
            cleaned = cleaned.replace(".", "").replace(",", ".")
        else:
            cleaned = cleaned.replace(",", "")
    elif "," in cleaned:
        # Spanish-style thousands (e.g. "1,250,000")
        if cleaned.count(",") > 1 or len(cleaned.split(",")[-1]) == 3:
            cleaned = cleaned.replace(",", "")
        else:
            cleaned = cleaned.replace(",", ".")
    elif "." in cleaned:
        # Multiple dots → thousands. Single dot followed by exactly 3 digits
        # is also thousands (European style: "120.000").
        parts = cleaned.split(".")
        if len(parts) > 2 or (len(parts) == 2 and len(parts[1]) == 3):
            cleaned = cleaned.replace(".", "")
    try:
        return float(cleaned)
    except ValueError:
        return None


def parse_size(text: Optional[str]) -> Optional[float]:
    """'60 m²' → 60.0  |  '1,200 sqft' → 111.5"""
    if not text:
        return None
    m = re.search(r"([\d.,]+)\s*(m²|m2|sqm|sqft|ft²)", text, re.IGNORECASE)
    if not m:
        # Sometimes the unit is missing — accept a bare number followed by m²
        m = re.search(r"([\d.,]+)", text)
        if not m:
            return None
        return parse_price(m.group(1))
    value = parse_price(m.group(1))
    if value is None:
        return None
    unit = m.group(2).lower()
    if unit in ("sqft", "ft²"):
        return round(value * 0.092903, 1)
    return value


def parse_int(text: Optional[str]) -> Optional[int]:
    if not text:
        return None
    m = re.search(r"\d+", text)
    return int(m.group(0)) if m else None


def collapse_whitespace(text: Optional[str]) -> Optional[str]:
    if not text:
        return None
    return re.sub(r"\s+", " ", text).strip() or None
