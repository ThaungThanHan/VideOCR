from __future__ import annotations

import json
import sys
import time
from pathlib import Path
from typing import Any, TextIO


class ProgressWriter:
    def __init__(self, path: Path | None = None) -> None:
        self._stream: TextIO | None = None
        self._owns_stream = False
        self._last_progress = 0

        if path is None:
            self._stream = sys.stdout
        else:
            path.parent.mkdir(parents=True, exist_ok=True)
            self._stream = path.open("a", encoding="utf-8")
            self._owns_stream = True

    def emit(self, event: str, stage: str, progress: int, **fields: Any) -> None:
        if self._stream is None:
            return

        progress = max(self._last_progress, min(100, progress))
        self._last_progress = progress

        payload: dict[str, Any] = {
            "event": event,
            "stage": stage,
            "progress": progress,
            "timestamp": time.time(),
        }
        payload.update({k: v for k, v in fields.items() if v is not None})
        self._stream.write(json.dumps(payload, ensure_ascii=False, separators=(",", ":")) + "\n")
        self._stream.flush()

    def close(self) -> None:
        if self._owns_stream and self._stream is not None:
            self._stream.close()
        self._stream = None

    def __enter__(self) -> ProgressWriter:
        return self

    def __exit__(self, *_: object) -> None:
        self.close()
