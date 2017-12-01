import mock
import tempfile
import shutil
import os
from mock import call
import unittest

from movie_runner import MovieRunner

class TestMovieRunner(unittest.TestCase):
    def setUp(self):
        self.movieRunner = MovieRunner()
        self.movieRunner._postMovie = mock.MagicMock()

    @mock.patch('movie_runner.MovieRunner.postMovies')
    def test_run(self,
                 mock_postMovies):
        self.movieRunner.run()
        self.assertEquals(1, mock_postMovies.call_count)

    @mock.patch('utils.requests.post')
    @mock.patch('movie_runner.os.path.exists')
    @mock.patch('path.Path.getMoviePathByLocalPathAndRemotePath')
    @mock.patch('file.requests')
    @mock.patch('movie_runner.reencodeFilesInDirectory')
    @mock.patch('movie_runner.MovieRunner._getLocalMoviePaths')
    @mock.patch('movie_runner.MovieRunner._getLocalMoviePathsSetting')
    def test_postMovies(self,
                        mock_getLocalMoviePathsSetting,
                        mock_getLocalMoviePaths,
                        mock_reencodeFilesInDirectory,
                        mock_requests,
                        mock_getMoviePathByLocalPathAndRemotePath,
                        mock_exists,
                        mock_requestsPost):
        def gen_test_data(num):
            return [dict(results=[dict(pk=i)]) for i in xrange(1, num + 1)]

        mock_exists.return_value = True
        mock_getMoviePathByLocalPathAndRemotePath.side_effect = gen_test_data(5)
        mock_getLocalMoviePathsSetting.return_value = ['/path/to/movies']
        mock_getLocalMoviePaths.return_value = ['movie1', 'movie2', 'movie3']
        mock_reencodeFilesInDirectory.return_value = None
        mock_json = mock.MagicMock()
        mock_json.json.return_value = dict(next=None,
                                           results=[{'filename': 'movie1',
                                                     'localpath': '/path/to/movies'},
                                                    {'filename': 'movie3',
                                                     'localpath': '/path/to/movies'}])

        mock_requests.get.return_value = mock_json
        self.movieRunner.postMovies()

        self.movieRunner._postMovie.assert_has_calls([call('movie2', 1)],
                                                      any_order=True)
        self.assertEqual(1, self.movieRunner._postMovie.call_count)

        mock_reencodeFilesInDirectory.assert_has_calls([call('/path/to/movies/movie2')],
                                                        any_order=True)
        self.assertEqual(1, mock_reencodeFilesInDirectory.call_count)

class TestgetLocalMoviePathsFunctional(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.movieRunner = MovieRunner()

    def tearDown(self):
        shutil.rmtree(self.temp_dir)

    def test_path_does_not_exist(self):
        path_name = os.path.join(self.temp_dir, 'test_file')
        expected = set()
        actual = self.movieRunner._getLocalMoviePaths(path_name)
        self.assertEqual(expected, actual)

    def test_path_exists(self):
        files = set([tempfile.mkstemp(dir=self.temp_dir)[1]
                    for i in xrange(3)])
        expected = set([os.path.basename(x) for x in files])
        actual = self.movieRunner._getLocalMoviePaths(self.temp_dir)
        self.assertEqual(expected, actual)
