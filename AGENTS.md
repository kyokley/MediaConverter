# Project guidance

## What this project does

MediaConverter is a Python service that converts local movie and TV files into HTML5-streamable MP4 media. A Celery task in `main.py` runs the TV pipeline, then the movie pipeline. The runners discover media, coordinate MediaViewer API records and optional Backblaze B2 uploads, and call the FFmpeg conversion pipeline. This repository is a worker, not a web application.

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

- Use Python 3.10+ (Docker uses Python 3.12). Dependencies are locked in `uv.lock`; Docker images install with `uv`.
- `make ci-tests` builds the development image, starts Compose services, and runs pytest. CI uses this command. `make tests` runs the interactive variant. Both require Docker and Docker Compose.
- With local development dependencies installed, `pytest` runs the default suite. `pyproject.toml` disables sockets and excludes `tests/integration` by default. Run integration tests deliberately with `pytest tests/integration -o addopts=''`; these tests allow network access and may need external services.
- `devenv test` runs CI's formatting/hook checks. `make autoformat` runs Black inside the development container; devenv also configures Ruff checks and formatting.
- `make up` starts Compose services. `make exec` queues the main task in the running service. `make down` removes Compose volumes (`down -v`), so check for data before running it.

## Changes that need care

- Before version-control operations, check whether Jujutsu is available with `command -v jj`. Use `jj` when available; use `git` otherwise.
- `makeFileStreamable` in `convert.py` writes a temporary MP4 under `/tmp`, moves the result into the source directory, and removes the original by default. Preserve file safety and test changes to naming, subtitles, and cleanup with fixtures before processing real media.
- FFmpeg and `srt-vtt` are external executables. Prefer the Docker environment for media-dependent tests; inspect `Dockerfile` when changing codec/tool assumptions.
- Settings for broker, media roots, MediaViewer, mail, and B2 come from `MC_*` variables in `settings.py`. Do not commit secrets or machine-specific `local_settings.py` values. `settings.py` reads `MC_BROKER`, while the current Compose file sets `BROKER`; account for this mismatch when diagnosing worker connectivity.
- RabbitMQ 4.3 rejects transient non-exclusive queues by default. `main.py` sets Celery's `control_queue_exclusive` and `event_queue_exclusive` so remote-control and event queues remain nondurable but exclusive; keep worker mingle, gossip, and remote control enabled.
- Add or update focused unit/functional tests alongside behavior changes. Keep integration tests explicit because they are excluded from normal pytest runs.

## Keep this file current

When changing repository structure, entry points, commands, dependencies, configuration, test behavior, or operational hazards, update `AGENTS.md` in the same change. Check paths and commands against the current files rather than repeating outdated guidance; remove instructions that no longer apply.
