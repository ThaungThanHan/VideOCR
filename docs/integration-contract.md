# Integration Contract

The future FastAPI backend should invoke the engine as a local subprocess. It should not import private VideOCR modules.

Command:

```bash
videocr-engine extract \
  --input <job-dir>/input.mp4 \
  --output <job-dir>/output.srt \
  --language ch \
  --crop x,y,width,height \
  --progress-jsonl <job-dir>/progress.jsonl \
  --cancel-file <job-dir>/cancel \
  --timeout-seconds 7200
```

Job directory:

```text
<job-dir>/
  input.mp4
  output.srt
  output.srt.part
  progress.jsonl
  cancel
```

Allowed options:

- language: `ch`
- crop: required manual subtitle crop
- time range: optional
- concurrency: start with one active job; queue at most two until benchmarks prove otherwise

Result ownership:

- The engine owns `.part` output during extraction.
- The backend owns upload retention, final result retention, cancellation marker creation, and stale job cleanup.

Exit codes are documented in `docs/server-cli.md`.
