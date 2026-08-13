# VideOCR Chinese SRT Server Engine Modification Plan

> **For Hermes:** Use this plan to modify the forked VideOCR project and deploy the CPU CLI to Capsule Corp. Do not begin web-app work until the engine benchmark and CLI contract are verified.

**Goal:** Adapt the forked `timminator/VideOCR` project into a VPS-friendly, Chinese-only CPU subtitle-extraction engine that accepts a video plus a manually selected subtitle crop and exports a standard SRT file like `cooking_raw_27.srt`.

**Architecture:** Keep VideOCR/PaddleOCR as the extraction engine and remove GUI requirements from the server runtime. Expose a deterministic CLI wrapper that processes one job at a time initially, emits machine-readable progress, supports cancellation, and writes SRT output. A future FastAPI product backend will invoke this CLI as a worker subprocess; it must not depend on the GUI.

**Tech Stack:** Python 3.11 virtual environment, VideOCR fork, PaddleOCR CPU, FFmpeg/ffprobe, PyAV or the existing VideOCR frame pipeline, Fast-SSIM, OpenCC, `srt`/existing SRT exporter, `psutil`, JSON Lines progress events, systemd, and local filesystem job directories.

---

## Product boundary

### Required now

- Chinese subtitle extraction only.
- Support the repository's Chinese language mode (`ch`, Chinese + English) and optionally Traditional Chinese mode only if the selected model is verified.
- Manual subtitle-region crop; no automatic region detection.
- CPU-only processing on the current 2-vCPU VPS.
- Input video path and output SRT path.
- Optional start/end time range.
- Frame skipping and SSIM filtering enabled by default.
- SRT cues with sequential numbering and `HH:MM:SS,mmm --> HH:MM:SS,mmm` timing.
- Preserve Chinese text as Unicode without accidental encoding loss.
- Deterministic non-zero exit codes for invalid input, failure, cancellation, and timeout.
- Machine-readable progress for a future FastAPI worker.

### Explicitly excluded

- GUI modification or macOS packaging in this phase.
- Web API, authentication, uploads, database, accounts, and billing.
- Google Lens/cloud OCR.
- GPU/CUDA support.
- PDF/VTT export.
- Automatic subtitle-box detection.
- Translation, simplification, or rewriting of extracted Chinese text.
- New automated test framework if the fork has no existing test convention; use focused fixtures, CLI smoke tests, and real execution benchmarks instead.

## Input/output contract

### Command shape

The final server command should be stable and scriptable. Prefer a new wrapper entry point rather than forcing the future backend to depend on internal module functions:

```bash
videocr-engine extract \
  --input /var/lib/subextractor/jobs/<job-id>/input.mp4 \
  --output /var/lib/subextractor/jobs/<job-id>/output.srt \
  --language ch \
  --crop x,y,width,height \
  --time-start 00:00:00 \
  --time-end 00:00:00 \
  --progress-jsonl /var/lib/subextractor/jobs/<job-id>/progress.jsonl \
  --cancel-file /var/lib/subextractor/jobs/<job-id>/cancel
```

`--time-start`, `--time-end`, `--progress-jsonl`, and `--cancel-file` may be optional. The first implementation may preserve the upstream CLI flags internally, but the wrapper must provide the stable contract above.

### SRT requirements

- UTF-8 output.
- Sequential cue numbers beginning at `1`.
- Comma-separated milliseconds, not periods.
- No overlapping cues.
- No empty text cues.
- Adjacent identical text should be merged according to the existing VideOCR merge logic.
- Cue timing must use video/frame timestamps, not OCR completion time.
- A representative output should be structurally comparable to `cooking_raw_27.srt`; exact OCR text depends on the supplied video and crop.

Example expected shape:

```srt
1
00:00:00,000 --> 00:00:02,000
但是项链不是花卷拿的

2
00:00:02,000 --> 00:00:02,800
是我放的
```

---

## Modification plan

### Task 1: Create and pin the fork baseline

**Objective:** Establish a reproducible fork baseline before changing behavior.

**Files:**
- Fork repository: `timminator/VideOCR` → the authorized GitHub owner/repository.
- Create: `ENGINE_MODIFICATIONS.md`
- Preserve: `LICENSE`

