"""Tests for http_client.py.

Coverage targets (all previously at 28%):
  http_get()        — lines 18-24
  http_get_text()   — lines 28-34
  http_post()       — lines 38-46
  http_post_form()  — lines 50-58
  http_patch()      — lines 62-70
  HttpRequestError  — lines 10-14
"""
from __future__ import annotations

import io
import json
import unittest
import urllib.error
import urllib.request
from unittest.mock import MagicMock, patch

from assistant_app.http_client import (
    HttpRequestError,
    http_get,
    http_get_text,
    http_patch,
    http_post,
    http_post_form,
)

# ---------------------------------------------------------------------------
# HttpRequestError
# ---------------------------------------------------------------------------

class TestHttpRequestError(unittest.TestCase):

    def test_stores_status_code(self) -> None:
        err = HttpRequestError("Not Found", status_code=404, body="page not found")
        self.assertEqual(err.status_code, 404)

    def test_stores_body(self) -> None:
        err = HttpRequestError("Bad Request", status_code=400, body='{"error":"bad"}')
        self.assertEqual(err.body, '{"error":"bad"}')

    def test_default_status_code_is_none(self) -> None:
        err = HttpRequestError("Something went wrong")
        self.assertIsNone(err.status_code)

    def test_default_body_is_empty_string(self) -> None:
        err = HttpRequestError("Something went wrong")
        self.assertEqual(err.body, "")

    def test_message_is_accessible_via_str(self) -> None:
        err = HttpRequestError("Network error", status_code=503)
        self.assertIn("Network error", str(err))

    def test_is_exception_subclass(self) -> None:
        err = HttpRequestError("msg")
        self.assertIsInstance(err, Exception)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_mock_response(body: bytes, status: int = 200):
    """Build a context-manager-compatible mock for urllib.request.urlopen."""
    mock_resp = MagicMock()
    mock_resp.read.return_value = body
    mock_resp.__enter__ = lambda s: s
    mock_resp.__exit__ = MagicMock(return_value=False)
    return mock_resp


def _make_http_error(code: int, body: bytes = b"error body"):
    """Build a urllib.error.HTTPError for simulating HTTP failures."""
    err = urllib.error.HTTPError(
        url="https://example.com",
        code=code,
        msg=f"HTTP {code}",
        hdrs=MagicMock(),
        fp=io.BytesIO(body),
    )
    return err


# ---------------------------------------------------------------------------
# http_get
# ---------------------------------------------------------------------------

class TestHttpGet(unittest.TestCase):

    def test_returns_parsed_json_on_success(self) -> None:
        response_body = json.dumps({"key": "value"}).encode("utf-8")
        mock_resp = _make_mock_response(response_body)

        with patch("urllib.request.urlopen", return_value=mock_resp):
            result = http_get("https://example.com/api")

        self.assertEqual(result, {"key": "value"})

    def test_raises_http_request_error_on_http_error(self) -> None:
        with patch("urllib.request.urlopen", side_effect=_make_http_error(404, b"not found")), self.assertRaises(HttpRequestError) as ctx:
            http_get("https://example.com/api")

        self.assertEqual(ctx.exception.status_code, 404)
        self.assertIn("not found", ctx.exception.body)

    def test_sends_headers_in_request(self) -> None:
        response_body = json.dumps({}).encode("utf-8")
        mock_resp = _make_mock_response(response_body)

        captured_req: list[urllib.request.Request] = []
        def fake_urlopen(req):
            captured_req.append(req)
            return mock_resp

        with patch("urllib.request.urlopen", side_effect=fake_urlopen):
            http_get("https://example.com", headers={"Authorization": "Bearer tok"})

        self.assertEqual(captured_req[0].get_header("Authorization"), "Bearer tok")

    def test_works_with_no_headers(self) -> None:
        response_body = json.dumps({"items": []}).encode("utf-8")
        mock_resp = _make_mock_response(response_body)

        with patch("urllib.request.urlopen", return_value=mock_resp):
            result = http_get("https://example.com/items")

        self.assertEqual(result, {"items": []})

    def test_raises_http_request_error_on_401(self) -> None:
        with patch("urllib.request.urlopen", side_effect=_make_http_error(401, b"Unauthorized")), self.assertRaises(HttpRequestError) as ctx:
            http_get("https://example.com/protected")

        self.assertEqual(ctx.exception.status_code, 401)

    def test_raises_http_request_error_on_500(self) -> None:
        with patch("urllib.request.urlopen", side_effect=_make_http_error(500, b"server error")), self.assertRaises(HttpRequestError) as ctx:
            http_get("https://example.com/api")

        self.assertEqual(ctx.exception.status_code, 500)


# ---------------------------------------------------------------------------
# http_get_text
# ---------------------------------------------------------------------------

