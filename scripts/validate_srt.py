#!/usr/bin/env python3
from __future__ import annotations

import sys
from pathlib import Path

SOURCE_ROOT = Path(__file__).resolve().parents[1]
if str(SOURCE_ROOT) not in sys.path:
    sys.path.insert(0, str(SOURCE_ROOT))

from server_cli.srt_output import validate_srt_file


def main() -> int:
    if len(sys.argv) != 2:
        print("usage: validate_srt.py PATH", file=sys.stderr)
        return 2
    try:
        cue_count = validate_srt_file(Path(sys.argv[1]))
    except Exception as exc:
        print(f"invalid SRT: {exc}", file=sys.stderr)
        return 1
    print(f"valid SRT: {cue_count} cues")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
