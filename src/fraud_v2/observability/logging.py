from __future__ import annotations

import contextvars
import logging
import logging.config
from uuid import uuid4

trace_id_var: contextvars.ContextVar[str] = contextvars.ContextVar("trace_id", default="")
REQUEST_LOG_FORMAT = (
    "%(asctime)s %(levelname)s %(name)s %(message)s %(trace_id)s "
    "%(method)s %(path)s %(status_code)s %(duration_ms)s"
)


def configure_logging() -> None:
    logging.config.dictConfig(
        {
            "version": 1,
            "disable_existing_loggers": False,
            "formatters": {
                "json": {
                    "()": "pythonjsonlogger.json.JsonFormatter",
                    "format": REQUEST_LOG_FORMAT,
                }
            },
            "handlers": {
                "default": {
                    "class": "logging.StreamHandler",
                    "formatter": "json",
                }
            },
            "loggers": {
                "fraud_v2": {
                    "handlers": ["default"],
                    "level": "INFO",
                    "propagate": False,
                }
            },
        }
    )


def new_trace_id() -> str:
    return str(uuid4())


def set_trace_id(trace_id: str) -> contextvars.Token[str]:
    return trace_id_var.set(trace_id)


def reset_trace_id(token: contextvars.Token[str]) -> None:
    trace_id_var.reset(token)


def get_trace_id() -> str:
    return trace_id_var.get()
