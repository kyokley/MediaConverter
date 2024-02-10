import pytest
from movie_runner import MovieRunner, Movie
from tv_runner import MediaFile


class BaseSettings:
    @pytest.fixture(autouse=True)
    def setUp(self,
              mocker,
              temp_directory,
              create_movie_directory,
              ):
        self._temp_directory = temp_directory
        mocker.patch('tv_runner.DOMAIN',
                     'http://mediaviewer:8000')
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


class TestGetMediaPath(BaseSettings):
    def test_get_media_path(self):
        post_resp = Movie.post_media_path(self.movie_dir)
        assert str(self.movie_dir) == post_resp['path']

        get_resp = Movie.get_media_path(post_resp['pk'])
        assert get_resp == post_resp


class TestGetAllMovies(BaseSettings):
    def test_get_all_movies(self):
        post_resp = Movie.post_media_path(self.movie_dir)
        resp = Movie.get_all_movies()
        assert self.movie_dir in resp
        assert post_resp['pk'] in resp[self.movie_dir]['pks']


class TestPostMediaFile(BaseSettings):
    def _local_movie_paths(self):
        return [
            str(self._temp_directory / f'{x}')
            for x in range(3)
        ]

    def test_post_media_file(self):
        post_resp = Movie.post_media_path(self.movie_dir)
        media_path_id = post_resp['pk']

        mf_resp = MediaFile.post_media_file(
            self.video_file.name,
            media_path_id,
            123123)
