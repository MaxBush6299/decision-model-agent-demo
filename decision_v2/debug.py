"""Opt-in sanitized debug trace.

Disabled by default so stdout and recorded output are unchanged. When enabled
(``--debug`` or ``DECISION_DEBUG=1``) one JSON object per event is written to
stderr, or to ``DECISION_DEBUG_FILE`` when set. Events carry summaries only:
no tokens, endpoints, identity claims or full message bodies.
"""
import json
import os
import sys
from time import monotonic

from .contracts import DemoError
from .diagnostics import sanitize

MAX_TEXT = 200
MAX_ITEMS = 12
MAX_DEPTH = 4

_sink = None
_started = monotonic()


class DebugSink:
    def __init__(self, stream, owned=False):
        self.stream, self.owned = stream, owned

    def write(self, line: str):
        try:
            self.stream.write(line + "\n")
            self.stream.flush()
        except (OSError, ValueError) as exc:
            raise DemoError("Debug trace sink failed; disable --debug or fix DECISION_DEBUG_FILE.") from exc


def enabled() -> bool:
    return _sink is not None


def enable(stream=None, owned=False):
    global _sink, _started
    _started = monotonic()
    _sink = DebugSink(stream if stream is not None else sys.stderr, owned)
    return _sink


def configure(flag: bool = False, environ=None):
    """Turn tracing on from the flag or DECISION_DEBUG=1; return True when enabled."""
    env = os.environ if environ is None else environ
    if not (flag or env.get("DECISION_DEBUG") == "1"):
        disable()
        return False
    path = env.get("DECISION_DEBUG_FILE")
    if path:
        try:
            enable(open(path, "a", encoding="utf-8"), owned=True)
        except OSError as exc:
            raise DemoError("Debug trace file cannot be opened.") from exc
    else:
        enable()
    return True


def disable():
    global _sink
    sink, _sink = _sink, None
    if sink is not None and sink.owned:
        try:
            sink.stream.close()
        except OSError:
            pass


def summarize(value, depth: int = 0):
    """Bounded structural summary: numbers and short strings only, never whole bodies."""
    if isinstance(value, dict):
        if depth >= MAX_DEPTH:
            return f"<dict {len(value)}>"
        return {str(k): summarize(v, depth + 1) for k, v in list(value.items())[:MAX_ITEMS]}
    if isinstance(value, (list, tuple)):
        if depth >= MAX_DEPTH:
            return f"<list {len(value)}>"
        return [summarize(v, depth + 1) for v in value[:MAX_ITEMS]]
    if isinstance(value, str):
        text = sanitize(value)
        return text if len(text) <= MAX_TEXT else text[:MAX_TEXT] + f"...<{len(text)} chars>"
    return value


def emit(event: str, **fields):
    if _sink is None:
        return
    record = {"t": round(monotonic() - _started, 3), "event": event}
    record.update({key: summarize(sanitize(value) if isinstance(value, (dict, list, tuple)) else value)
                   for key, value in fields.items()})
    _sink.write(json.dumps(record, default=str, sort_keys=False))


def usage_of(payload) -> dict | None:
    usage = payload.get("usage") if isinstance(payload, dict) else None
    if not isinstance(usage, dict):
        return None
    return {key: value for key, value in usage.items()
            if isinstance(value, int) and not isinstance(value, bool)} or None
