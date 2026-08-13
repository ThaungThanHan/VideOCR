# Progress Events

Progress is emitted as JSON Lines either to stdout or to `--progress-jsonl`.

Example:

```json
{"event":"started","stage":"metadata","progress":0}
{"event":"processing","stage":"ocr","progress":5,"current_time":0,"duration":742.8}
{"event":"processing","stage":"export","progress":95,"current_time":742.8,"duration":742.8}
{"event":"completed","stage":"export","progress":100,"output":"output.srt","cues":27}
```

Fields:

- `event`: `started`, `processing`, `completed`, `cancelled`, or `failed`
- `stage`: current coarse stage
- `progress`: monotonic integer from `0` to `100`
- `timestamp`: Unix timestamp
- `current_time`: approximate processed video time in seconds when known
- `duration`: decoded input duration in seconds when known
- `output`: final SRT path on success
- `cues`: cue count on success
- `message`: failure/cancellation detail

Current progress is coarse because upstream VideOCR does not expose a stable per-frame callback contract. The wrapper keeps the schema stable so a future worker can tail this file without parsing human logs.
