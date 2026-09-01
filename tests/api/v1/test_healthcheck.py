from fastapi.testclient import TestClient


class TestGetHealthcheck:
    def test_returns_ok_status(self, client: TestClient) -> None:
        response = client.get("/api/v1/healthcheck")

        assert response.status_code == 200
        assert response.json() == {"status": "ok"}
