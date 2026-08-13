from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

TIMESTAMP_RE = re.compile(
    r"^(?P<sh>\d{2}):(?P<sm>\d{2}):(?P<ss>\d{2}),(?P<sms>\d{3}) --> "
    r"(?P<eh>\d{2}):(?P<em>\d{2}):(?P<es>\d{2}),(?P<ems>\d{3})$"
)


@dataclass
class Cue:
    start_ms: int
    end_ms: int
    text: str


def _timestamp_to_ms(h: str, m: str, s: str, ms: str) -> int:
    return ((int(h) * 60 + int(m)) * 60 + int(s)) * 1000 + int(ms)


def _ms_to_timestamp(value: int) -> str:
    value = max(0, value)
    seconds, ms = divmod(value, 1000)
    minutes, seconds = divmod(seconds, 60)
    hours, minutes = divmod(minutes, 60)
    return f"{hours:02d}:{minutes:02d}:{seconds:02d},{ms:03d}"


def parse_srt(text: str) -> list[Cue]:
    cues: list[Cue] = []
    blocks = [block.strip() for block in text.replace("\r\n", "\n").replace("\r", "\n").split("\n\n") if block.strip()]

    for block in blocks:
        lines = block.splitlines()
        if len(lines) < 3:
            raise ValueError("SRT cue must contain an index, timestamp line, and text")

        match = TIMESTAMP_RE.match(lines[1].strip())
        if not match:
            raise ValueError(f"Invalid SRT timestamp line: {lines[1]}")

        start_ms = _timestamp_to_ms(match["sh"], match["sm"], match["ss"], match["sms"])
        end_ms = _timestamp_to_ms(match["eh"], match["em"], match["es"], match["ems"])
        text_lines = [re.sub(r"[ \t]+", " ", line).strip() for line in lines[2:]]
        cue_text = "\n".join(line for line in text_lines if line).strip()

        if not cue_text:
            continue
        if end_ms <= start_ms:
            end_ms = start_ms + 1

        cues.append(Cue(start_ms=start_ms, end_ms=end_ms, text=cue_text))

    return cues


def normalize_cues(cues: list[Cue]) -> list[Cue]:
    normalized: list[Cue] = []

    for cue in sorted(cues, key=lambda item: (item.start_ms, item.end_ms)):
        if normalized and cue.start_ms < normalized[-1].end_ms:
            cue.start_ms = normalized[-1].end_ms
            if cue.end_ms <= cue.start_ms:
                cue.end_ms = cue.start_ms + 1

        if normalized and cue.text == normalized[-1].text and cue.start_ms <= normalized[-1].end_ms + 90:
            normalized[-1].end_ms = max(normalized[-1].end_ms, cue.end_ms)
            continue

        normalized.append(cue)

    return normalized


def render_srt(cues: list[Cue]) -> str:
    blocks: list[str] = []
    for index, cue in enumerate(cues, 1):
        blocks.append(
            f"{index}\n"
            f"{_ms_to_timestamp(cue.start_ms)} --> {_ms_to_timestamp(cue.end_ms)}\n"
            f"{cue.text}\n"
        )
    return "\n".join(blocks)


def normalize_srt_file(path: Path) -> int:
    text = path.read_text(encoding="utf-8")
    cues = normalize_cues(parse_srt(text))
    path.write_text(render_srt(cues), encoding="utf-8")
    return len(cues)


def validate_srt_file(path: Path) -> int:
    text = path.read_text(encoding="utf-8")
    cues = parse_srt(text)
    previous_end = -1

    for cue in cues:
        if cue.start_ms < previous_end:
            raise ValueError("SRT cues overlap")
        if cue.end_ms <= cue.start_ms:
            raise ValueError("SRT cue end must be after start")
        previous_end = cue.end_ms

    return len(cues)
