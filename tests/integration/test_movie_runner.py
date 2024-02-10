import pytest
from movie_runner import MovieRunner, Movie


class BaseSettings:
    @pytest.fixture(autouse=True)
    def setUp(self,
              mocker,
              temp_directory,
              create_movie_directory,
              ):
        self._temp_directory = temp_directory
        mocker.patch('movie_runner.DOMAIN',
                     'http://mediaviewer:8000')
        self.local_paths = self._local_movie_paths()
        mocker.patch('movie_runner.LOCAL_MOVIE_PATHS',
                     self.local_paths)
        self.movie_dir, self.video_file = create_movie_directory(
            directory=self.local_paths[-1]
        )

    def _local_movie_paths(self):
        return [str(self._temp_directory)]


class TestRun(BaseSettings):
    def test_run(self):
        movie_runner = MovieRunner()
        movie_runner.run()
