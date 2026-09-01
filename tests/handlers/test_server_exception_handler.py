import json

import pytest

from fastapi import Request

from crm_be.core.config.base import core_settings
from crm_be.handlers.server_exception_handler import handler


def build_request(method: str = "GET", path: str = "/api/v1/test") -> Request:
    scope = {"type": "http", "method": method, "path": path, "headers": [], "query_string": b""}
    return Request(scope)


class TestHandler:
    def test_returns_status_code_500(self) -> None:
        response = handler(build_request(), ValueError("boom"))

        assert response.status_code == 500

    def test_returns_generic_error_detail(self) -> None:
        response = handler(build_request(), ValueError("boom"))

        body = json.loads(response.body)
        assert body["detail"] == "システムエラーが発生しました。"

    def test_does_not_leak_original_exception_message(self) -> None:
        response = handler(build_request(), ValueError("secret internal detail"))

        body = json.loads(response.body)
        assert "secret internal detail" not in json.dumps(body)

    def test_sets_cors_allow_origin_header(self) -> None:
        response = handler(build_request(), ValueError("boom"))

        assert response.headers["access-control-allow-origin"] == core_settings.frontend_base_url

    def test_sets_cors_allow_credentials_header(self) -> None:
        response = handler(build_request(), ValueError("boom"))

        assert response.headers["access-control-allow-credentials"] == "true"

    def test_sets_cors_allow_methods_header(self) -> None:
        response = handler(build_request(), ValueError("boom"))

        assert response.headers["access-control-allow-methods"] == "*"

    def test_sets_cors_allow_headers_header(self) -> None:
        response = handler(build_request(), ValueError("boom"))

        assert response.headers["access-control-allow-headers"] == "*"

    def test_logs_error_with_exception_info(self, monkeypatch: pytest.MonkeyPatch) -> None:
        logged: dict[str, object] = {}

        def fake_error(message: str, *, exc_info: Exception) -> None:
            logged["message"] = message
            logged["exc_info"] = exc_info

        monkeypatch.setattr("crm_be.handlers.server_exception_handler.logger.error", fake_error)
        exc = ValueError("boom")

        handler(build_request(method="POST", path="/api/v1/auth/login"), exc)

        assert logged["exc_info"] is exc
        assert "POST" in str(logged["message"])
        assert "/api/v1/auth/login" in str(logged["message"])
