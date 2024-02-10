import pytest
import random
from pathlib import Path

from movie_runner import MovieRunner, Movie
from tv_runner import MediaFile


rand = random.SystemRandom()


class BaseSettings:
    @pytest.fixture(autouse=True)
    def setUp(self,
              mocker,
              temp_directory,
              create_movie_directory,
              ):
        self.media_file_size = rand.randint(1_000_000, 1_000_000_000)

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
            self.media_file_size)

        assert mf_resp['filename'] == self.video_file.name
        assert mf_resp['media_path'] == post_resp['pk']
        assert mf_resp['ismovie'] is True
        assert mf_resp['size'] == self.media_file_size

    def test_multiple_media_paths(self, create_movie_directory):
        self.video_files = []
        self.dirs = []
        movie = None

        for idx, dir_str in enumerate(self.local_paths):
            new_dir = Path(dir_str) / f'TestDir{idx}'

            movie_dir, video_file = create_movie_directory(
                directory=new_dir
            )

            self.video_files.append(video_file)
            self.dirs.append(movie_dir)

            resp = Movie.post_media_path(movie_dir, movie=movie)
            MediaFile.post_media_file(
                video_file.name,
                resp['pk'],
                self.media_file_size)

            movie = resp['movie']

            resp = Movie.get_movie(movie)
            media_path = resp['media_path']

            assert movie_dir == Path(media_path['path'])
