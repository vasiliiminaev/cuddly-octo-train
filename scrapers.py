"""Site-specific scrapers.

Each scraper takes a BeautifulSoup-parsed page + the original URL and
returns a partial dict of fields. A generic fallback is used when no
site-specific scraper matches the host.
"""
from __future__ import annotations

import json
import re
from typing import Callable, Dict, Optional
from urllib.parse import urlparse

from bs4 import BeautifulSoup

from .cleaning import collapse_whitespace, parse_int, parse_price, parse_size


# ---------- helpers ----------

def _jsonld(soup: BeautifulSoup) -> list[dict]:
    """Return all JSON-LD blocks parsed as dicts (flattened from arrays)."""
    out: list[dict] = []
    for tag in soup.find_all("script", type="application/ld+json"):
        try:
            data = json.loads(tag.string or "")
        except Exception:
            continue
        if isinstance(data, list):
            out.extend(d for d in data if isinstance(d, dict))
        elif isinstance(data, dict):
            if "@graph" in data and isinstance(data["@graph"], list):
                out.extend(d for d in data["@graph"] if isinstance(d, dict))
            else:
                out.append(data)
    return out


def _meta(soup: BeautifulSoup, prop: str) -> Optional[str]:
    tag = soup.find("meta", attrs={"property": prop}) or soup.find("meta", attrs={"name": prop})
    return tag["content"].strip() if tag and tag.get("content") else None


# ---------- site scrapers ----------

def scrape_idealista(soup: BeautifulSoup, url: str) -> dict:
    out: dict = {"source": "idealista"}

    # Title + description
    out["title"] = collapse_whitespace(
        getattr(soup.find("h1"), "get_text", lambda **_: None)(strip=True)
    )
    desc_tag = soup.select_one(".comment, .adCommentsLanguage")
    out["description"] = collapse_whitespace(desc_tag.get_text(" ", strip=True) if desc_tag else None)

    # Price
    price_tag = soup.select_one(".info-data-price, .price, [class*='price']")
    out["price"] = parse_price(price_tag.get_text(" ", strip=True) if price_tag else None)

    # Size + rooms
    info_features = soup.select(".info-features span, .details-property-feature-one li")
    text_blob = " | ".join(s.get_text(" ", strip=True) for s in info_features)
    out["size"] = parse_size(text_blob)
    rooms_match = re.search(r"(\d+)\s*(hab|bed|room|dorm)", text_blob, re.IGNORECASE)
    out["rooms"] = int(rooms_match.group(1)) if rooms_match else None
    bath_match = re.search(r"(\d+)\s*(baño|bath)", text_blob, re.IGNORECASE)
    out["bathrooms"] = int(bath_match.group(1)) if bath_match else None

    # Location
    loc_tag = soup.select_one("#headerMap li, .main-info__title-minor, [class*='location']")
    out["location"] = collapse_whitespace(loc_tag.get_text(" ", strip=True) if loc_tag else None)

    # Images
    out["images"] = [img["src"] for img in soup.select("picture img[src]")][:10]

    return out


def scrape_seloger(soup: BeautifulSoup, url: str) -> dict:
    out: dict = {"source": "seloger"}
    out["title"] = collapse_whitespace(
        getattr(soup.find("h1"), "get_text", lambda **_: None)(strip=True)
    )
    price_tag = soup.select_one("[data-test='price'], .Summary__PriceText")
    out["price"] = parse_price(price_tag.get_text(" ", strip=True) if price_tag else None)
    size_tag = soup.find(string=re.compile(r"\d+\s*m²"))
    out["size"] = parse_size(str(size_tag) if size_tag else None)
    loc_tag = soup.select_one("[data-test='address'], .Summary__Address")
    out["location"] = collapse_whitespace(loc_tag.get_text(" ", strip=True) if loc_tag else None)
    desc_tag = soup.select_one("[data-test='description'], .description")
    out["description"] = collapse_whitespace(desc_tag.get_text(" ", strip=True) if desc_tag else None)
    return out


