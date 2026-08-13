from __future__ import annotations

from dataclasses import dataclass


SUPPORTED_LANGUAGES = {"ch"}


class ExitCode:
    OK = 0
    VALIDATION = 2
    FAILED = 10
    CANCELLED = 20
    TIMEOUT = 30


@dataclass(frozen=True)
class EngineDefaults:
    conf_threshold: int = 75
    sim_threshold: int = 80
    max_merge_gap: float = 0.09
    ssim_threshold: int = 92
    frames_to_skip: int = 1
    min_subtitle_duration: float = 0.2
    ocr_image_max_width: int = 720
    max_input_bytes: int = 5 * 1024 * 1024 * 1024
