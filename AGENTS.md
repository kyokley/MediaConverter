# Project guidance

## What this project does

MediaConverter is a Python service that converts local movie and TV files into HTML5-streamable MP4 media. A Celery task in `main.py` runs the TV pipeline, then the movie pipeline. The runners discover media, coordinate MediaViewer API records and Backblaze B2 uploads, and call the FFmpeg conversion pipeline. B2 storage is required; there is no local-only publication mode. This repository is a worker, not a web application.

## Where to work

- `main.py`: Celery app, processing task, and error reporting.
- `tv_runner.py`, `movie_runner.py`: discovery and per-library processing.
- `convert.py`: codec detection, FFmpeg encoding, subtitle extraction/conversion, and source replacement.
- `utils.py`: shared media, path, HTTP/API, email, and subtitle helpers.
- `b2.py`: Backblaze B2 integration.
- `settings.py`: defaults and `MC_*` environment settings; optional `local_settings.py` overrides them.
- `tests/unit/`, `tests/functional/`, `tests/integration/`: test suites; shared fixtures and sample media live in `tests/conftest.py` and `tests/data/`.
- `Dockerfile`, `docker-compose.yml`, `Makefile`, `devenv.nix`: container runtime and developer workflows.

## Run and verify

- Before considering any code changes complete, run the test suite and formatting checks using the commands below and confirm both pass. If either check fails or cannot run, report the failure or blocker and do not consider the changes complete.
- Use Python 3.10+ (Docker uses Python 3.12). Dependencies are locked in `uv.lock`; Docker images install with `uv`.
- `make ci-tests` builds the development image, starts Compose services, and runs pytest. CI uses this command. `make tests` runs the interactive variant. Both require Docker and Docker Compose.
- With local development dependencies installed, `pytest` runs the default suite. `pyproject.toml` disables sockets and excludes `tests/integration` by default. Run integration tests deliberately with `pytest tests/integration -o addopts=''`; these tests allow network access and may need external services.
- `devenv test` runs CI's formatting/hook checks. `make autoformat` runs Black inside the development container; devenv also configures Ruff checks and formatting.
- `make up` starts Compose services. `make exec` queues the main task in the running service. `make down` removes Compose volumes (`down -v`), so check for data before running it.

## Changes that need care

- Before version-control operations, check whether Jujutsu is available with `command -v jj`. Use `jj` when available; use `git` otherwise.
- `makeFileStreamable` in `convert.py` writes a temporary MP4 under `/tmp`, moves the result into the source directory, and removes the original by default. Preserve file safety and test changes to naming, subtitles, and cleanup with fixtures before processing real media.
- Movie discovery expects one directory per movie under each configured movie root. It ignores loose files, including video files; directory symlinks remain eligible.
- B2 upload keys use MediaViewer's returned `bucket` and versioned, server-owned opaque `b2_upload_prefix`, followed by a generated UUID filename. Consume the prefix unchanged; never derive a B2 key directory from a MediaPath PK, real filename, or URI basename. Legacy prefixes may be flat (for example, `archive/42/`); v2 prefixes use exactly three zero-padded 3-digit MediaPath PK components (IDs `1`–`999999999`, with at most 1,000 child ID directories per generated level), such as `001/234/567/` for PK `1234567`. Keep the logical MediaPath URI unchanged for mapping and identity.
- B2 movie MediaPaths are created before upload without a filename. MediaFile publication supplies the original converted filename and UUID only after video and subtitles upload successfully; incomplete B2 movie paths remain retryable.
- TV and movie runners remove each uploaded local video only after video upload, subtitle uploads, and MediaFile publication succeed. Failures preserve that upload file for retry; deduped files and subtitle sidecars are not cleaned up by this step.
- `B2Client.upload_file` retries HTTP errors for up to three total attempts, including single-file and multipart uploads. Only the final failed attempt reaches runner error handling and failure email; other exception types still fail immediately.
- TV uploads use an existing B2 MediaPath's returned bucket, upload prefix, and PK; when multiple distinct destinations exist, the configured URI must match one or processing fails rather than choosing arbitrarily.
- Unsorted TV files preserve inferred B2 URIs and map inferred local paths through the configured B2 bucket and prefix. Processing does not require a local show directory. Encoded outputs remain in the unsorted directory for upload retries.
- Subtitle discovery matches adjacent SRT/VTT sidecars to video basenames with delimiter boundaries, supports generated encoded names and case-insensitive extensions, and uploads UUID-named VTT objects before MediaFile publication. Generic English sidecars are accepted only for an unambiguous single-video directory.
- B2 TV and movie runs load a complete global MediaViewer filename inventory from paginated TV and movie MediaPath endpoints before processing. Exact logical filename matches skip upload; incomplete inventory reads fail closed.
- FFmpeg and `srt-vtt` are external executables. Prefer the Docker environment for media-dependent tests; inspect `Dockerfile` when changing codec/tool assumptions.
- Settings for broker, media roots, MediaViewer, mail, and B2 come from `MC_*` variables in `settings.py`. Do not commit secrets or machine-specific `local_settings.py` values. `settings.py` reads `MC_BROKER`, while the current Compose file sets `BROKER`; account for this mismatch when diagnosing worker connectivity.
- RabbitMQ 4.3 rejects transient non-exclusive queues by default. `main.py` sets Celery's `control_queue_exclusive` and `event_queue_exclusive` so remote-control and event queues remain nondurable but exclusive; keep worker mingle, gossip, and remote control enabled.
- Logging defaults to timestamped `INFO` for standalone scripts; `MC_LOG_LEVEL` selects the level. Compose passes this setting to Celery's `--loglevel`; directly launched workers must set `--loglevel` explicitly. `main.py` configures worker/task formats with logger and task context. Keep routine API diagnostics at `DEBUG`, omit payloads/response bodies and URL credentials/query strings, and preserve progress output at `INFO`. Media paths and B2 destinations remain private log content; see `README.md`.
- Add or update focused unit/functional tests alongside behavior changes. Keep integration tests explicit because they are excluded from normal pytest runs.

## Keep this file current

When changing repository structure, entry points, commands, dependencies, configuration, test behavior, or operational hazards, update `AGENTS.md` in the same change. Check paths and commands against the current files rather than repeating outdated guidance; remove instructions that no longer apply.
