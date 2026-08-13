# VideOCR Engine Modifications

This fork keeps the upstream VideOCR/PaddleOCR extraction engine and adds a server-focused CPU CLI contract for Chinese SRT extraction.

## Baseline

- Upstream project: https://github.com/timminator/VideOCR
- Fork origin: https://github.com/ThaungThanHan/VideOCR.git
- Baseline target: upstream `v1.5.1` release, pending exact upstream commit verification on the deployment host.
- Local commit at modification time: `8f8c5c181604ab386304b84fab957f02083cc683`
- License: MIT, preserved in `LICENSE`.

## Runtime

- Python: Python 3.11 required for the server environment. This local host currently exposes `python3` as Python 3.13.7 and does not have `python3.11` on PATH.
- FFmpeg: FFmpeg 6.x recommended for the VPS target. This local host has FFmpeg 8.1.2.
- OCR engine: PaddleOCR CPU only.
- GPU/CUDA: not used by `videocr-engine extract`.
- GUI: unchanged and not required for the server CLI.

## Server Additions

- `server_cli/`: stable command wrapper exposed as `videocr-engine`.
- `scripts/validate_srt.py`: structural SRT validation helper.
- `docs/`: runtime, CLI, progress, cancellation, SRT, deployment, and integration documentation.
- `benchmarks/`: metadata-only benchmark records. Private videos must not be committed.

## Verification Commands

```bash
git remote -v
git status --short
git rev-parse HEAD
python3 --version
ffmpeg -version | head -1
```
