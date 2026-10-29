"""Quick manual check for Stage 2. Run while the app is running:  python test_stage2.py"""
import http.client
import json


def call(method, path, body=None):
    conn = http.client.HTTPConnection("localhost", 5000)
    headers = {"Content-Type": "application/json"} if body else {}
    conn.request(method, path, json.dumps(body) if body else None, headers)
    resp = conn.getresponse()
    data = resp.read()
    return resp.status, resp.getheader("X-Cache"), data


status, _, data = call("POST", "/shorten", {"url": "https://www.google.com"})
print("Create:", status, data.decode())
code = json.loads(data)["short_code"]

print("\n--- Cache check (create warms the cache, so expect HIT) ---")
for i in range(2):
    status, cache, _ = call("GET", f"/{code}")
    print(f"GET /{code}: status={status}, X-Cache={cache}")

print("\n--- Rate limit check (limit is 10/min) ---")
for i in range(1, 13):
    status, _, _ = call("POST", "/shorten", {"url": "https://example.com"})
    print(f"Request {i}: {status}")
