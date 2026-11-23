"""Local-first authentication, durable runtime state and lightweight observability.

The internal showcase intentionally has no paid infrastructure dependency.  This
module keeps mutable sessions/jobs outside the immutable evidence database so a
session write cannot invalidate a verified evidence snapshot.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import logging
import os
import secrets
import sqlite3
import time
from collections import defaultdict, deque
from dataclasses import dataclass
from pathlib import Path
from threading import Lock
from typing import Any

from pydantic import SecretStr
from starlette.responses import JSONResponse
from starlette.types import ASGIApp, Message, Receive, Scope, Send

from backend.app.settings import Settings

LOG = logging.getLogger("himaroad.http")
COOKIE = "himaroad_access"


class JsonFormatter(logging.Formatter):
    """One-line logs suitable for files, journald or a future log collector."""

    def format(self, record: logging.LogRecord) -> str:
        item: dict[str, Any] = {
            "timestamp": time.strftime(
                "%Y-%m-%dT%H:%M:%SZ", time.gmtime(record.created)
            ),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        fields = getattr(record, "fields", None)
        if isinstance(fields, dict):
            item.update(fields)
        if record.exc_info:
            item["exception"] = self.formatException(record.exc_info)
        return json.dumps(item, separators=(",", ":"), ensure_ascii=False)


def configure_logging() -> None:
    root = logging.getLogger()
    if any(getattr(handler, "_himaroad_json", False) for handler in root.handlers):
        return
    handler = logging.StreamHandler()
    handler.setFormatter(JsonFormatter())
    handler._himaroad_json = True  # type: ignore[attr-defined]
    root.addHandler(handler)
    root.setLevel(logging.WARNING)
    logging.getLogger("himaroad").setLevel(
        os.environ.get("HIMAROAD_LOG_LEVEL", "INFO").upper()
    )


def _b64(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).decode().rstrip("=")


def _unb64(value: str) -> bytes:
    return base64.urlsafe_b64decode(value + "=" * (-len(value) % 4))


def hash_password(password: str, *, salt: bytes | None = None) -> str:
    """Return a self-describing scrypt hash; plaintext is never stored."""

    if not 12 <= len(password) <= 256:
        raise ValueError("Password must contain 12 to 256 characters")
    salt = salt or secrets.token_bytes(16)
    digest = hashlib.scrypt(
        password.encode(), salt=salt, n=2**15, r=8, p=1, dklen=32, maxmem=64 * 1024**2
    )
    return f"scrypt$32768$8$1${_b64(salt)}${_b64(digest)}"


def verify_password(password: str, encoded: str) -> bool:
    try:
        algorithm, n, r, p, salt, expected = encoded.split("$")
        if algorithm != "scrypt":
            return False
        digest = hashlib.scrypt(
            password.encode(),
            salt=_unb64(salt),
            n=int(n),
            r=int(r),
            p=int(p),
            dklen=32,
            maxmem=64 * 1024**2,
        )
        return hmac.compare_digest(digest, _unb64(expected))
    except (ValueError, TypeError):
        return False


def _secret(value: SecretStr | None) -> str | None:
    return value.get_secret_value() if value is not None else None


@dataclass(frozen=True)
class Identity:
    username: str
    role: str


class Metrics:
    def __init__(self) -> None:
        self.lock = Lock()
        self.started = time.time()
        self.requests = defaultdict(int)
        self.seconds = defaultdict(float)
        self.in_flight = 0

    def begin(self) -> None:
        with self.lock:
            self.in_flight += 1

    def end(self, method: str, status: int, seconds: float) -> None:
        family = f"{method}:{status // 100}xx"
        with self.lock:
            self.in_flight = max(0, self.in_flight - 1)
            self.requests[family] += 1
            self.seconds[family] += seconds

    def render(self) -> bytes:
        with self.lock:
            lines = [
                "# HELP himaroad_uptime_seconds Process uptime.",
                "# TYPE himaroad_uptime_seconds gauge",
                f"himaroad_uptime_seconds {max(0, time.time() - self.started):.3f}",
                "# HELP himaroad_http_in_flight Current HTTP requests.",
                "# TYPE himaroad_http_in_flight gauge",
                f"himaroad_http_in_flight {self.in_flight}",
                "# HELP himaroad_http_requests_total HTTP requests by method and status family.",
                "# TYPE himaroad_http_requests_total counter",
            ]
            for family in sorted(self.requests):
                method, status = family.split(":")
                lines.append(
                    f'himaroad_http_requests_total{{method="{method}",status="{status}"}} '
                    f"{self.requests[family]}"
                )
            return ("\n".join(lines) + "\n").encode()


METRICS = Metrics()


class SlidingWindowLimiter:
    def __init__(self, limit: int) -> None:
        self.limit = limit
        self.events: dict[str, deque[float]] = {}
        self.lock = Lock()

    def admit(self, key: str, now: float) -> bool:
        with self.lock:
            queue = self.events.setdefault(key, deque())
            while queue and queue[0] <= now - 60:
                queue.popleft()
            if len(queue) >= self.limit:
                return False
            queue.append(now)
            if len(self.events) > 2048:
                self.events = {
                    k: q for k, q in self.events.items() if q and q[-1] > now - 60
                }
            return True


class RuntimeStore:
    """Small durable SQLite store for capabilities and the local analysis queue."""

    def __init__(self, path: Path, *, max_jobs: int = 16, stale_seconds: int = 7200):
        self.path = path.resolve()
        self.max_jobs = max_jobs
        self.stale_seconds = stale_seconds
        self.path.parent.mkdir(parents=True, exist_ok=True)
        if self.path.is_symlink():
            raise ValueError("runtime database must not be a symlink")
        self._initialize()

    def connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.path, timeout=5)
        connection.execute("PRAGMA busy_timeout=5000")
        connection.execute("PRAGMA foreign_keys=ON")
        return connection

    def _initialize(self) -> None:
        with self.connect() as connection:
            connection.execute("PRAGMA journal_mode=WAL")
            connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS sessions (
                    digest TEXT PRIMARY KEY, evidence_id TEXT NOT NULL,
                    expires_at REAL NOT NULL, created_at REAL NOT NULL
                );
                CREATE INDEX IF NOT EXISTS sessions_expiry ON sessions(expires_at);
                CREATE TABLE IF NOT EXISTS jobs (
                    id TEXT PRIMARY KEY, kind TEXT NOT NULL, state TEXT NOT NULL,
                    payload TEXT NOT NULL, result TEXT, error_code TEXT,
                    created_at REAL NOT NULL, updated_at REAL NOT NULL,
                    started_at REAL, finished_at REAL
                );
                CREATE INDEX IF NOT EXISTS jobs_state_created ON jobs(state, created_at);
                """
            )

    def health(self) -> dict[str, int | str]:
        with self.connect() as connection:
            connection.execute("SELECT 1").fetchone()
            sessions = connection.execute(
                "SELECT count(*) FROM sessions WHERE expires_at>?", (time.time(),)
            ).fetchone()[0]
            queued = connection.execute(
                "SELECT count(*) FROM jobs WHERE state='queued'"
            ).fetchone()[0]
            running = connection.execute(
                "SELECT count(*) FROM jobs WHERE state='running'"
            ).fetchone()[0]
        return {
            "status": "ok",
            "active_sessions": sessions,
            "queued_jobs": queued,
            "running_jobs": running,
        }

    def create_session(
        self, digest: str, evidence_id: str, seconds: int, limit: int
    ) -> None:
        now = time.time()
        with self.connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            connection.execute("DELETE FROM sessions WHERE expires_at<=?", (now,))
            count = connection.execute("SELECT count(*) FROM sessions").fetchone()[0]
            if count >= limit:
                raise RuntimeError("session_limit")
            connection.execute(
                "INSERT INTO sessions VALUES (?, ?, ?, ?)",
                (digest, evidence_id, now + seconds, now),
            )

    def session(self, digest: str) -> str | None:
        now = time.time()
        with self.connect() as connection:
            row = connection.execute(
                "SELECT evidence_id, expires_at FROM sessions WHERE digest=?", (digest,)
            ).fetchone()
            if row is None:
                return None
            if row[1] <= now:
                connection.execute("DELETE FROM sessions WHERE digest=?", (digest,))
                return None
            return str(row[0])

    def delete_session(self, digest: str) -> None:
        with self.connect() as connection:
            connection.execute("DELETE FROM sessions WHERE digest=?", (digest,))

    def enqueue(self, kind: str, payload: dict[str, Any]) -> str:
        encoded = json.dumps(
            payload, sort_keys=True, separators=(",", ":"), allow_nan=False
        )
        if len(encoded.encode()) > 32 * 1024:
            raise ValueError("job payload too large")
        now = time.time()
        identifier = secrets.token_hex(16)
        with self.connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            count = connection.execute(
                "SELECT count(*) FROM jobs WHERE state IN ('queued','running')"
            ).fetchone()[0]
            if count >= self.max_jobs:
                raise RuntimeError("job_queue_full")
            connection.execute(
                "INSERT INTO jobs(id,kind,state,payload,created_at,updated_at) VALUES(?,?,'queued',?,?,?)",
                (identifier, kind, encoded, now, now),
            )
        return identifier

    def recover_stale(self) -> int:
        cutoff = time.time() - self.stale_seconds
        with self.connect() as connection:
            cursor = connection.execute(
                "UPDATE jobs SET state='failed', error_code='worker_interrupted', "
                "finished_at=?, updated_at=? WHERE state='running' AND updated_at<?",
                (time.time(), time.time(), cutoff),
            )
            return cursor.rowcount

    def claim(self, kind: str = "analysis") -> tuple[str, dict[str, Any]] | None:
        now = time.time()
        with self.connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            row = connection.execute(
                "SELECT id,payload FROM jobs WHERE state='queued' AND kind=? ORDER BY created_at LIMIT 1",
                (kind,),
            ).fetchone()
            if row is None:
                return None
            changed = connection.execute(
                "UPDATE jobs SET state='running',started_at=?,updated_at=? WHERE id=? AND state='queued'",
                (now, now, row[0]),
            ).rowcount
            if changed != 1:
                return None
        return str(row[0]), json.loads(row[1])

    def finish(
        self, identifier: str, *, result: str | None = None, error: str | None = None
    ) -> None:
        now = time.time()
        state = "failed" if error else "complete"
        with self.connect() as connection:
            changed = connection.execute(
                "UPDATE jobs SET state=?,result=?,error_code=?,updated_at=?,finished_at=? "
                "WHERE id=? AND state='running'",
                (state, result, error, now, now, identifier),
            ).rowcount
            if changed != 1:
                raise ValueError("job is not running")

    def job(self, identifier: str) -> dict[str, Any] | None:
        with self.connect() as connection:
            row = connection.execute(
                "SELECT id,kind,state,result,error_code,created_at,updated_at,started_at,finished_at "
                "FROM jobs WHERE id=?",
                (identifier,),
            ).fetchone()
        if row is None:
            return None
        keys = (
            "id",
            "kind",
            "state",
            "result",
            "error_code",
            "created_at",
            "updated_at",
            "started_at",
            "finished_at",
        )
        return dict(zip(keys, row))

    def recent_jobs(self, limit: int = 20) -> list[dict[str, Any]]:
        with self.connect() as connection:
            rows = connection.execute(
                "SELECT id,kind,state,result,error_code,created_at,updated_at,started_at,finished_at "
                "FROM jobs ORDER BY created_at DESC LIMIT ?",
                (min(max(limit, 1), 100),),
            ).fetchall()
        keys = (
            "id",
            "kind",
            "state",
            "result",
            "error_code",
            "created_at",
            "updated_at",
            "started_at",
            "finished_at",
        )
        return [dict(zip(keys, row)) for row in rows]


