import tempfile
import os
import unittest
import shutil

from movie_runner import MovieRunner


class TestgetLocalMoviePathsFunctional(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.movieRunner = MovieRunner()

    def tearDown(self):
        shutil.rmtree(self.temp_dir)

    def test_path_does_not_exist(self):
        path_name = os.path.join(self.temp_dir, "test_file")
        expected = set()
        actual = self.movieRunner._getLocalMoviePaths(path_name)
        self.assertEqual(expected, actual)

    def test_path_exists(self):
        files = set([tempfile.mkstemp(dir=self.temp_dir)[1] for i in xrange(3)])
        expected = set([os.path.basename(x) for x in files])
        actual = self.movieRunner._getLocalMoviePaths(self.temp_dir)
        self.assertEqual(expected, actual)