def scrape_immobiliare(soup: BeautifulSoup, url: str) -> dict:
    out: dict = {"source": "immobiliare"}
    out["title"] = collapse_whitespace(
        getattr(soup.find("h1"), "get_text", lambda **_: None)(strip=True)
    )
    price_tag = soup.select_one(".im-mainFeatures__price, [class*='price']")
    out["price"] = parse_price(price_tag.get_text(" ", strip=True) if price_tag else None)
    feat = soup.select(".im-mainFeatures__list li, [class*='feature']")
    blob = " | ".join(s.get_text(" ", strip=True) for s in feat)
    out["size"] = parse_size(blob)
    loc_tag = soup.select_one(".im-location, [class*='location']")
    out["location"] = collapse_whitespace(loc_tag.get_text(" ", strip=True) if loc_tag else None)
    desc_tag = soup.select_one(".im-description__text, [class*='description']")
    out["description"] = collapse_whitespace(desc_tag.get_text(" ", strip=True) if desc_tag else None)
    return out


# ---------- generic fallback ----------

def scrape_generic(soup: BeautifulSoup, url: str) -> dict:
    """Use OpenGraph + JSON-LD + heuristics. Works on most listing sites."""
    out: dict = {"source": urlparse(url).netloc}

    out["title"] = _meta(soup, "og:title") or collapse_whitespace(
        getattr(soup.find("h1"), "get_text", lambda **_: None)(strip=True)
    )
    out["description"] = _meta(soup, "og:description") or _meta(soup, "description")

    images = []
    og_image = _meta(soup, "og:image")
    if og_image:
        images.append(og_image)
    out["images"] = images

    # JSON-LD: schema.org/Product, RealEstateListing, Residence
    for block in _jsonld(soup):
        types = block.get("@type")
        types = [types] if isinstance(types, str) else (types or [])

        offers = block.get("offers") or {}
        if isinstance(offers, list):
            offers = offers[0] if offers else {}
        if not out.get("price") and isinstance(offers, dict):
            out["price"] = parse_price(str(offers.get("price") or ""))
            if offers.get("priceCurrency"):
                out["currency"] = offers["priceCurrency"]

        addr = block.get("address") or {}
        if isinstance(addr, dict):
            loc_parts = [addr.get("addressLocality"), addr.get("addressRegion"), addr.get("addressCountry")]
            loc = ", ".join(p for p in loc_parts if p)
            if loc and not out.get("location"):
                out["location"] = loc

        for key in ("floorSize", "size", "area"):
            v = block.get(key)
            if isinstance(v, dict):
                v = v.get("value")
            if v and not out.get("size"):
                out["size"] = parse_size(str(v))

        if not out.get("rooms"):
            out["rooms"] = parse_int(str(block.get("numberOfRooms") or block.get("numberOfBedrooms") or ""))

    # Last-resort price heuristic from visible text
    if not out.get("price"):
        m = re.search(r"€\s*[\d.,]+|\$\s*[\d.,]+|\b[\d.,]{4,}\s*€", soup.get_text(" "))
        if m:
            out["price"] = parse_price(m.group(0))

    # Last-resort size heuristic
    if not out.get("size"):
        m = re.search(r"\b\d{1,4}[\s.,]?\d*\s*(?:m²|m2|sqm)\b", soup.get_text(" "), re.IGNORECASE)
        if m:
            out["size"] = parse_size(m.group(0))

    return out


# ---------- registry ----------

SCRAPERS: Dict[str, Callable[[BeautifulSoup, str], dict]] = {
    "idealista": scrape_idealista,
    "seloger": scrape_seloger,
    "immobiliare": scrape_immobiliare,
}


def pick_scraper(url: str) -> Callable[[BeautifulSoup, str], dict]:
    host = urlparse(url).netloc.lower()
    for key, fn in SCRAPERS.items():
        if key in host:
            return fn
    return scrape_generic
