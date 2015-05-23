from tv_runner import TvRunner
from movie_runner import MovieRunner

from log import LogFile
log = LogFile().getLogger()

def main():
    tvRunner = TvRunner()
    tvRunner.run()

    movieRunner = MovieRunner()
    movieRunner.run()

if __name__ == '__main__':
    main()