def runtime_store(config: Settings) -> RuntimeStore:
    return RuntimeStore(
        config.data_root / "runtime.sqlite3",
        max_jobs=config.max_queued_jobs,
        stale_seconds=config.job_stale_seconds,
    )


class OperationsMiddleware:
    """Loopback boundary, optional local accounts, rate limits and security headers."""

    def __init__(self, app: ASGIApp, config: Settings):
        self.app = app
        self.config = config
        self.limiter = SlidingWindowLimiter(config.rate_limit_per_minute)
        self.users: dict[str, tuple[str, str]] = {}
        if config.local_auth_admin_username and config.local_auth_admin_password_hash:
            self.users[config.local_auth_admin_username] = (
                _secret(config.local_auth_admin_password_hash) or "",
                "admin",
            )
        if config.local_auth_viewer_username and config.local_auth_viewer_password_hash:
            self.users[config.local_auth_viewer_username] = (
                _secret(config.local_auth_viewer_password_hash) or "",
                "viewer",
            )
        self.cookie_secret = (_secret(config.local_auth_cookie_secret) or "").encode()
        self.service_token = _secret(config.local_service_token)

    @property
    def enabled(self) -> bool:
        return bool(self.users)

    def signed_cookie(self, identity: Identity, now: float) -> str:
        payload = f"{identity.username}|{identity.role}|{int(now + 8 * 3600)}".encode()
        body = _b64(payload)
        signature = hmac.new(
            self.cookie_secret, body.encode(), hashlib.sha256
        ).hexdigest()
        return body + "." + signature

    def cookie_identity(self, value: str, now: float) -> Identity | None:
        try:
            body, signature = value.split(".", 1)
            expected = hmac.new(
                self.cookie_secret, body.encode(), hashlib.sha256
            ).hexdigest()
            if not hmac.compare_digest(signature, expected):
                return None
            username, role, expiry = _unb64(body).decode().split("|", 2)
            if int(expiry) <= now or self.users.get(username, (None, None))[1] != role:
                return None
            return Identity(username, role)
        except (ValueError, UnicodeDecodeError):
            return None

    def authenticate(self, scope: Scope, now: float) -> tuple[Identity | None, bool]:
        headers = {k.lower(): v for k, v in scope.get("headers", [])}
        service = headers.get(b"x-himaroad-service-token", b"").decode(errors="ignore")
        if self.service_token and hmac.compare_digest(service, self.service_token):
            return Identity("local-service", "admin"), False
        cookie = headers.get(b"cookie", b"").decode(errors="ignore")
        for part in cookie.split(";"):
            name, _, value = part.strip().partition("=")
            if name == COOKIE and (identity := self.cookie_identity(value, now)):
                return identity, False
        authorization = headers.get(b"authorization", b"")
        if authorization.startswith(b"Basic ") and len(authorization) <= 1024:
            try:
                username, password = (
                    base64.b64decode(authorization[6:], validate=True)
                    .decode()
                    .split(":", 1)
                )
            except (ValueError, UnicodeDecodeError):
                return None, False
            saved = self.users.get(username)
            if saved and verify_password(password, saved[0]):
                return Identity(username, saved[1]), True
        return None, False

    @staticmethod
    def client_is_loopback(scope: Scope) -> bool:
        host = (scope.get("client") or ("", 0))[0]
        return host in {"127.0.0.1", "::1", "localhost", "testclient"}

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        now = time.time()
        path = scope.get("path", "")
        public = path in {"/health", "/ready"}
        identity: Identity | None = None
        issue_cookie = False
        if self.enabled and not public:
            identity, issue_cookie = self.authenticate(scope, now)
            if identity is None:
                await JSONResponse(
                    {"detail": "local_authentication_required"},
                    status_code=401,
                    headers={"WWW-Authenticate": 'Basic realm="HimaRoad internal"'},
                )(scope, receive, send)
                return
        elif not self.enabled and not self.client_is_loopback(scope):
            await JSONResponse({"detail": "loopback_only"}, status_code=403)(
                scope, receive, send
            )
            return
        key = (
            identity.username if identity else (scope.get("client") or ("local", 0))[0]
        )
        if not self.limiter.admit(key, now):
            await JSONResponse(
                {"detail": "rate_limit"}, status_code=429, headers={"Retry-After": "60"}
            )(scope, receive, send)
            return
        scope.setdefault("state", {})["identity"] = identity
        started = time.monotonic()
        status = 500
        METRICS.begin()

        async def secured_send(message: Message) -> None:
            nonlocal status
            if message["type"] == "http.response.start":
                status = int(message["status"])
                headers = list(message.get("headers", []))
                headers.extend(
                    [
                        (b"x-content-type-options", b"nosniff"),
                        (b"x-frame-options", b"DENY"),
                        (b"referrer-policy", b"no-referrer"),
                        (
                            b"permissions-policy",
                            b"geolocation=(),camera=(),microphone=()",
                        ),
                        (
                            b"content-security-policy",
                            (
                                b"default-src 'self'; img-src 'self' data: blob:; "
                                b"style-src 'self' 'unsafe-inline'; script-src 'self'; "
                                b"connect-src 'self'; frame-src blob:; object-src 'none'; "
                                b"base-uri 'self'; frame-ancestors 'none'"
                            ),
                        ),
                    ]
                )
                if issue_cookie and identity:
                    cookie = self.signed_cookie(identity, now)
                    headers.append(
                        (
                            b"set-cookie",
                            f"{COOKIE}={cookie}; Path=/; HttpOnly; SameSite=Strict; Max-Age=28800".encode(),
                        )
                    )
                message["headers"] = headers
            await send(message)

        try:
            await self.app(scope, receive, secured_send)
        finally:
            duration = time.monotonic() - started
            METRICS.end(scope.get("method", "?"), status, duration)
            LOG.info(
                "request",
                extra={
                    "fields": {
                        "method": scope.get("method"),
                        "path": path,
                        "status": status,
                        "duration_ms": round(duration * 1000, 2),
                        "role": identity.role if identity else "loopback",
                    }
                },
            )
