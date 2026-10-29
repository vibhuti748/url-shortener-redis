import os
import string
from datetime import datetime, timezone
from urllib.parse import urlparse

import redis
from flask import Flask, jsonify, redirect, request
from flask_sqlalchemy import SQLAlchemy

app = Flask(__name__)
app.config["SQLALCHEMY_DATABASE_URI"] = os.getenv(
    "DATABASE_URL",
    "postgresql+psycopg2://shortener:shortener@localhost:5432/shortener",
)
db = SQLAlchemy(app)

r = redis.Redis.from_url(
    os.getenv("REDIS_URL", "redis://localhost:6379/0"),
    decode_responses=True,
)

CACHE_ENABLED = os.getenv("CACHE_ENABLED", "true").lower() == "true"
CACHE_TTL_SECONDS = 3600      # keep cached URLs for 1 hour
RATE_LIMIT = int(os.getenv("RATE_LIMIT", "10"))  # max requests ...
RATE_WINDOW_SECONDS = 60      # ... per minute, per IP

ALPHABET = string.digits + string.ascii_letters  # 62 characters


def encode(n: int) -> str:
    if n == 0:
        return ALPHABET[0]
    chars = []
    while n:
        n, rem = divmod(n, 62)
        chars.append(ALPHABET[rem])
    return "".join(reversed(chars))


def decode(code: str) -> int:
    n = 0
    for c in code:
        n = n * 62 + ALPHABET.index(c)  # raises ValueError if invalid
    return n


class Url(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    original_url = db.Column(db.Text, nullable=False)
    created_at = db.Column(
        db.DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
    )


def is_valid_url(url: str) -> bool:
    parsed = urlparse(url)
    return parsed.scheme in ("http", "https") and bool(parsed.netloc)


def check_rate_limit(ip: str):
    """Fixed-window rate limiter using Redis INCR + EXPIRE.
    Returns (is_limited, seconds_until_reset)."""
    key = f"rl:{ip}"
    count = r.incr(key)
    if count == 1:
        r.expire(key, RATE_WINDOW_SECONDS)
    return count > RATE_LIMIT, max(r.ttl(key), 0)


@app.post("/shorten")
def shorten():
    limited, retry_after = check_rate_limit(request.remote_addr)
    if limited:
        resp = jsonify(error="Too many requests. Try again later.")
        resp.status_code = 429
        resp.headers["Retry-After"] = str(retry_after)
        return resp

    data = request.get_json(silent=True) or {}
    url = data.get("url", "").strip()
    if not is_valid_url(url):
        return jsonify(error="Provide a valid http/https URL"), 400

    row = Url(original_url=url)
    db.session.add(row)
    db.session.commit()

    code = encode(row.id)
    if CACHE_ENABLED:
        r.setex(f"url:{code}", CACHE_TTL_SECONDS, url)  # warm the cache
    return jsonify(short_code=code, short_url=f"{request.host_url}{code}"), 201


@app.get("/<code>")
def go(code):
    # 1. Try the cache first
    cached = r.get(f"url:{code}") if CACHE_ENABLED else None
    if cached:
        resp = redirect(cached, code=302)
        resp.headers["X-Cache"] = "HIT"
        return resp

    # 2. Cache miss: fall back to the database
    try:
        url_id = decode(code)
    except ValueError:
        return jsonify(error="Not found"), 404

    row = db.session.get(Url, url_id)
    if row is None:
        return jsonify(error="Not found"), 404

    # 3. Store in cache for next time
    if CACHE_ENABLED:
        r.setex(f"url:{code}", CACHE_TTL_SECONDS, row.original_url)
    resp = redirect(row.original_url, code=302)
    resp.headers["X-Cache"] = "MISS"
    return resp


with app.app_context():
    db.create_all()

if __name__ == "__main__":
    app.run(debug=True, port=5000)
