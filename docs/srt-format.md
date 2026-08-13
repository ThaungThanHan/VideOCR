# SRT Format

Server output is normalized and validated before success is reported.

Rules:

- UTF-8 text.
- Sequential cue numbers beginning at `1`.
- Timestamps use `HH:MM:SS,mmm --> HH:MM:SS,mmm`.
- Empty text cues are removed.
- Whitespace is normalized without changing Chinese characters.
- Overlaps are clamped forward.
- Adjacent identical text with a small gap is merged.
- Traditional Chinese is preserved; no Simplified conversion is performed by the wrapper.

Validate an output file:

```bash
.venv/bin/python scripts/validate_srt.py /path/to/output.srt
```
