URL = "https://www.google.com"


def create(client, url=URL):
    return client.post("/shorten", json={"url": url})


def test_shorten_and_redirect(client):
    resp = create(client)
    assert resp.status_code == 201
    code = resp.get_json()["short_code"]

    resp = client.get(f"/{code}")
    assert resp.status_code == 302
    assert resp.headers["Location"] == URL


def test_invalid_url_rejected(client):
    resp = create(client, "not-a-url")
    assert resp.status_code == 400


def test_unknown_code_returns_404(client):
    assert client.get("/zzzz").status_code == 404


def test_invalid_characters_return_404(client):
    assert client.get("/bad-code!").status_code == 404


def test_cache_hit_after_create(client):
    code = create(client).get_json()["short_code"]
    resp = client.get(f"/{code}")
    assert resp.headers["X-Cache"] == "HIT"


def test_cache_miss_then_hit(client, fake_redis):
    code = create(client).get_json()["short_code"]
    fake_redis.flushall()  # simulate an empty cache

    assert client.get(f"/{code}").headers["X-Cache"] == "MISS"
    assert client.get(f"/{code}").headers["X-Cache"] == "HIT"


def test_rate_limit_blocks_after_10_requests(client):
    for _ in range(10):
        assert create(client).status_code == 201

    resp = create(client)
    assert resp.status_code == 429
    assert "Retry-After" in resp.headers