class TestHttpGetText(unittest.TestCase):

    def test_returns_plain_text_on_success(self) -> None:
        body = b"Hello, world!"
        mock_resp = _make_mock_response(body)

        with patch("urllib.request.urlopen", return_value=mock_resp):
            result = http_get_text("https://example.com/text")

        self.assertEqual(result, "Hello, world!")

    def test_raises_http_request_error_on_http_error(self) -> None:
        with patch("urllib.request.urlopen", side_effect=_make_http_error(403, b"forbidden")), self.assertRaises(HttpRequestError) as ctx:
            http_get_text("https://example.com/text")

        self.assertEqual(ctx.exception.status_code, 403)
        self.assertIn("forbidden", ctx.exception.body)

    def test_returns_utf8_decoded_string(self) -> None:
        body = "café résumé".encode()
        mock_resp = _make_mock_response(body)

        with patch("urllib.request.urlopen", return_value=mock_resp):
            result = http_get_text("https://example.com/text")

        self.assertEqual(result, "café résumé")

    def test_sends_headers_in_request(self) -> None:
        body = b"content"
        mock_resp = _make_mock_response(body)
        captured: list[urllib.request.Request] = []

        def fake_urlopen(req):
            captured.append(req)
            return mock_resp

        with patch("urllib.request.urlopen", side_effect=fake_urlopen):
            http_get_text("https://example.com", headers={"X-Token": "abc"})

        self.assertEqual(captured[0].get_header("X-token"), "abc")


# ---------------------------------------------------------------------------
# http_post
# ---------------------------------------------------------------------------

class TestHttpPost(unittest.TestCase):

    def test_returns_parsed_json_on_success(self) -> None:
        response_body = json.dumps({"id": "new-item-1"}).encode("utf-8")
        mock_resp = _make_mock_response(response_body)

        with patch("urllib.request.urlopen", return_value=mock_resp):
            result = http_post("https://example.com/items", {"name": "widget"})

        self.assertEqual(result, {"id": "new-item-1"})

    def test_raises_http_request_error_on_http_error(self) -> None:
        with patch("urllib.request.urlopen", side_effect=_make_http_error(422, b"invalid data")), self.assertRaises(HttpRequestError) as ctx:
            http_post("https://example.com/items", {"bad": "data"})

        self.assertEqual(ctx.exception.status_code, 422)

    def test_sets_content_type_to_json(self) -> None:
        response_body = json.dumps({}).encode("utf-8")
        mock_resp = _make_mock_response(response_body)
        captured: list[urllib.request.Request] = []

        def fake_urlopen(req):
            captured.append(req)
            return mock_resp

        with patch("urllib.request.urlopen", side_effect=fake_urlopen):
            http_post("https://example.com/api", {"a": 1})

        self.assertEqual(captured[0].get_header("Content-type"), "application/json")

    def test_sends_json_encoded_body(self) -> None:
        response_body = json.dumps({}).encode("utf-8")
        mock_resp = _make_mock_response(response_body)
        captured: list[urllib.request.Request] = []

        def fake_urlopen(req):
            captured.append(req)
            return mock_resp

        payload = {"title": "Buy groceries", "notes": "milk and eggs"}
        with patch("urllib.request.urlopen", side_effect=fake_urlopen):
            http_post("https://example.com/tasks", payload)

        sent_data = json.loads(captured[0].data.decode("utf-8"))
        self.assertEqual(sent_data, payload)

    def test_uses_post_method(self) -> None:
        response_body = json.dumps({}).encode("utf-8")
        mock_resp = _make_mock_response(response_body)
        captured: list[urllib.request.Request] = []

        def fake_urlopen(req):
            captured.append(req)
            return mock_resp

        with patch("urllib.request.urlopen", side_effect=fake_urlopen):
            http_post("https://example.com/api", {})

        self.assertEqual(captured[0].get_method(), "POST")

    def test_merges_extra_headers(self) -> None:
        response_body = json.dumps({}).encode("utf-8")
        mock_resp = _make_mock_response(response_body)
        captured: list[urllib.request.Request] = []

        def fake_urlopen(req):
            captured.append(req)
            return mock_resp

        with patch("urllib.request.urlopen", side_effect=fake_urlopen):
            http_post("https://example.com/api", {}, headers={"Authorization": "Bearer tok"})

        self.assertEqual(captured[0].get_header("Authorization"), "Bearer tok")


# ---------------------------------------------------------------------------
# http_post_form
# ---------------------------------------------------------------------------

