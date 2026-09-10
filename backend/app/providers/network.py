"""Shared provider network-layer rules (spec IMPLEMENTATION_SPEC_TR.md §9.4).

- GET retry: exponential backoff + jitter, bounded, honors `Retry-After`.
- Paid POSTs are never auto-retried here; callers that time out on a submit
  with no documented provider idempotency must raise `SubmissionUnknownError`
  (see app.providers.base) instead of calling this module's retry helper.
- `is_safe_public_url` blocks SSRF-prone destinations: private/loopback/
  link-local/reserved IPs, localhost, and non-http(s) schemes (file://, etc).
- `validate_downloaded_media` rejects HTML/JSON error bodies or undersized
  files saved as if they were valid video content.
"""

from __future__ import annotations

import ipaddress
import random
import socket
import time
from pathlib import Path
from typing import Any, Callable
from urllib.parse import urlparse

import httpx

RETRYABLE_STATUS_CODES = frozenset({429, 500, 502, 503, 504})

_BLOCKED_HOSTNAMES = frozenset({"localhost", "localhost.localdomain"})


def is_safe_public_url(url: str) -> bool:
    """True only for http(s) URLs that resolve to a public, routable address.

    Rejects file:// and other non-http(s) schemes, bare localhost, and any
    address that resolves to a private/loopback/link-local/reserved/
    multicast/unspecified IP (RFC1918, 127.0.0.0/8, 169.254.0.0/16 incl. the
    common cloud metadata IP, etc). Used before a media URL from a provider
    response is ever fetched or handed to a subprocess.
    """
    try:
        parsed = urlparse(url)
    except ValueError:
        return False

    if parsed.scheme not in ("http", "https"):
        return False

    hostname = parsed.hostname
    if not hostname:
        return False
    if hostname.lower() in _BLOCKED_HOSTNAMES:
        return False

    try:
        candidates: list[str] = [str(ipaddress.ip_address(hostname))]
    except ValueError:
        try:
            infos = socket.getaddrinfo(hostname, None)
        except socket.gaierror:
            return False
        candidates = list({info[4][0] for info in infos})
        if not candidates:
            return False

    for candidate in candidates:
        try:
            ip = ipaddress.ip_address(candidate)
        except ValueError:
            continue
        if (
            ip.is_private
            or ip.is_loopback
            or ip.is_link_local
            or ip.is_reserved
            or ip.is_multicast
            or ip.is_unspecified
        ):
            return False

    return True


def _backoff_delay(attempt: int, base_delay_s: float, max_delay_s: float) -> float:
    exp = min(max_delay_s, base_delay_s * (2**attempt))
    return random.uniform(0, exp)


def _parse_retry_after(value: str | None) -> float | None:
    if value is None:
        return None
    try:
        return max(0.0, float(value))
    except ValueError:
        return None


def get_with_retry(
    client: httpx.Client,
    url: str,
    *,
    max_retries: int = 4,
    base_delay_s: float = 0.5,
    max_delay_s: float = 20.0,
    sleep: Callable[[float], None] = time.sleep,
    **kwargs: Any,
) -> httpx.Response:
    """GET with exponential backoff + jitter on 429/5xx and transport errors.

    Honors `Retry-After` when present. Bounded by `max_retries`. This helper
    is for idempotent GET requests only — never use it for paid POST submits
    (spec §9.4/§19.2: no automatic re-POST after an unconfirmed submission).
    """
    attempt = 0
    while True:
        try:
            response = client.get(url, **kwargs)
        except httpx.TransportError:
            if attempt >= max_retries:
                raise
            sleep(_backoff_delay(attempt, base_delay_s, max_delay_s))
            attempt += 1
            continue

        if response.status_code not in RETRYABLE_STATUS_CODES or attempt >= max_retries:
            return response

        retry_after = _parse_retry_after(response.headers.get("Retry-After"))
        delay = retry_after if retry_after is not None else _backoff_delay(
            attempt, base_delay_s, max_delay_s
        )
        sleep(delay)
        attempt += 1


def download_with_retry(
    client: httpx.Client,
    url: str,
    destination: Path,
    *,
    headers: dict[str, str] | None = None,
    max_retries: int = 3,
    base_delay_s: float = 1.0,
    max_delay_s: float = 20.0,
    sleep: Callable[[float], None] = time.sleep,
) -> str | None:
    """Stream `url` to `destination` with retry on transport errors / 429/5xx.

    Writes to a `.partial` sibling first and atomically renames it into place
    only once the full body has been received (spec §7.4: no half-written
    file is ever a usable asset). Restarts the write from scratch on each
    retry — this does not attempt HTTP range resume. Returns the response's
    Content-Type header (or None) on success.
    """
    partial = destination.with_suffix(destination.suffix + ".partial")
    attempt = 0
    while True:
        try:
            with client.stream("GET", url, headers=headers) as response:
                if response.status_code in RETRYABLE_STATUS_CODES and attempt < max_retries:
                    retry_after = _parse_retry_after(response.headers.get("Retry-After"))
                    delay = (
                        retry_after
                        if retry_after is not None
                        else _backoff_delay(attempt, base_delay_s, max_delay_s)
                    )
                    sleep(delay)
                    attempt += 1
                    continue

                response.raise_for_status()
                content_type = response.headers.get("Content-Type")
                with partial.open("wb") as handle:
                    for chunk in response.iter_bytes():
                        handle.write(chunk)
                partial.replace(destination)
                return content_type
        except httpx.TransportError:
            if attempt >= max_retries:
                raise
            sleep(_backoff_delay(attempt, base_delay_s, max_delay_s))
            attempt += 1


class MediaValidationError(ValueError):
    """Raised when a downloaded media file fails MIME/size/magic-byte checks."""


def validate_downloaded_media(
    path: Path,
    *,
    content_type_header: str | None = None,
    min_size_bytes: int = 1024,
) -> None:
    """Reject HTML/JSON error pages or truncated files saved as `.mp4`.

    Checks, in order: file exists and is above `min_size_bytes`; the
    Content-Type header (when the provider sent one) is a plausible video/
    binary type; the file does not start with an HTML/JSON error body; the
    file contains the ISO base media file format `ftyp` box magic bytes.
    """
    if not path.exists():
        raise MediaValidationError(f"downloaded file is missing: {path}")

    size = path.stat().st_size
    if size < min_size_bytes:
        raise MediaValidationError(
            f"downloaded file is too small ({size} bytes < {min_size_bytes}): {path}"
        )

    if content_type_header:
        mime = content_type_header.split(";")[0].strip().lower()
        if not (mime.startswith("video/") or mime == "application/octet-stream"):
            raise MediaValidationError(
                f"unexpected content-type for a video download: {content_type_header!r}"
            )

    with path.open("rb") as handle:
        header = handle.read(64)

    stripped = header.lstrip()[:15].lower()
    if stripped.startswith(b"<!doctype") or stripped.startswith(b"<html") or stripped.startswith(
        b"{"
    ) or stripped.startswith(b"["):
        raise MediaValidationError(
            "downloaded file looks like an HTML/JSON error body, not a video"
        )

    if b"ftyp" not in header[:32]:
        raise MediaValidationError(
            "downloaded file is missing the MP4 'ftyp' box magic bytes"
        )
