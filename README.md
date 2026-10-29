# URL Shortener

A URL shortening service built with Flask, PostgreSQL and Redis, containerized
with Docker, tested with Pytest, load tested with Locust and deployed to AWS EC2
through a GitHub Actions CI/CD pipeline.

**Live demo:** <add your EC2 URL here>

## Features
- Shorten URLs and redirect via base62 short codes
- Redis cache-aside caching for fast redirects (`X-Cache: HIT/MISS` header)
- Per-IP rate limiting on `/shorten` (fixed window, Redis `INCR` + `EXPIRE`)
- Docker Compose setup for the app, PostgreSQL and Redis
- Automated tests and deployment with GitHub Actions

## Architecture

    Client -> Flask/Gunicorn -> Redis (cache + rate limit counters)
                             -> PostgreSQL (source of truth)

**Redirect flow:** check Redis -> on miss, read PostgreSQL -> store in Redis (1h TTL) -> 302 redirect.

## API

| Method | Path | Description |
|--------|------|-------------|
| POST | `/shorten` | Body: `{"url": "https://example.com"}`. Returns `short_code` and `short_url` (201) |
| GET | `/<code>` | Redirects (302) to the original URL, or 404 |

Rate limit: 10 requests/minute per IP on `/shorten`, then `429` with `Retry-After`.

## Run locally

    docker compose up -d --build
    curl -X POST localhost:5000/shorten -H "Content-Type: application/json" -d '{"url":"https://example.com"}'

## Run tests

    pip install -r requirements-dev.txt
    pytest

Tests use SQLite and fakeredis, so no Docker is needed.

## Load test

    locust -f locustfile.py --headless -u 50 -r 10 -t 30s --host http://localhost:5000

Compare with caching off: set `CACHE_ENABLED=false` and restart the app container.

| Setup | Requests/sec | Median latency |
|-------|--------------|----------------|
| Cache off | <fill in> | <fill in> |
| Cache on | <fill in> | <fill in> |

(Measured locally with 50 concurrent users for 30 seconds.)

## Tech stack
Python, Flask, SQLAlchemy, PostgreSQL, Redis, Docker, Gunicorn, Pytest, Locust,
GitHub Actions, AWS EC2

## Possible improvements
- Click analytics, link expiry and custom aliases
- Nginx and HTTPS, secrets management
- Container registry (ECR) instead of building on the server
