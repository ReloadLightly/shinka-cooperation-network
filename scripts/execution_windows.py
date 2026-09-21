"""Shared cooperative admission windows; None explicitly means unbounded."""
from __future__ import annotations

import math
import os
import time

ENVIRONMENT_KEY = "SHINKA_EXECUTION_DEADLINE"


def resolve_deadline(hours=None, *, inherited=None, now=None):
    """Return an optional Unix deadline without assigning scientific fitness.

    The caller decides whether an inherited deadline belongs to this invocation.
    In particular, the native launcher deliberately discards stale session state.
    """
    deadlines = []
    if hours is not None:
        if isinstance(hours, bool) or not isinstance(hours, (int, float)) or not math.isfinite(hours) or hours <= 0:
            raise ValueError("--window-hours must be finite and positive, or omitted")
        deadlines.append((time.time() if now is None else now) + hours * 3600)
    if inherited not in (None, ""):
        try:
            value = float(inherited)
        except (TypeError, ValueError) as exc:
            raise ValueError("Inherited execution deadline must be finite positive Unix seconds") from exc
        if isinstance(inherited, bool) or not math.isfinite(value) or value <= 0:
            raise ValueError("Inherited execution deadline must be finite positive Unix seconds")
        deadlines.append(value)
    return min(deadlines) if deadlines else None


def set_deadline(deadline):
    if deadline is None:
        os.environ.pop(ENVIRONMENT_KEY, None)
    else:
        os.environ[ENVIRONMENT_KEY] = str(deadline)
