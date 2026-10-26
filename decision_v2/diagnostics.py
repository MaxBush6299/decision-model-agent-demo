import asyncio
import json
import re
from time import monotonic
from typing import Callable

import httpx2 as httpx

from .contracts import DemoError


PRIVATE_KEYS = frozenset({
    "authorization", "proxy_authorization", "api_key", "apikey", "access_token",
    "refresh_token", "id_token", "token", "password", "secret", "client_secret",
    "encrypted_content", "previous_response_id", "conversation", "call_id",
    "id", "system_fingerprint", "headers",
})
REQUEST_ID_HEADERS = ("x-request-id", "apim-request-id", "x-ms-request-id", "request-id")


def sanitize(value):
    """Sanitize independent diagnostic copies, never request/response objects."""
    if isinstance(value, dict):
        return {key: ("[redacted]" if key.lower().replace("-", "_") in PRIVATE_KEYS
                      else sanitize(item)) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [sanitize(item) for item in value]
    if not isinstance(value, str):
        return value
    value = re.sub(r"https?://[^\s<>\"']+", "[endpoint omitted]", value, flags=re.I)
    value = re.sub(r"\bBearer\s+[^\s,\"'}]+", "Bearer [redacted]", value, flags=re.I)
    value = re.sub(r"\beyJ[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+",
                   "[redacted token]", value)
    private = "|".join(re.escape(key).replace("_", "[-_]") for key in PRIVATE_KEYS)
    value = re.sub(
        rf"(?i)(?<![\w-])((?:{private})[\"']?\s*[:=]\s*)(?:\"[^\"]*\"|'[^']*'|[^\s,}}\]]+)",
        r"\1[redacted]", value,
    )
    return value


def response_diagnostics(response: httpx.Response) -> dict:
    details = {"http_status": response.status_code}
    for header in REQUEST_ID_HEADERS:
        if request_id := response.headers.get(header):
            details["request_id"] = sanitize(request_id)
            break
    try:
        body = response.json()
    except (json.JSONDecodeError, UnicodeDecodeError):
        body = response.text
    except httpx.ResponseNotRead:
        details["body_unavailable"] = "Response body was not fully read."
        return details
    details["body"] = sanitize(body)
    if isinstance(body, dict):
        details["native_status"] = sanitize(body.get("status"))
        details["incomplete_details"] = sanitize(body.get("incomplete_details"))
    return details


def exception_diagnostics(exc: BaseException, response: httpx.Response | None = None) -> dict:
    chain, seen = [], set()
    while exc is not None and id(exc) not in seen:
        seen.add(id(exc))
        item = {
            "type": f"{type(exc).__module__}.{type(exc).__name__}",
            "message": sanitize(getattr(exc, "diagnostic_message", str(exc))),
        }
        existing = getattr(exc, "diagnostics", None)
        if existing and existing.get("response"):
            item["response"] = existing["response"]
        native_response = getattr(exc, "response", None)
        if isinstance(native_response, httpx.Response):
            item["response"] = response_diagnostics(native_response)
        if request_id := getattr(exc, "request_id", None):
            item["request_id"] = sanitize(request_id)
        chain.append(item)
        exc = exc.__cause__ or exc.__context__
    details = {"exception_chain": chain}
    if response is not None:
        details["response"] = response_diagnostics(response)
    return sanitize(details)


def diagnostic_error(message: str, exc: BaseException,
                     response: httpx.Response | None = None) -> DemoError:
    details = exception_diagnostics(exc, response)
    safe_message = sanitize(message)
    error = DemoError(f"{safe_message} Diagnostics: {json.dumps(details, ensure_ascii=True)}")
    error.diagnostic_message = safe_message
    error.diagnostics = details
    return error


class DiagnosticCaptureTransport(httpx.AsyncBaseTransport):
    """Opt-in private capture with failure records even when response reading fails."""

    def __init__(self, inner: httpx.AsyncBaseTransport, current_call: Callable):
        self.inner, self.current_call = inner, current_call
        self.records = []

    async def handle_async_request(self, request):
        record = {"call": self.current_call(), "path": request.url.path,
                  "request": sanitize(json.loads(request.content))}
        self.records.append(record)
        started, response = monotonic(), None
        try:
            response = await self.inner.handle_async_request(request)
            record["status"] = response.status_code
            await response.aread()
            details = response_diagnostics(response)
            record["response_details"] = details
            record["response"] = details.get("body")
            return response
        except (httpx.HTTPError, OSError, asyncio.CancelledError) as exc:
            record["failure"] = exception_diagnostics(exc, response)
            if response is not None:
                await response.aclose()
            raise
        finally:
            record["elapsed_seconds"] = round(monotonic() - started, 3)

    async def aclose(self):
        await self.inner.aclose()