class TestHttpPostForm(unittest.TestCase):

    def test_returns_parsed_json_on_success(self) -> None:
        response_body = json.dumps({"access_token": "abc123"}).encode("utf-8")
        mock_resp = _make_mock_response(response_body)

        with patch("urllib.request.urlopen", return_value=mock_resp):
            result = http_post_form(
                "https://example.com/token",
                {"grant_type": "authorization_code", "code": "XYZ"},
            )

        self.assertEqual(result, {"access_token": "abc123"})

    def test_raises_http_request_error_on_http_error(self) -> None:
        with patch("urllib.request.urlopen", side_effect=_make_http_error(400, b"bad request")), self.assertRaises(HttpRequestError) as ctx:
            http_post_form("https://example.com/token", {"grant_type": "bad"})

        self.assertEqual(ctx.exception.status_code, 400)

    def test_sets_content_type_to_form_urlencoded(self) -> None:
        response_body = json.dumps({}).encode("utf-8")
        mock_resp = _make_mock_response(response_body)
        captured: list[urllib.request.Request] = []

        def fake_urlopen(req):
            captured.append(req)
            return mock_resp

        with patch("urllib.request.urlopen", side_effect=fake_urlopen):
            http_post_form("https://example.com/form", {"key": "value"})

        self.assertIn("application/x-www-form-urlencoded", captured[0].get_header("Content-type"))

    def test_sends_url_encoded_body(self) -> None:
        import urllib.parse

        response_body = json.dumps({}).encode("utf-8")
        mock_resp = _make_mock_response(response_body)
        captured: list[urllib.request.Request] = []

        def fake_urlopen(req):
            captured.append(req)
            return mock_resp

        fields = {"client_id": "my-client", "grant_type": "authorization_code"}
        with patch("urllib.request.urlopen", side_effect=fake_urlopen):
            http_post_form("https://example.com/token", fields)

        sent_fields = dict(urllib.parse.parse_qsl(captured[0].data.decode("utf-8")))
        self.assertEqual(sent_fields["client_id"], "my-client")
        self.assertEqual(sent_fields["grant_type"], "authorization_code")

    def test_uses_post_method(self) -> None:
        response_body = json.dumps({}).encode("utf-8")
        mock_resp = _make_mock_response(response_body)
        captured: list[urllib.request.Request] = []

        def fake_urlopen(req):
            captured.append(req)
            return mock_resp

        with patch("urllib.request.urlopen", side_effect=fake_urlopen):
            http_post_form("https://example.com/form", {"key": "val"})

        self.assertEqual(captured[0].get_method(), "POST")


# ---------------------------------------------------------------------------
# http_patch
# ---------------------------------------------------------------------------

class TestHttpPatch(unittest.TestCase):

    def test_returns_parsed_json_on_success(self) -> None:
        response_body = json.dumps({"status": "updated"}).encode("utf-8")
        mock_resp = _make_mock_response(response_body)

        with patch("urllib.request.urlopen", return_value=mock_resp):
            result = http_patch("https://example.com/tasks/1", {"status": "completed"})

        self.assertEqual(result, {"status": "updated"})

    def test_raises_http_request_error_on_http_error(self) -> None:
        with patch("urllib.request.urlopen", side_effect=_make_http_error(404, b"not found")), self.assertRaises(HttpRequestError) as ctx:
            http_patch("https://example.com/tasks/999", {"status": "done"})

        self.assertEqual(ctx.exception.status_code, 404)

    def test_uses_patch_method(self) -> None:
        response_body = json.dumps({}).encode("utf-8")
        mock_resp = _make_mock_response(response_body)
        captured: list[urllib.request.Request] = []

        def fake_urlopen(req):
            captured.append(req)
            return mock_resp

        with patch("urllib.request.urlopen", side_effect=fake_urlopen):
            http_patch("https://example.com/tasks/1", {"done": True})

        self.assertEqual(captured[0].get_method(), "PATCH")

    def test_sets_content_type_to_json(self) -> None:
        response_body = json.dumps({}).encode("utf-8")
        mock_resp = _make_mock_response(response_body)
        captured: list[urllib.request.Request] = []

        def fake_urlopen(req):
            captured.append(req)
            return mock_resp

        with patch("urllib.request.urlopen", side_effect=fake_urlopen):
            http_patch("https://example.com/tasks/1", {"done": True})

        self.assertEqual(captured[0].get_header("Content-type"), "application/json")

    def test_sends_json_encoded_body(self) -> None:
        response_body = json.dumps({}).encode("utf-8")
        mock_resp = _make_mock_response(response_body)
        captured: list[urllib.request.Request] = []

        def fake_urlopen(req):
            captured.append(req)
            return mock_resp

        updates = {"status": "completed", "hidden": True}
        with patch("urllib.request.urlopen", side_effect=fake_urlopen):
            http_patch("https://example.com/tasks/1", updates)

        sent_data = json.loads(captured[0].data.decode("utf-8"))
        self.assertEqual(sent_data, updates)

    def test_merges_extra_headers(self) -> None:
        response_body = json.dumps({}).encode("utf-8")
        mock_resp = _make_mock_response(response_body)
        captured: list[urllib.request.Request] = []

        def fake_urlopen(req):
            captured.append(req)
            return mock_resp

        with patch("urllib.request.urlopen", side_effect=fake_urlopen):
            http_patch("https://example.com/tasks/1", {}, headers={"Authorization": "Bearer t"})

        self.assertEqual(captured[0].get_header("Authorization"), "Bearer t")


if __name__ == "__main__":
    unittest.main()