**Steps:**

1. Fork the upstream repository and clone the fork into the VPS workspace.
2. Add the original repository as `upstream`.
3. Record the upstream commit/tag used, initially the verified `v1.5.1` release or its exact commit.
4. Confirm the repository license and preserve the MIT notice.
5. Record the fork URL, upstream URL, baseline version, Python version, and FFmpeg version in `ENGINE_MODIFICATIONS.md`.

**Verification:**

```bash
git remote -v
git status --short
git rev-parse HEAD
python3 --version
ffmpeg -version | head -1
```

Expected: clean working tree, correct fork/origin and upstream remotes, Python 3.11 available, FFmpeg 6.x available.

### Task 2: Create an isolated CPU runtime

**Objective:** Install the fork without modifying the system Python or Hermes environment.

**Files:**
- Create: `.venv/` (ignored by Git)
- Modify: `pyproject.toml` or a server-specific dependency file only if required
- Create/modify: `.gitignore`
- Create: `docs/cpu-runtime.md`

**Steps:**

1. Create a project virtual environment using Python 3.11.
2. Install the fork's CPU dependencies in that environment.
3. Do not install CUDA packages or use the GPU release.
4. Verify imports for the existing VideOCR core, PaddleOCR dependencies, PyAV, Fast-SSIM, OpenCC, Pillow, NumPy, and `psutil`.
5. Document the exact install command and any dependency pinning needed for repeatable deployment.

**Verification:**

```bash
.venv/bin/python -c "import av, numpy, PIL, psutil; print('core imports ok')"
.venv/bin/python -m pip check
```

Expected: imports succeed and `pip check` reports no broken requirements.

### Task 3: Prove the unmodified CPU CLI

**Objective:** Establish a real baseline on Capsule Corp before modifying the engine.

**Files:**
- Create: `benchmarks/README.md`
- Create: `benchmarks/results/` (benchmark outputs should not include private videos)

**Steps:**

1. Select a representative local Chinese-subtitle video and a manually verified crop.
2. Run the upstream CPU CLI against a short range first.
3. Use Chinese + English mode (`ch`) unless the video is Traditional Chinese-only; do not normalize text unless explicitly desired.
4. Enable crop, frame skipping, SSIM filtering, and an OCR width cap suitable for CPU processing.
5. Capture wall-clock time, peak RSS, CPU usage, output size, number of cues, and exit status.
6. Inspect the generated SRT for UTF-8 Chinese text, timestamps, duplicate cues, empty cues, and obvious timing errors.

**Verification:**

The run must produce a non-empty `.srt` file and the benchmark record must contain real measurements, not estimates. Save only metadata and a small redacted/fixture output to the repository.

### Task 4: Add a server-focused CLI wrapper

**Objective:** Provide a stable command contract without coupling the future API to VideOCR internals.

**Files:**
- Create: `server_cli/`
- Create: `server_cli/__main__.py`
- Create: `server_cli/commands/extract.py`
- Create: `server_cli/config.py`
- Modify: `pyproject.toml` to expose `videocr-engine` entry point
- Create: `docs/server-cli.md`

**Steps:**

1. Add an `extract` subcommand.
2. Validate that the input exists, is a regular file, is readable, and is within the configured size limit.
3. Validate crop coordinates are non-negative, complete, and inside the decoded video dimensions.
4. Validate the language is Chinese-only (`ch` initially).
5. Validate output and progress paths are inside the job directory or an explicitly allowed root.
6. Translate the wrapper options into the existing VideOCR CLI/library options.
7. Use argument arrays/subprocess APIs; never use shell interpolation.
8. Set CPU-safe defaults: `use_gpu=false`, crop required, full-frame disabled, SSIM enabled, frame skipping enabled, and bounded OCR image width.
9. Return documented exit codes.

**Verification:**

```bash
.venv/bin/videocr-engine --help
.venv/bin/videocr-engine extract --help
.venv/bin/videocr-engine extract --language en ...
```

Expected: help is available; invalid non-Chinese language is rejected before processing; malformed crop/input arguments return a non-zero validation exit code.

### Task 5: Add structured progress events

**Objective:** Allow the future FastAPI worker to report progress without parsing human-readable logs.

