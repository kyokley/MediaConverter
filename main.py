import logging
from time import monotonic

from tv_runner import TvRunner
from movie_runner import MovieRunner
from settings import (
    SEND_EMAIL,
    CELERY_VHOST,
    BROKER,
    LOG_FORMAT,
)
from utils import send_email
from celery import Celery

log = logging.getLogger(__name__)

app = Celery("tasks", broker=f"{BROKER}/{CELERY_VHOST}")
app.conf.control_queue_exclusive = True
app.conf.event_queue_exclusive = True
app.conf.worker_log_format = LOG_FORMAT
app.conf.worker_task_log_format = (
    "%(asctime)s %(levelname)s [%(name)s/%(processName)s] "
    "%(task_name)s[%(task_id)s]: %(message)s"
)


@app.task(name="main.main", serializer="json")
def main():
    started = monotonic()
    log.info("Media processing started: pipelines=2")
    all_errors = []
    phase = "TV pipeline"
    try:
        log.info("[1/2] TV pipeline started")
        phase_started = monotonic()
        tvRunner = TvRunner()
        tv_errors = tvRunner.run()
        log.info(
            "[1/2] TV pipeline completed: errors=%d elapsed=%.1fs",
            len(tv_errors),
            monotonic() - phase_started,
        )

        phase = "Movie pipeline"
        log.info("[2/2] Movie pipeline started")
        phase_started = monotonic()
        movieRunner = MovieRunner()
        movie_errors = movieRunner.run()
        log.info(
            "[2/2] Movie pipeline completed: errors=%d elapsed=%.1fs",
            len(movie_errors),
            monotonic() - phase_started,
        )
    except Exception:
        log.exception(
            "Media processing failed during %s: elapsed=%.1fs",
            phase,
            monotonic() - started,
        )
        raise

    all_errors.extend(tv_errors)
    all_errors.extend(movie_errors)

    if all_errors:
        log.error("Processing errors:")
        for error in all_errors:
            log.error(error)

        if SEND_EMAIL:
            subject = "MC: Got some errors"
            message = "\n".join(all_errors)
            send_email(subject, message)

    summary_log = log.warning if all_errors else log.info
    summary_log(
        "Media processing completed: tv_errors=%d movie_errors=%d elapsed=%.1fs",
        len(tv_errors),
        len(movie_errors),
        monotonic() - started,
    )


@app.task(name="main.test")
def test_task():
    log.info("Test job ran successfully!")


if __name__ == "__main__":
    main.delay()
