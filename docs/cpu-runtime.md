# CPU Runtime

Use an isolated Python 3.11 environment. Do not install CUDA or GPU PaddleOCR builds for this server engine.

```bash
python3.11 -m venv .venv
.venv/bin/python -m pip install --upgrade pip
.venv/bin/python -m pip install -e .
```

Verify the core dependencies:

```bash
.venv/bin/python -c "import av, numpy, PIL, psutil; print('core imports ok')"
.venv/bin/python -m pip check
```

The packaged PaddleOCR executable/model bundle used by upstream VideOCR must be present beside the installed command, matching the upstream runtime layout. The server wrapper always passes `use_gpu=False`.
