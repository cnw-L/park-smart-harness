"""Bounded executor for synchronous PyMilvus calls."""

from __future__ import annotations

import asyncio
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from functools import partial
from threading import Semaphore
from typing import Any, Callable, TypeVar


T = TypeVar("T")


class MilvusExecutorBusy(RuntimeError):
    """Raised when too many Milvus calls are already in flight."""


@dataclass(frozen=True)
class MilvusExecutorConfig:
    """Concurrency limits for the synchronous Milvus SDK adapter."""

    max_workers: int = 8
    max_in_flight: int = 16
    queue_timeout_seconds: float = 0.01


class BoundedMilvusExecutor:
    """Run blocking Milvus calls without using the event loop default executor."""

    def __init__(self, config: MilvusExecutorConfig | None = None) -> None:
        self.config = config or MilvusExecutorConfig()
        self._executor = ThreadPoolExecutor(
            max_workers=self.config.max_workers,
            thread_name_prefix="assistant-core-milvus",
        )
        self._semaphore = Semaphore(self.config.max_in_flight)
        self._closed = False

    async def run(
        self,
        func: Callable[..., T],
        *args: Any,
        queue_timeout_seconds: float | None = None,
        **kwargs: Any,
    ) -> T:
        """Run a blocking function with short admission backpressure."""

        if self._closed:
            raise RuntimeError("Milvus executor is closed")

        timeout = self.config.queue_timeout_seconds if queue_timeout_seconds is None else queue_timeout_seconds
        if not self._semaphore.acquire(timeout=timeout):
            raise MilvusExecutorBusy("Milvus executor is at capacity")
        try:
            loop = asyncio.get_running_loop()
            call = partial(func, *args, **kwargs)
            future = loop.run_in_executor(self._executor, call)
            return await future
        finally:
            self._semaphore.release()

    def close(self) -> None:
        self._closed = True
        self._executor.shutdown(wait=False, cancel_futures=True)
