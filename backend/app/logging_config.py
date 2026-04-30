"""Structured logging via structlog. JSON in production, key/value locally."""
from __future__ import annotations

import logging
import sys

import structlog


def configure_logging(level: str = "INFO", json_output: bool = True) -> None:
    """Wire stdlib logging + structlog. Call once at startup.

    Args:
        level: Standard logging level name (e.g. "INFO", "DEBUG"). Falls
            back to INFO if unrecognized.
        json_output: When True, emit JSON-formatted log lines suitable for
            ingestion by aggregators. When False, emit colorized
            human-readable lines for local development.
    """
    log_level = getattr(logging, level.upper(), logging.INFO)

    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=log_level,
        force=True,
    )

    # Processors run in order on every log call. `merge_contextvars` is
    # what makes request-scoped fields (e.g. trace ids bound by
    # middleware) automatically appear on every log line in that scope.
    shared_processors: list = [
        structlog.contextvars.merge_contextvars,
        structlog.processors.add_log_level,
        structlog.processors.TimeStamper(fmt="iso", utc=True),
        structlog.processors.StackInfoRenderer(),
    ]

    # Final rendering:
    #   - Choose json_output for production
    #   - Otherwise coloured messages for local development
    if json_output:
        renderer = structlog.processors.JSONRenderer()
    else:
        renderer = structlog.dev.ConsoleRenderer(colors=True)

    structlog.configure(
        processors=[*shared_processors,
                    structlog.processors.format_exc_info,
                    renderer],

        # `make_filtering_bound_logger` short-circuits below `log_level`
        # so the processor chain isn't even invoked for filtered messages.
        wrapper_class=structlog.make_filtering_bound_logger(log_level),
        logger_factory=structlog.PrintLoggerFactory(),
        cache_logger_on_first_use=True,
    )


def get_logger(name: str | None = None) -> structlog.stdlib.BoundLogger:
    """Return a structlog logger, optionally bound to a module name.

    Args:
        name: Logger name, typically `__name__` from the calling module.

    Returns:
        A bound structlog logger that respects the configuration applied
        by `configure_logging`.
    """
    return structlog.get_logger(name)
