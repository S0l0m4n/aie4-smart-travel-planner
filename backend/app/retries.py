"""Async retry policies built on tenacity.

Engineering standard: every external call (LLM, embedding, DB) is wrapped
with a timeout + bounded retry. Auth errors / 4xx are not retried — those
are deterministic and would just burn the retry budget.
"""
from __future__ import annotations

import httpx
from tenacity import (
    AsyncRetrying,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

_TRANSIENT = (
    httpx.TimeoutException,
    httpx.ConnectError,
    httpx.RemoteProtocolError,
    ConnectionError,
)


def llm_retry(*, attempts: int = 3, max_wait: float = 8.0) -> AsyncRetrying:
    """Retry policy for LLM calls. Use as:
    ``async for attempt in llm_retry(): with attempt: await ...``
    """
    return AsyncRetrying(
        stop=stop_after_attempt(attempts),
        wait=wait_exponential(multiplier=0.5, max=max_wait),
        retry=retry_if_exception_type(_TRANSIENT),
        reraise=True,
    )