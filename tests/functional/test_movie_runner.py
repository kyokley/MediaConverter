import tempfile
import os
import shutil
import pytest

from pathlib import Path as PathlibPath

from movie_runner import MovieRunner


class TestGetLocalMoviePathsFunctional:
    @pytest.fixture(autouse=True)
    def setUp(self):
        self.temp_dir = PathlibPath(tempfile.mkdtemp())
        self.movieRunner = MovieRunner()

        yield
        shutil.rmtree(self.temp_dir)

    def test_path_does_not_exist(self):
        path_name = self.temp_dir / "test_file"
        expected = set()
        actual = self.movieRunner._getLocalMoviePaths(path_name)
        assert expected == actual

    def test_path_exists(self):
        files = set([tempfile.mkstemp(dir=self.temp_dir)[1] for i in range(3)])
        expected = set([os.path.basename(x) for x in files])
        actual = self.movieRunner._getLocalMoviePaths(self.temp_dir)
        assert expected == actual
