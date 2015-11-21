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
    tvRunner = TvRunner()
    errors = tvRunner.run()

    movieRunner = MovieRunner()
    movieRunner.run()

    postData({}, MEDIAVIEWER_INFER_SCRAPERS_URL)

    if errors:
        log.error('Errors occured in the following files:')
        for error in errors:
            log.error(error)

    log.info('All done')

if __name__ == '__main__':
    main()
