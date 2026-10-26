# MediaConverter [![Build Status](https://travis-ci.org/kyokley/MediaConverter.svg)](https://travis-ci.org/kyokley/MediaConverter)
Convert media files to HTML5 streamable format

## Processing logs

Logs show pipeline steps, directory/file progress, skip reasons, elapsed time,
and publication results. Encoding reports media time and speed periodically;
multipart B2 uploads report confirmed parts and bytes. Progress uses ordinary
log lines, so it works in Docker logs and non-interactive Celery workers.

Standalone scripts default to `INFO`, with timestamps, severity, and logger names.
Set `MC_LOG_LEVEL=DEBUG` for diagnostic details, including API request timings.
API logs omit request payloads, response bodies, and URL credentials/query strings.
Logs still include local media paths and B2 destinations; treat them as private.

Compose workers default to `INFO` and use `MC_LOG_LEVEL` from the host:

```bash
MC_LOG_LEVEL=DEBUG docker compose up mediaconverter
docker compose logs -f mediaconverter
```

For workers started directly, set Celery's log level explicitly:

```bash
celery -A main worker --loglevel=INFO --concurrency=1
```

The production image also defaults to `--loglevel=info`. Override its command
to change the worker log level. Dry runs label planned work rather than reporting
successful uploads or publications. Encoding progress reports media time, not a
percentage or ETA; single-request uploads log their start and completion.
