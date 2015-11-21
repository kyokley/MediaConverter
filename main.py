from tv_runner import TvRunner
from movie_runner import MovieRunner
from settings import MEDIAVIEWER_INFER_SCRAPERS_URL
from utils import postData
from celery import Celery

from log import LogFile
log = LogFile().getLogger()

app = Celery('tasks', broker='amqp://guest@localhost//')

@app.task
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
        log.error('Errors occured in the following files:')
        for error in all_errors:
            log.error(error)

    log.info('All done')

if __name__ == '__main__':
    main()
