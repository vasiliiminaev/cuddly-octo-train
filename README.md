# Lumen Scraper Service

FastAPI + Playwright + BeautifulSoup service that scrapes a property listing
URL (Idealista-like) and returns clean structured JSON.

## Endpoints

- `GET  /health` → `{ "status": "ok" }`
- `POST /scrape` → body `{ "url": "https://www.idealista.com/inmueble/..." }`

### Response shape

```json
{
  "url": "https://www.idealista.com/inmueble/12345",
  "source": "idealista.com",
  "price": 120000,
  "currency": "EUR",
  "size": 60,
  "size_unit": "m2",
  "location": "Valencia",
  "title": "Piso en Ruzafa, Valencia",
  "description": "Bright 2-bed apartment...",
  "rooms": 2,
  "bathrooms": 1,
  "images": ["https://..."]
}
```

Fields that can't be extracted are returned as `null` — never fabricated.

## Run locally

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
playwright install chromium
uvicorn app.main:app --reload
```

## Run with Docker

```bash
docker build -t lumen-scraper .
docker run -p 8000:8000 --env-file .env lumen-scraper
```

## Deploy

Works on Railway, Fly.io, Render, or any container host. The provided
Dockerfile uses the official Playwright base image so browsers are
pre-installed.

## Plug into Lumen

In `supabase/functions/analyze/index.ts` set the `ANALYSIS_SERVICE_URL`
secret to your deployed URL and uncomment the `fetch()` block in
`runAnalysis()`.

## Legal

Respect the target site's robots.txt and Terms of Service. This code is for
education and personal use; do not run it at scale against sites that
forbid scraping.
