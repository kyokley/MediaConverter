from celery import Celery

from log import LogFile
from movie_runner import MovieRunner
from settings import CELERY_VHOST, MEDIAVIEWER_INFER_SCRAPERS_URL, SEND_EMAIL
from tv_runner import TvRunner
from utils import postData, send_email

log = LogFile().getLogger()

app = Celery("tasks", broker="amqp://guest@localhost/%s" % CELERY_VHOST)


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


if __name__ == "__main__":
    main.delay()
