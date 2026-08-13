from __future__ import annotations

import signal
import time
from pathlib import Path


class CancelledError(RuntimeError):
    pass


class EngineTimeoutError(RuntimeError):
    pass


class CancellationToken:
    def __init__(self, cancel_file: Path | None = None, timeout_seconds: int | None = None) -> None:
        self.cancel_file = cancel_file
        self.timeout_seconds = timeout_seconds
        self.started_at = time.monotonic()
        self._cancelled = False

    def cancel(self) -> None:
        self._cancelled = True

    def raise_if_cancelled(self) -> None:
        if self._cancelled or (self.cancel_file is not None and self.cancel_file.exists()):
            raise CancelledError("extraction cancelled")
        if self.timeout_seconds is not None and time.monotonic() - self.started_at > self.timeout_seconds:
            raise EngineTimeoutError(f"extraction exceeded timeout of {self.timeout_seconds} seconds")


class SignalHandlers:
    def __init__(self, token: CancellationToken) -> None:
        self.token = token
        self._previous: list[tuple[int, signal.Handlers]] = []

    def __enter__(self) -> SignalHandlers:
        for sig in (signal.SIGINT, signal.SIGTERM):
            previous = signal.getsignal(sig)
            self._previous.append((sig, previous))

            def handler(_signum: int, _frame: object) -> None:
                self.token.cancel()
                raise CancelledError("extraction cancelled by signal")

            signal.signal(sig, handler)
        return self

    def __exit__(self, *_: object) -> None:
        for sig, previous in self._previous:
            signal.signal(sig, previous)
