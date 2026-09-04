"""Structured JSON logging — never emit PHI values. Only field names/event types."""

from __future__ import annotations

import json
import logging
import sys
import time
import uuid
from contextvars import ContextVar
from typing import Any

# Request-scoped context (X-Request-Id propagated to Celery tasks)
request_id_var: ContextVar[str | None] = ContextVar("request_id", default=None)
family_id_var: ContextVar[str | None] = ContextVar("family_id", default=None)

# Fields that must never appear as values in logs (AGENTS rule #7)
PHI_FIELD_NAMES = frozenset(
    {
        "password",
        "password_hash",
        "otp_code_hash",
        "refresh_token_hash",
        "access_token",
        "refresh_token",
        "disease_history",
        "medication",
        "test_report",
        "bmi",
        "conditions",
        "allergies",
        "medications",
        "notes",
        "phi",
    }
)


class AarogyaJsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "ts": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(record.created)),
            "level": record.levelname.lower(),
            "logger": record.name,
            "msg": record.getMessage(),
            "request_id": request_id_var.get(),
            "family_id": family_id_var.get(),
        }
        # Include structured extras without leaking PHI values
        for k, v in record.__dict__.items():
            if k in ("msg", "args", "levelname", "levelno", "name", "created", "msecs", "exc_info", "exc_text", "stack_info", "pathname", "lineno", "funcName", "module", "thread", "threadName", "process", "message"):
                continue
            if k.lower() in PHI_FIELD_NAMES:
                continue
            if k.startswith("_"):
                continue
            try:
                json.dumps(v)
                payload[k] = v
            except Exception:
                payload[k] = str(v)[:500]
        if record.exc_info and record.exc_info[0] is not None:
            payload["exc_type"] = record.exc_info[0].__name__
        return json.dumps(payload, ensure_ascii=False, separators=(",", ":"))


def configure_logging(level: str = "INFO") -> None:
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(AarogyaJsonFormatter())
    root = logging.getLogger()
    # keep uvicorn access logs but route through same handler
    for name in ("uvicorn", "uvicorn.error", "uvicorn.access", "aarogya", "app"):
        lg = logging.getLogger(name)
        lg.handlers.clear()
        lg.addHandler(handler)
        lg.setLevel(getattr(logging, level.upper(), logging.INFO))
        lg.propagate = False
    root.setLevel(getattr(logging, level.upper(), logging.INFO))
    # silence noisy libs
    logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)


def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(name)


def set_request_context(request_id: str | None = None, family_id: str | None = None) -> str:
    rid = request_id or uuid.uuid4().hex[:16]
    request_id_var.set(rid)
    if family_id is not None:
        family_id_var.set(family_id)
    return rid
