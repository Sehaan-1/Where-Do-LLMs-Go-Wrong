"""Minimal structured observability for offline CLI runs."""

from __future__ import annotations

import json
import sys
from datetime import UTC, datetime
from uuid import uuid4


def new_run_id() -> str:
    """Create a per-invocation correlation ID without storing user data."""
    return uuid4().hex[:16]


def emit_event(
    run_id: str,
    command: str,
    event: str,
    details: dict[str, object] | None = None,
) -> None:
    """Write one structured event to stderr; never include prompts or traces."""
    timestamp = datetime.now(UTC).isoformat(timespec="milliseconds").replace("+00:00", "Z")
    entry = {
        "timestamp_utc": timestamp,
        "level": "INFO",
        "event": event,
        "run_id": run_id,
        "command": command,
        "details": details or {},
    }
    sys.stderr.write(json.dumps(entry, ensure_ascii=False, separators=(",", ":")) + "\n")
