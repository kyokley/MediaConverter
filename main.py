from tv_runner import TvRunner
from movie_runner import MovieRunner
from settings import MEDIAVIEWER_INFER_SCRAPERS_URL
from utils import postData

from log import LogFile
log = LogFile().getLogger()

def main():
    tvRunner = TvRunner()
    tvRunner.run()

    movieRunner = MovieRunner()
    movieRunner.run()

    postData({}, MEDIAVIEWER_INFER_SCRAPERS_URL)

if __name__ == '__main__':
    main()