**Files:**
- Modify: `server_cli/commands/extract.py`
- Create: `server_cli/progress.py`
- Create: `docs/progress-events.md`

**Event format:** One JSON object per line, flushed immediately:

```json
{"event":"started","stage":"metadata","progress":0}
{"event":"processing","stage":"ocr","progress":47,"current_time":312.4,"duration":742.8}
{"event":"completed","stage":"export","progress":100,"output":"output.srt"}
```

**Steps:**

1. Emit `started`, stage changes, periodic `processing`, `completed`, `cancelled`, and `failed` events.
2. Keep progress monotonic from 0 to 100.
3. Use frame/video timestamps for `current_time`.
4. Flush each event so a parent worker can tail the file or read stdout.
5. Keep human-readable logs on stderr and structured events on stdout or the configured JSONL file.
6. Document fields and compatibility expectations.

**Verification:**

Run a short extraction and parse every JSONL line with Python. Expected: all lines are valid JSON, event order is sensible, and a successful job ends with exactly one `completed` event.

### Task 6: Add cancellation and timeout handling

**Objective:** Stop expensive work cleanly and leave no partially trusted result.

**Files:**
- Modify: `server_cli/commands/extract.py`
- Create: `server_cli/cancellation.py`
- Create: `docs/cancellation.md`

**Steps:**

1. Accept a cancellation marker file and/or a signal from the parent process.
2. Check cancellation between frame batches and before OCR work.
3. On cancellation, emit a `cancelled` event, remove incomplete output, and return the documented cancellation code.
4. Add a command-level timeout option; the future API worker may also enforce an outer timeout.
5. Ensure child FFmpeg/PaddleOCR processes or threads are not left running after cancellation.
6. Ensure temporary frame data is released after each batch.

**Verification:**

Start a long or deliberately slowed extraction, create the cancellation marker, and verify that the process exits, no complete-looking SRT is left, and the event stream ends with `cancelled`.

### Task 7: Normalize and validate SRT export

**Objective:** Guarantee output compatible with the supplied `cooking_raw_27.srt` format.

**Files:**
- Modify: the existing VideOCR subtitle/export module, or create `server_cli/srt_output.py` if a wrapper is safer
- Create: `docs/srt-format.md`
- Create: `fixtures/expected_shape.srt`

**Steps:**

1. Confirm output is UTF-8.
2. Confirm milliseconds use commas.
3. Remove empty OCR results.
4. Normalize whitespace without altering Chinese characters.
5. Merge adjacent identical/near-identical cues using the existing threshold controls.
6. Prevent overlapping timestamps and clamp invalid cue ranges.
7. Preserve Traditional Chinese unless a future explicit normalization option is enabled.
8. Use a parser/validator to inspect generated SRT before reporting success.

**Verification:**

Run a generated SRT through a small validation command that checks numbering, timestamp syntax, monotonic timing, non-empty text, UTF-8 decoding, and absence of overlapping cues.

### Task 8: Add the CPU deployment service

**Objective:** Run the forked engine reproducibly on Capsule Corp without affecting the system Python.

**Files:**
- Create: `deploy/systemd/videocr-worker.service` or the engine-specific service only if a standalone worker is implemented
- Create: `deploy/environment.example`
- Create: `deploy/storage-layout.md`
- Create: `scripts/cleanup-job.sh`

**Steps:**

1. Create a dedicated non-root service user for extraction.
2. Create a dedicated storage root such as `/var/lib/subextractor/` with `uploads/`, `work/`, and `results/`.
3. Set restrictive permissions and keep the repository separate from job data.
4. Apply CPU/memory/task limits conservatively; do not let the first deployment starve Hermes or other services.
5. Start with one active worker and a maximum queue size of two.
6. Add cleanup for uploads, temporary frames, failed jobs, and stale results.
7. Keep the engine bound to localhost or invoked locally; do not expose a raw public OCR endpoint.

**Verification:**

```bash
systemctl --user status videocr-worker  # if user service is chosen
journalctl -u videocr-worker --no-pager -n 100
```

Also verify the service user can read a job input, write only to its job directory, and cannot access unrelated private files.

### Task 9: Benchmark one and two jobs

