"""
Locust load test for the Universal FastAPI Foundation API.

Run with: locust -f tests/performance/locustfile.py --host=http://localhost:8000
"""

from locust import HttpUser, task, between


class APIUser(HttpUser):
    """Simulated user hitting the API endpoints."""

    wait_time = between(1, 3)
    host = "http://localhost:8000"

    @task(3)
    def test_health_endpoint(self):
        """Hit the health check endpoint."""
        self.client.get("/health")

    @task(2)
    def test_root_endpoint(self):
        """Hit the root endpoint."""
        self.client.get("/")

    @task(1)
    def test_api_docs(self):
        """Hit the OpenAPI docs endpoint."""
        self.client.get("/api/v1/openapi.json")
