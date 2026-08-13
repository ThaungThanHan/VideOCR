# Cancellation

`videocr-engine extract` accepts `--cancel-file PATH` and listens for `SIGINT`/`SIGTERM`.

Behavior:

- Cancellation before OCR starts exits with code `20`.
- Signal cancellation exits with code `20`.
- Incomplete `.part` output is removed.
- Any pre-existing final output path is removed when cancellation is detected.
- A `cancelled` progress event is emitted when progress output is available.

`--timeout-seconds N` enforces a command-level timeout at wrapper checkpoints and exits with code `30`. The future FastAPI worker should still enforce an outer subprocess timeout so it can terminate the whole process tree if needed.
