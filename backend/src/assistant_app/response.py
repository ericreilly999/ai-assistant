from __future__ import annotations

import json
import os
from typing import Any


_cors_origin = os.environ.get("CORS_ALLOWED_ORIGINS", "*")

CORS_HEADERS = {
    "Access-Control-Allow-Origin": _cors_origin,
    "Access-Control-Allow-Headers": "content-type,authorization",
    "Access-Control-Allow-Methods": "GET,POST,OPTIONS",
}


def json_response(status_code: int, body: dict[str, Any]) -> dict[str, Any]:
    return {
        "statusCode": status_code,
        "headers": {
            "Content-Type": "application/json",
            **CORS_HEADERS,
        },
        "body": json.dumps(body),
    }


def html_response(status_code: int, body: str) -> dict[str, Any]:
    return {
        "statusCode": status_code,
        "headers": {
            "Content-Type": "text/html; charset=utf-8",
            **CORS_HEADERS,
        },
        "body": body,
    }


def redirect_response(location: str) -> dict[str, Any]:
    return {
        "statusCode": 302,
        "headers": {
            "Location": location,
            **CORS_HEADERS,
        },
        "body": "",
    }
