import os
import logging

from tv_runner import TvRunner
from movie_runner import MovieRunner
from settings import (
    MEDIAVIEWER_INFER_SCRAPERS_URL,
    SEND_EMAIL,
    CELERY_VHOST,
)
from utils import postData, send_email
from celery import Celery

log = logging.getLogger(__name__)

app = Celery("tasks", broker=f"{os.environ['BROKER']}/{CELERY_VHOST}")


@app.task(name="main.main", serializer="json")
def main():
    all_errors = []
    tvRunner = TvRunner()
    tv_errors = tvRunner.run()

    movieRunner = MovieRunner()
    movie_errors = movieRunner.run()

    postData({}, MEDIAVIEWER_INFER_SCRAPERS_URL)

    all_errors.extend(tv_errors)
    all_errors.extend(movie_errors)

    if all_errors:
        log.error("Errors occured in the following files:")
        for error in all_errors:
            log.error(error)

        if SEND_EMAIL:
            subject = "MC: Got some errors"
            message = "\n".join(all_errors)
            send_email(subject, message)

    log.info("All done")


@app.task(name='main.test')
def test_task():
    log.info('Test job ran successfully!')


if __name__ == "__main__":
    main.delay()
