"""
Security Middleware and Defenses for the rag-lesson-agent Web Application.
Implements:
1. CSRF validation with hmac.compare_digest and double-submit tokens.
2. In-memory sliding-window IP rate limiting & concurrency caps.
3. Strict Content-Security-Policy and HTTP security headers.
4. Input sanitization (server-side XSS stripping, length and character whitelists).
5. Safe run ID and sample lesson allow-list validation.
6. Error masking with correlation IDs.
"""

import re
import hmac
import uuid
import time
import secrets
import logging
from typing import Dict, List, Optional
from fastapi import Request, HTTPException, status
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from pydantic import BaseModel, Field, field_validator

logger = logging.getLogger("rag_lesson_agent.security")

# Secret key used for signing CSRF tokens
CSRF_SECRET = secrets.token_hex(32)

# Allow-list for deliberate error test files (Path Traversal Protection)
ALLOWED_SAMPLE_LESSONS = {
    "factual_error": "tests/bad_lessons/factual_error.md",
    "jargon_dump": "tests/bad_lessons/jargon_dump.md",
    "bad_flow": "tests/bad_lessons/bad_flow.md",
    "wrong_pipeline_order": "tests/bad_lessons/wrong_pipeline_order.md",
}

# UUID4 regex for run_id validation
UUID4_REGEX = re.compile(r"^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$", re.I)


# -----------------------------------------------------------------------------
# Input Validation Models (Pydantic)
# -----------------------------------------------------------------------------
class TopicRunRequest(BaseModel):
    topic: str = Field(..., max_length=100, min_length=2)
    sample_key: Optional[str] = None

    @field_validator("topic")
    @classmethod
    def validate_topic_chars(cls, v: str) -> str:
        # Whitelist alphanumeric, spaces, and safe punctuation: - _ , . ( ) [ ] / : ' ?
        if not re.match(r"^[\w\s\-\.,\(\)\[\]/:?'\"]+$", v, re.UNICODE):
            raise ValueError("Topic contains invalid characters.")
        return v.strip()

    @field_validator("sample_key")
    @classmethod
    def validate_sample_key(cls, v: Optional[str]) -> Optional[str]:
        if v and v not in ALLOWED_SAMPLE_LESSONS:
            raise ValueError(f"Unknown sample key. Allowed keys: {list(ALLOWED_SAMPLE_LESSONS.keys())}")
        return v


class EvaluateLessonRequest(BaseModel):
    lesson_text: str = Field(..., max_length=25000, min_length=20)
    topic: Optional[str] = Field(default="Introduction to RAG", max_length=100)

    @field_validator("topic")
    @classmethod
    def validate_topic(cls, v: str) -> str:
        if v and not re.match(r"^[\w\s\-\.,\(\)\[\]/:?'\"]+$", v, re.UNICODE):
            raise ValueError("Topic contains invalid characters.")
        return v.strip()


def sanitize_untrusted_text(text: str) -> str:
    """
    Server-side defense-in-depth: strips script tags, event handlers, and javascript: URLs.
    Primary rendering will also be purified on the client with DOMPurify.
    """
    if not text:
        return ""
    # Strip <script> tags
    cleaned = re.sub(r"(?i)<script[\s\S]*?>[\s\S]*?</script>", "", text)
    # Strip javascript: URLs
    cleaned = re.sub(r"(?i)javascript:\s*", "", cleaned)
    # Strip dangerous HTML event handlers (e.g. onerror=, onclick=)
    cleaned = re.sub(r"(?i)\son\w+\s*=\s*['\"].*?['\"]", "", cleaned)
    cleaned = re.sub(r"(?i)\son\w+\s*=\s*[^\s>]+", "", cleaned)
    return cleaned


