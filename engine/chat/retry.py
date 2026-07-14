"""Action-aware retry policies shared by model, Modal, and tool execution."""
from __future__ import annotations

import asyncio
from dataclasses import dataclass
from random import random
from typing import Awaitable, Callable, TypeVar

T = TypeVar("T")


class RetryableActionError(RuntimeError):
    pass


class PermanentActionError(RuntimeError):
    pass


@dataclass(frozen=True)
class RetryPolicy:
    max_retries: int
    base_delay_seconds: float = 1.0
    max_delay_seconds: float = 8.0
    jitter_ratio: float = 0.20

    def delay(self, retry_index: int) -> float:
        base = min(self.max_delay_seconds, self.base_delay_seconds * (2 ** retry_index))
        return base + base * self.jitter_ratio * random()


def _classify_modal_exception(exc: BaseException) -> bool | None:
    """Classify Modal SDK errors by concrete type instead of sniffing gRPC status.

    Modal will stop propagating the raw ``grpclib.GRPCError`` type, so the old
    ``.status``/``.status_code`` sniffing is going away. Modal now raises typed
    exceptions from ``modal.exception``; classify those directly. Returns True
    (retry), False (permanent), or None (not a Modal error / undecided).
    """
    try:
        import modal.exception as modal_exc
    except Exception:
        return None
    if not isinstance(exc, modal_exc.Error):
        return None
    permanent = (
        modal_exc.InvalidError,
        modal_exc.NotFoundError,
        modal_exc.AuthError,
        modal_exc.PermissionDeniedError,
        modal_exc.AlreadyExistsError,
        modal_exc.VersionError,
    )
    if isinstance(exc, permanent):
        return False
    transient = (
        modal_exc.ResourceExhaustedError,
        modal_exc.InternalError,
        modal_exc.RemoteError,
        modal_exc.ConnectionError,
        modal_exc.TimeoutError,
    )
    if isinstance(exc, transient):
        return True
    return None


def is_retryable_exception(exc: BaseException) -> bool:
    if isinstance(exc, PermanentActionError):
        return False
    if isinstance(exc, (RetryableActionError, TimeoutError, asyncio.TimeoutError, ConnectionError)):
        return True
    retryable = getattr(exc, "retryable", None)
    if retryable is not None:
        return bool(retryable)
    modal_verdict = _classify_modal_exception(exc)
    if modal_verdict is not None:
        return modal_verdict
    status = getattr(exc, "status", None) or getattr(exc, "status_code", None)
    if isinstance(status, int):
        return status in {408, 425, 429} or status >= 500
    # Unknown tool/provider failures are retried conservatively; validation and
    # policy code should raise ValueError or PermanentActionError instead.
    return not isinstance(exc, (ValueError, TypeError, KeyError, PermissionError))


async def retry_async(
    operation: Callable[[], Awaitable[T]],
    *,
    policy: RetryPolicy,
    retryable: Callable[[BaseException], bool] = is_retryable_exception,
) -> T:
    for attempt in range(policy.max_retries + 1):
        try:
            return await operation()
        except BaseException as exc:
            if attempt >= policy.max_retries or not retryable(exc):
                raise
            await asyncio.sleep(policy.delay(attempt))
    raise AssertionError("retry loop exhausted without returning or raising")
