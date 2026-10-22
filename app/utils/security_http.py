"""Bounded single-worker admission control and credential-free operations data.

Production starter runs exactly one worker/replica. Before horizontal scaling,
replace this process-local limiter with shared gateway/Redis admission control.
Daily client AI accounting remains database-backed and independent.
"""
from collections import OrderedDict
import json
import logging
import time
import uuid

logger = logging.getLogger("dash.requests")
logger.setLevel(logging.INFO)
if not logger.handlers:
    handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter("%(message)s"))
    logger.addHandler(handler)
logger.propagate = False


class RequestPolicy:
    def __init__(self, settings):
        self.settings = settings
        self.windows = OrderedDict()
        self.total, self.errors, self.limited = 0, 0, 0
        self.started = time.monotonic()

    def admit(self, identity, category, now=None):
        if not self.settings.rate_limit_enabled:
            return True, 0
        now = time.monotonic() if now is None else now
        limits = {"auth": self.settings.auth_requests_per_minute,
                  "ai": self.settings.ai_requests_per_minute,
                  "api": self.settings.api_requests_per_minute}
        key = (identity, category)
        start, count = self.windows.pop(key, (now, 0))
        if now - start >= 60:
            start, count = now, 0
        # Eviction cannot be used to reset an active bucket: fail closed at cap.
        if len(self.windows) >= 10000:
            expired = [item for item, (stamp, _) in self.windows.items() if now - stamp >= 60]
            for item in expired:
                self.windows.pop(item, None)
            if len(self.windows) >= 10000:
                self.limited += 1
                return False, 60
        self.windows[key] = (start, count + 1)
        if count >= limits[category]:
            self.limited += 1
            return False, max(1, int(61 - (now - start)))
        return True, 0

    def metrics(self):
        return {"requests": self.total, "server_errors": self.errors, "rate_limited": self.limited,
                "uptime_seconds": int(time.monotonic() - self.started), "scope": "single_process"}


def category_for(path, method="GET"):
    if method == "POST" and path.rstrip("/") in {"/auth/login", "/auth/register"}:
        return "auth"
    if method == "POST" and path.startswith(("/insights/", "/reports/")):
        return "ai"
    return "api"


class SecurityHTTPMiddleware:
    def __init__(self, app, settings, policy):
        self.app, self.settings, self.policy = app, settings, policy

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            return await self.app(scope, receive, send)
        request_id, started = uuid.uuid4().hex, time.monotonic()
        self.policy.total += 1
        category = category_for(scope["path"], scope["method"])
        status = 500

        async def safe_send(message):
            nonlocal status
            if message["type"] == "http.response.start":
                status = message["status"]
                headers = [(name, value) for name, value in message.get("headers", [])
                           if name.lower() not in {b"x-request-id", b"x-content-type-options", b"referrer-policy"}]
                headers += [(b"x-request-id", request_id.encode()), (b"x-content-type-options", b"nosniff"),
                            (b"referrer-policy", b"no-referrer")]
                if not any(name.lower() == b"cache-control" for name, _ in headers):
                    headers.append((b"cache-control", b"no-store"))
                if self.settings.app_env == "production":
                    headers.append((b"strict-transport-security", b"max-age=31536000"))
                message = {**message, "headers": headers}
            await send(message)

        async def reject(code, detail, retry=None):
            body = json.dumps({"detail": detail}).encode()
            headers = [(b"content-type", b"application/json"), (b"content-length", str(len(body)).encode())]
            if retry is not None:
                headers.append((b"retry-after", str(retry).encode()))
            await safe_send({"type": "http.response.start", "status": code, "headers": headers})
            await safe_send({"type": "http.response.body", "body": body})

        try:
            # Liveness/readiness must not be denied by the public rate buckets.
            if scope["path"] not in {"/health", "/ready"} and scope["method"] != "OPTIONS":
                identity = (scope.get("client") or ("unknown",))[0]
                allowed, retry = self.policy.admit(identity, category)
                if not allowed:
                    return await reject(429, "Muitas requisições. Aguarde antes de tentar novamente.", retry)
            size, chunks = 0, []
            while True:
                message = await receive()
                if message["type"] == "http.disconnect":
                    return
                if message["type"] != "http.request":
                    continue
                chunk = message.get("body", b"")
                size += len(chunk)
                if size > self.settings.max_request_bytes:
                    return await reject(413, "Corpo da requisição excede o limite permitido.")
                chunks.append(chunk)
                if not message.get("more_body", False):
                    break
            body = b"".join(chunks)
            delivered = False

            async def replay():
                nonlocal delivered
                if not delivered:
                    delivered = True
                    return {"type": "http.request", "body": body, "more_body": False}
                return await receive()

            await self.app(scope, replay, safe_send)
        finally:
            if status >= 500:
                self.policy.errors += 1
            # No URL, query, headers, user identity, request body or exception text.
            logger.info(json.dumps({"event": "http_request", "request_id": request_id,
                "category": category, "method": scope["method"], "status": status,
                "duration_ms": round((time.monotonic() - started) * 1000, 1)}))