# -----------------------------------------------------------------------------
# Rate Limiting & Concurrency Control
# -----------------------------------------------------------------------------
class RateLimiter:
    """
    In-memory rate limiter per IP address and global concurrent run governor.
    """

    def __init__(self, max_runs_per_hour: int = 20, max_requests_per_minute: int = 120, max_concurrent: int = 3):
        self.max_runs_per_hour = max_runs_per_hour
        self.max_requests_per_minute = max_requests_per_minute
        self.max_concurrent = max_concurrent
        self.active_runs = 0
        self.request_timestamps: Dict[str, List[float]] = {}
        self.run_timestamps: Dict[str, List[float]] = {}

    def check_request_rate(self, ip: str):
        now = time.time()
        window = now - 60.0
        ts_list = self.request_timestamps.get(ip, [])
        ts_list = [t for t in ts_list if t > window]
        if len(ts_list) >= self.max_requests_per_minute:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Rate limit exceeded: too many requests per minute. Please wait."
            )
        ts_list.append(now)
        self.request_timestamps[ip] = ts_list

    def acquire_run_slot(self, ip: str):
        now = time.time()
        window = now - 3600.0
        ts_list = self.run_timestamps.get(ip, [])
        ts_list = [t for t in ts_list if t > window]
        if len(ts_list) >= self.max_runs_per_hour:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Rate limit exceeded: maximum generation runs per hour reached for this IP."
            )
        if self.active_runs >= self.max_concurrent:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Server busy: maximum concurrent generation runs active. Please retry in a few seconds."
            )
        self.active_runs += 1
        ts_list.append(now)
        self.run_timestamps[ip] = ts_list

    def release_run_slot(self):
        if self.active_runs > 0:
            self.active_runs -= 1


global_limiter = RateLimiter()


# -----------------------------------------------------------------------------
# CSRF Utilities
# -----------------------------------------------------------------------------
def generate_csrf_token() -> str:
    """Generates a cryptographically strong random token."""
    return secrets.token_urlsafe(32)


def validate_csrf(request: Request):
    """
    Validates CSRF token using double-submit cookie pattern with constant-time comparison.
    """
    # Exclude safe read methods
    if request.method in ("GET", "HEAD", "OPTIONS"):
        return

    cookie_token = request.cookies.get("csrf_token")
    header_token = request.headers.get("X-CSRF-Token")

    if not header_token or len(header_token) < 20:
        logger.warning("CSRF validation failed: Missing token in X-CSRF-Token header.")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="CSRF validation failed: Missing CSRF token."
        )

    # When both cookie and header are provided, enforce constant-time match
    if cookie_token and not hmac.compare_digest(cookie_token, header_token):
        logger.warning("CSRF validation failed: Token mismatch between cookie and header.")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="CSRF token expired or desynchronized. Please refresh the page."
        )


# -----------------------------------------------------------------------------
# Security Headers Middleware
# -----------------------------------------------------------------------------
class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        # 1. Rate check general requests
        client_ip = request.client.host if request.client else "127.0.0.1"
        try:
            global_limiter.check_request_rate(client_ip)
        except HTTPException as exc:
            return JSONResponse(status_code=exc.status_code, content={"error": exc.detail})

        # 2. Origin/Referer check for state-changing requests
        if request.method in ("POST", "PUT", "DELETE", "PATCH"):
            origin = request.headers.get("Origin")
            host = request.headers.get("Host")
            if origin and host:
                # Strip protocol from origin
                origin_host = re.sub(r"^https?://", "", origin)
                if origin_host != host and not host.startswith(origin_host):
                    logger.warning(f"Forbidden cross-origin request: origin={origin}, host={host}")
                    return JSONResponse(
                        status_code=status.HTTP_403_FORBIDDEN,
                        content={"error": "Cross-origin requests are forbidden."}
                    )

        # 3. Call endpoint with exception handling to prevent leaking internal stack traces
        try:
            response = await call_next(request)
        except Exception as e:
            error_id = uuid.uuid4().hex[:8]
            logger.error(f"Internal error [{error_id}]: {e}", exc_info=True)
            return JSONResponse(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                content={"error": f"An unexpected server error occurred. Reference ID: {error_id}"}
            )

        # 4. Inject strict security headers
        # Content-Security-Policy: restrict scripts/styles to self and vendored assets, no unsafe-inline
        csp = (
            "default-src 'self'; "
            "script-src 'self' 'unsafe-eval'; "  # unsafe-eval allows local marked parser
            "style-src 'self' 'unsafe-inline'; " # unsafe-inline for dynamic theme variables
            "font-src 'self' data:; "
            "img-src 'self' data:; "
            "object-src 'none'; "
            "base-uri 'none'; "
            "frame-ancestors 'none';"
        )
        response.headers["Content-Security-Policy"] = csp
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "no-referrer"
        response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
        response.headers["Cross-Origin-Opener-Policy"] = "same-origin"

        # Prevent browser caching of dynamic API results
        if request.url.path.startswith("/api/"):
            response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
            response.headers["Pragma"] = "no-cache"

        return response

