from locust import HttpUser, between, task


class RedirectUser(HttpUser):
    """Hammers the redirect endpoint. Code '1' must already exist
    (create it first with POST /shorten)."""

    wait_time = between(0.05, 0.2)

    @task
    def redirect(self):
        self.client.get("/1", allow_redirects=False, name="/[code]")