**Objective:** Determine the safe concurrency policy for the 2-vCPU, 3.6-GB VPS.

**Files:**
- Modify: `benchmarks/README.md`
- Create: `benchmarks/results/<date>-cpu-single.json`
- Create: `benchmarks/results/<date>-cpu-double.json`

**Steps:**

1. Run one representative Chinese extraction and record duration, peak RSS, average/peak CPU, load, and output quality.
2. Repeat with two independent jobs using separate job directories.
3. Check Hermes responsiveness and disk usage during the run.
4. Compare output quality and failure behavior.
5. Set the initial worker policy based on measurements, not assumptions.

**Acceptance target:**

- One job completes successfully.
- Chinese SRT output is readable and structurally valid.
- No orphaned FFmpeg/PaddleOCR processes remain.
- Peak memory remains within a safe margin.
- Two-job behavior is documented even if concurrency is disabled.

Default outcome if two jobs are too slow or resource-heavy: keep one active worker and allow the second request to remain queued.

### Task 10: Prepare the future FastAPI integration boundary

**Objective:** Document how the separate product backend will invoke the engine.

**Files:**
- Create: `docs/integration-contract.md`
- Create: `examples/job-request.json`
- Create: `examples/progress.jsonl`

**Document:**

- Command invocation.
- Allowed language/options.
- Job-directory layout.
- Progress event schema.
- Exit codes.
- Cancellation behavior.
- Result naming.
- Cleanup ownership.
- Maximum concurrent jobs.

The future FastAPI project should launch this CLI as a worker subprocess and expose its own authenticated API. It should not import private VideOCR modules unless a later benchmark proves that library integration is necessary.

---

## Acceptance criteria

The modification is complete only when all of the following are true:

- The fork builds/installs in an isolated Python 3.11 CPU environment.
- A real Chinese-subtitle video is processed on Capsule Corp.
- The command requires a valid crop and rejects unsupported languages.
- The output is a UTF-8 SRT with the same structural format as `cooking_raw_27.srt`.
- The output contains no empty cues or overlapping timestamps.
- Progress is available as valid JSONL events.
- Cancellation removes incomplete output and exits with a documented code.
- The process does not use GPU/CUDA or Google Lens.
- Temporary files are cleaned up after success, failure, and cancellation.
- Single-job and two-job resource measurements are recorded.
- The engine can be invoked by a future FastAPI worker without GUI dependencies.
- The fork retains upstream MIT attribution and documents modifications.

## Risks and decisions

### CPU performance

PaddleOCR CPU inference may be the bottleneck on the 2-vCPU VPS. Optimize workload first: manual crop, SSIM filtering, frame skipping, and OCR width limits. Do not replace the engine before measuring it.

### Chinese model selection

VideOCR's `ch` mode may include Chinese and English. Traditional Chinese handling and OpenCC normalization must remain explicit; accidental conversion would make the extracted text unsuitable for Han's review workflow.

### Progress accuracy

If upstream internals do not expose enough progress information, report progress by sampled video time rather than pretending OCR completion percentage is exact. Document the approximation.

### Upstream synchronization

Keep modifications small and isolated. Maintain an `upstream` remote and avoid broad GUI rewrites in the engine fork. Rebase/sync only after the current benchmark is reproducible.

### Security

Video files are untrusted. Never run the engine as root, never pass user input through a shell, restrict job paths, enforce file limits, and clean up temporary files.

## Verification command summary

```bash
# Static CLI contract
.venv/bin/videocr-engine --help
.venv/bin/videocr-engine extract --help

# Dependency health
.venv/bin/python -m pip check

# Real extraction
.venv/bin/videocr-engine extract \
  --input /path/to/fixture.mp4 \
  --output /tmp/videocr-output.srt \
  --language ch \
  --crop x,y,width,height

# Validate UTF-8 and SRT structure
.venv/bin/python scripts/validate_srt.py /tmp/videocr-output.srt

# Confirm no orphaned processes after completion/cancellation
pgrep -af 'ffmpeg|videocr|paddle' || true
```

The plan should be executed in order. The first implementation gate is the baseline CPU benchmark; no web backend or macOS client work should begin until the forked engine produces and validates a real Chinese SRT on the VPS.
