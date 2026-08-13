from __future__ import annotations

import argparse
import contextlib
import datetime
import os
import shutil
import sys
from pathlib import Path

SOURCE_ROOT = Path(__file__).resolve().parents[2]
CLI_ROOT = SOURCE_ROOT / "CLI"
if CLI_ROOT.is_dir() and str(CLI_ROOT) not in sys.path:
    sys.path.insert(0, str(CLI_ROOT))

from server_cli.cancellation import CancelledError, CancellationToken, EngineTimeoutError, SignalHandlers
from server_cli.config import EngineDefaults, ExitCode, SUPPORTED_LANGUAGES
from server_cli.progress import ProgressWriter
from server_cli.srt_output import normalize_srt_file, validate_srt_file


def add_extract_parser(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--input", required=True, help="Input video path.")
    parser.add_argument("--output", required=True, help="Output SRT path.")
    parser.add_argument("--language", default="ch", help="OCR language. Only 'ch' is supported for the server engine.")
    parser.add_argument("--crop", required=True, help="Subtitle crop as x,y,width,height.")
    parser.add_argument("--time-start", default="00:00:00", help="Optional start time as HH:MM:SS or MM:SS.")
    parser.add_argument("--time-end", default="", help="Optional end time as HH:MM:SS or MM:SS.")
    parser.add_argument("--progress-jsonl", default=None, help="Write JSONL progress events to this file instead of stdout.")
    parser.add_argument("--cancel-file", default=None, help="Cancel when this marker file appears.")
    parser.add_argument("--timeout-seconds", type=int, default=None, help="Command timeout in seconds.")
    parser.add_argument("--allowed-root", action="append", default=[], help="Additional root allowed for output/progress/cancel paths.")
    parser.add_argument("--max-input-bytes", type=int, default=EngineDefaults.max_input_bytes, help="Maximum input video size.")
    parser.add_argument("--frames-to-skip", type=int, default=EngineDefaults.frames_to_skip, help="CPU frame skip count.")
    parser.add_argument("--ssim-threshold", type=int, default=EngineDefaults.ssim_threshold, help="Initial SSIM filtering threshold.")
    parser.add_argument("--ocr-image-max-width", type=int, default=EngineDefaults.ocr_image_max_width, help="Maximum OCR image width.")


def _resolve_path(raw_path: str) -> Path:
    return Path(raw_path).expanduser().resolve(strict=False)


def _parse_crop(value: str) -> dict[str, int]:
    parts = value.split(",")
    if len(parts) != 4:
        raise ValueError("--crop must be x,y,width,height")
    try:
        x, y, width, height = [int(part.strip()) for part in parts]
    except ValueError as exc:
        raise ValueError("--crop values must be integers") from exc
    if x < 0 or y < 0:
        raise ValueError("--crop x and y must be non-negative")
    if width <= 0 or height <= 0:
        raise ValueError("--crop width and height must be positive")
    return {"x": x, "y": y, "width": width, "height": height}


def _is_within(path: Path, root: Path) -> bool:
    try:
        path.resolve(strict=False).relative_to(root.resolve(strict=False))
        return True
    except ValueError:
        return False


def _validate_path_scope(path: Path, roots: list[Path], label: str) -> None:
    if not any(_is_within(path, root) for root in roots):
        allowed = ", ".join(str(root) for root in roots)
        raise ValueError(f"{label} must be inside the job directory or an allowed root: {allowed}")


def _validate_time_range(time_start: str, time_end: str) -> None:
    if time_start:
        _get_ms_from_time_str(time_start)
    if time_end:
        _get_ms_from_time_str(time_end)
    if time_start and time_end and _get_ms_from_time_str(time_start) > _get_ms_from_time_str(time_end):
        raise ValueError("--time-start cannot be after --time-end")


def _get_ms_from_time_str(time_str: str) -> float:
    try:
        parts = [float(value) for value in time_str.split(":")]
    except ValueError as exc:
        raise ValueError(f"Invalid time value: {time_str}") from exc

    if len(parts) == 3:
        td = datetime.timedelta(hours=parts[0], minutes=parts[1], seconds=parts[2])
    elif len(parts) == 2:
        td = datetime.timedelta(minutes=parts[0], seconds=parts[1])
    else:
        raise ValueError(f"Invalid time format '{time_str}'. Use MM:SS or HH:MM:SS.")
    return td.total_seconds() * 1000


def _validate_args(args: argparse.Namespace) -> tuple[Path, Path, Path | None, Path | None, dict[str, int], dict[str, int]]:
    input_path = _resolve_path(args.input)
    output_path = _resolve_path(args.output)
    progress_path = _resolve_path(args.progress_jsonl) if args.progress_jsonl else None
    cancel_file = _resolve_path(args.cancel_file) if args.cancel_file else None

    if args.language not in SUPPORTED_LANGUAGES:
        raise ValueError(f"Unsupported language '{args.language}'. Supported languages: {', '.join(sorted(SUPPORTED_LANGUAGES))}")
    if not input_path.is_file():
        raise ValueError(f"Input does not exist or is not a regular file: {input_path}")
    if not os.access(input_path, os.R_OK):
        raise ValueError(f"Input is not readable: {input_path}")
    if input_path.stat().st_size > args.max_input_bytes:
        raise ValueError(f"Input exceeds size limit of {args.max_input_bytes} bytes")

    crop = _parse_crop(args.crop)
    _validate_time_range(args.time_start, args.time_end)

    from videocr.pyav_adapter import get_video_properties

    props = get_video_properties(str(input_path))
    if props["width"] <= 0 or props["height"] <= 0:
        raise ValueError("Could not decode input video dimensions")
    if crop["x"] + crop["width"] > props["width"] or crop["y"] + crop["height"] > props["height"]:
        raise ValueError(
            f"Crop {args.crop} is outside decoded video dimensions {props['width']}x{props['height']}"
        )

    job_root = input_path.parent
    allowed_roots = [job_root, *[_resolve_path(root) for root in args.allowed_root]]
    _validate_path_scope(output_path, allowed_roots, "output path")
    if progress_path is not None:
        _validate_path_scope(progress_path, allowed_roots, "progress path")
    if cancel_file is not None:
        _validate_path_scope(cancel_file, allowed_roots, "cancel file")

    output_path.parent.mkdir(parents=True, exist_ok=True)
    if progress_path is not None:
        progress_path.parent.mkdir(parents=True, exist_ok=True)

    if args.timeout_seconds is not None and args.timeout_seconds <= 0:
        raise ValueError("--timeout-seconds must be positive")
    if args.frames_to_skip < 0:
        raise ValueError("--frames-to-skip must be non-negative")
    if not 0 <= args.ssim_threshold <= 100:
        raise ValueError("--ssim-threshold must be between 0 and 100")
    if args.ocr_image_max_width <= 0:
        raise ValueError("--ocr-image-max-width must be positive")

    return input_path, output_path, progress_path, cancel_file, crop, props


def _remove_if_exists(path: Path) -> None:
    with contextlib.suppress(FileNotFoundError):
        path.unlink()


def run_extract(args: argparse.Namespace) -> int:
    progress: ProgressWriter | None = None
    output_path: Path | None = None
    temp_output: Path | None = None

    try:
        input_path, output_path, progress_path, cancel_file, crop, props = _validate_args(args)
        temp_output = output_path.with_name(output_path.name + ".part")
        _remove_if_exists(temp_output)

        token = CancellationToken(cancel_file=cancel_file, timeout_seconds=args.timeout_seconds)
        with ProgressWriter(progress_path) as progress, SignalHandlers(token):
            progress.emit("started", "metadata", 0, input=str(input_path), duration=props["duration_ms"] / 1000)
            token.raise_if_cancelled()

            progress.emit("processing", "ocr", 5, current_time=0, duration=props["duration_ms"] / 1000)
            from videocr import save_subtitles_to_file

            with contextlib.redirect_stdout(sys.stderr):
                save_subtitles_to_file(
                    video_path=str(input_path),
                    file_path=str(temp_output),
                    ocr_engine="paddleocr",
                    lang=args.language,
                    time_start=args.time_start,
                    time_end=args.time_end,
                    conf_threshold=EngineDefaults.conf_threshold,
                    sim_threshold=EngineDefaults.sim_threshold,
                    max_merge_gap_sec=EngineDefaults.max_merge_gap,
                    use_fullframe=False,
                    use_gpu=False,
                    use_angle_cls=False,
                    use_server_model=False,
                    brightness_threshold=None,
                    ssim_threshold=args.ssim_threshold,
                    subtitle_position="center",
                    frames_to_skip=args.frames_to_skip,
                    crop_zones=[crop],
                    normalize_to_simplified_chinese=False,
                    post_processing=False,
                    min_subtitle_duration_sec=EngineDefaults.min_subtitle_duration,
                    ocr_image_max_width=args.ocr_image_max_width,
                    subtitle_alignments=[None, None],
                )

            token.raise_if_cancelled()
            progress.emit("processing", "export", 95, current_time=props["duration_ms"] / 1000, duration=props["duration_ms"] / 1000)

            cue_count = normalize_srt_file(temp_output)
            if cue_count == 0:
                raise RuntimeError("extraction produced no SRT cues")
            validate_srt_file(temp_output)
            shutil.move(str(temp_output), str(output_path))
            progress.emit("completed", "export", 100, output=str(output_path), cues=cue_count)
            return ExitCode.OK

    except CancelledError as exc:
        _remove_if_exists(temp_output) if temp_output else None
        _remove_if_exists(output_path) if output_path else None
        if progress:
            progress.emit("cancelled", "cancel", 100, message=str(exc))
        print(f"Cancelled: {exc}", file=sys.stderr, flush=True)
        return ExitCode.CANCELLED
    except EngineTimeoutError as exc:
        _remove_if_exists(temp_output) if temp_output else None
        _remove_if_exists(output_path) if output_path else None
        if progress:
            progress.emit("failed", "timeout", 100, message=str(exc))
        print(f"Timeout: {exc}", file=sys.stderr, flush=True)
        return ExitCode.TIMEOUT
    except ValueError as exc:
        if progress:
            progress.emit("failed", "validation", 100, message=str(exc))
        print(f"Validation error: {exc}", file=sys.stderr, flush=True)
        return ExitCode.VALIDATION
    except SystemExit as exc:
        _remove_if_exists(temp_output) if temp_output else None
        code = exc.code if isinstance(exc.code, int) else ExitCode.FAILED
        if progress:
            progress.emit("failed", "engine", 100, message=f"engine exited with {code}")
        return ExitCode.FAILED
    except Exception as exc:
        _remove_if_exists(temp_output) if temp_output else None
        _remove_if_exists(output_path) if output_path else None
        if progress:
            progress.emit("failed", "engine", 100, message=str(exc))
        print(f"Error: {exc}", file=sys.stderr, flush=True)
        return ExitCode.FAILED
