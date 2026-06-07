"""FastAPI app exposing /scrape and /health.

Plug into Lumen by setting `ANALYSIS_SERVICE_URL` to the deployed URL of
this service and uncommenting the fetch() block in
supabase/functions/analyze/index.ts.
"""
from __future__ import annotations

import logging
import os
from contextlib import asynccontextmanager

from bs4 import BeautifulSoup
from fastapi import Depends, FastAPI, HTTPException, Request, status
from fastapi.middleware.cors import CORSMiddleware

from .browser import pool
from .models import ErrorResponse, ScrapeRequest, ScrapeResponse
from .scrapers import pick_scraper
from .ingest import ingest_property

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("scraper")


@asynccontextmanager
async def lifespan(app: FastAPI):
    await pool.start()
    log.info("Browser pool started")
    try:
        yield
    finally:
        await pool.stop()
        log.info("Browser pool stopped")


app = FastAPI(
    title="Lumen Scraper",
    version="1.0.0",
    description="Scrapes property listing URLs into clean JSON.",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
)


def require_token(request: Request) -> None:
    """Optional bearer-token auth. If API_TOKEN is unset, the endpoint is open."""
    expected = os.getenv("API_TOKEN")
    if not expected:
        return
    auth = request.headers.get("authorization", "")
    if not auth.lower().startswith("bearer "):
        raise HTTPException(status_code=401, detail="Missing bearer token")
    if auth.split(" ", 1)[1].strip() != expected:
        raise HTTPException(status_code=403, detail="Invalid token")


@app.get("/health")
async def health() -> dict:
    return {"status": "ok"}


@app.post(
    "/scrape",
    response_model=ScrapeResponse,
    responses={400: {"model": ErrorResponse}, 502: {"model": ErrorResponse}},
)
async def scrape(req: ScrapeRequest, _=Depends(require_token)) -> ScrapeResponse:
    url = str(req.url)
    log.info("Scraping %s", url)
    try:
        html = await pool.fetch_html(url)
    except Exception as e:
        log.exception("Fetch failed")
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=f"Failed to fetch page: {e}")

    soup = BeautifulSoup(html, "html.parser")
    scraper = pick_scraper(url)
    data = scraper(soup, url)

    payload = {
        "url": url,
        "source": data.get("source"),
        "price": data.get("price"),
        "currency": data.get("currency", "EUR"),
        "size": data.get("size"),
        "size_unit": "m2",
        "location": data.get("location"),
        "title": data.get("title"),
        "description": data.get("description"),
        "rooms": data.get("rooms"),
        "bathrooms": data.get("bathrooms"),
        "images": data.get("images", []),
    }
    # Push to Supabase in background (don't block the response)
    import asyncio
    asyncio.create_task(ingest_property(payload))

    return ScrapeResponse(**payload)
