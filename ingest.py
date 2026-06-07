"""Send scraped property data to Supabase via Edge Function."""
import os
import logging
import httpx

log = logging.getLogger("scraper")

INGEST_URL = os.getenv("SUPABASE_INGEST_URL", "")
SCRAPER_SECRET = os.getenv("SCRAPER_SECRET", "")


async def ingest_property(data: dict) -> dict | None:
    """
    POST property data to the Supabase Edge Function.
    Returns the response JSON on success, None on failure.
    """
    if not INGEST_URL or not SCRAPER_SECRET:
        log.warning("Ingest not configured — skipping Supabase push")
        return None

    payload = {
        "url":      data.get("url"),
        "source":   data.get("source"),
        "title":    data.get("title"),
        "price":    data.get("price"),
        "location": data.get("location"),
        "size":     data.get("size"),
        "rooms":    data.get("rooms"),
        "raw_data": data,
    }

    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.post(
                INGEST_URL,
                json=payload,
                headers={
                    "Authorization": f"Bearer {SCRAPER_SECRET}",
                    "Content-Type": "application/json",
                },
            )
            if resp.status_code == 200:
                log.info("Ingested to Supabase: %s", resp.json())
                return resp.json()
            else:
                log.error("Ingest failed %s: %s", resp.status_code, resp.text)
                return None
    except Exception as e:
        log.exception("Ingest exception: %s", e)
        return None
