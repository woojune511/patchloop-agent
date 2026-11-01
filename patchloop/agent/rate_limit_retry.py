"""Opt-in rejection retry policy, separate from successful generation accounting."""
from __future__ import annotations

import math
import re
from datetime import UTC
from email.utils import parsedate_to_datetime
from time import time

import openai

POLICY = "bounded-429-v1"
MAX_ATTEMPTS = 3
MAX_BACKOFF_SECONDS = 120.0
TEMPORARY_CODES = frozenset({"rate_limit_exceeded", "slow_down"})


def contract():
    return {
        "policy": POLICY, "sdk_retries": 0,
        "request_kinds": ["input_count", "provider_response"],
        "http_status": 429, "error_codes": sorted(TEMPORARY_CODES),
        "max_attempts": MAX_ATTEMPTS, "max_backoff_seconds": MAX_BACKOFF_SECONDS,
        "backoff": "retry-after-minimum-or-2s-exponential-plus-0.1-1s-jitter",
        "deadline": "one-caller-deadline-including-all-attempts-and-waits",
        "accounting": "same-counted-payload-and-reservation-rejected-attempts-separate",
        "recovery": "no-automatic-resume-of-unmatched-logical-dispatch",
    }


def temporary_rejection(exc):
    """No free-form message or unknown error code becomes retry authority."""
    if not isinstance(exc, openai.RateLimitError) or exc.status_code != 429:
        return None
    code = getattr(exc, "code", None)
    if not isinstance(code, str) or code not in TEMPORARY_CODES:
        return None
    request_id = exc.response.headers.get("x-request-id", "")
    return {
        "http_status": 429, "error_code": code,
        "request_id": request_id if re.fullmatch(r"[A-Za-z0-9_-]{1,128}", request_id) else None,
        "usage_receipt": False,
    }


def retry_after_seconds(headers, *, now=None):
    """Honor valid seconds or HTTP-date hints; never truncate a long server delay."""
    value = headers.get("retry-after")
    if not isinstance(value, str) or not value.strip():
        return None
    try:
        seconds = float(value)
    except ValueError:
        try:
            date = parsedate_to_datetime(value)
            if date.tzinfo is None:
                date = date.replace(tzinfo=UTC)
            seconds = max(0.0, date.timestamp() - (time() if now is None else now))
        except (ValueError, TypeError, OverflowError):
            return None
    return seconds if math.isfinite(seconds) and seconds >= 0 else None
