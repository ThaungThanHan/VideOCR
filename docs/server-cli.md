# Server CLI

`videocr-engine` provides the stable contract for the future product backend.

```bash
videocr-engine extract \
  --input /var/lib/subextractor/jobs/<job-id>/input.mp4 \
  --output /var/lib/subextractor/jobs/<job-id>/output.srt \
  --language ch \
  --crop x,y,width,height \
  --progress-jsonl /var/lib/subextractor/jobs/<job-id>/progress.jsonl \
  --cancel-file /var/lib/subextractor/jobs/<job-id>/cancel
```

Optional arguments:

- `--time-start HH:MM:SS`
- `--time-end HH:MM:SS`
- `--timeout-seconds N`
- `--allowed-root PATH`
- `--frames-to-skip N`
- `--ssim-threshold 0..100`
- `--ocr-image-max-width N`

Exit codes:

- `0`: success
- `2`: validation error
- `10`: engine failure
- `20`: cancellation
- `30`: timeout

The wrapper rejects non-`ch` languages, requires an explicit crop, forces PaddleOCR CPU mode, disables full-frame extraction, writes UTF-8 SRT output, and validates the SRT before reporting success.
