import mock
import tempfile
import shutil
import os
from mock import call
import unittest

from movie_runner import MovieRunner

class TestMovieRunner(unittest.TestCase):
    def setUp(self):
        self.post_patcher = mock.patch('utils.requests.post')
        self.mock_post = self.post_patcher.start()

        self.exists_patcher = mock.patch('movie_runner.os.path.exists')
        self.mock_exists = self.exists_patcher.start()

        self.getMoviePathByLocalPathAndRemotePath_patcher = mock.patch('path.Path.getMoviePathByLocalPathAndRemotePath')
        self.mock_getMoviePathByLocalPathAndRemotePath = self.getMoviePathByLocalPathAndRemotePath_patcher.start()

        self.requests_patcher = mock.patch('file.requests')
        self.mock_requests = self.requests_patcher.start()

        self.reencodeFilesInDirectory_patcher = mock.patch('movie_runner.reencodeFilesInDirectory')
        self.mock_reencodeFilesInDirectory = self.reencodeFilesInDirectory_patcher.start()
        self.mock_reencodeFilesInDirectory.return_value = [mock.MagicMock() for x in xrange(3)]

        self._getLocalMoviePaths_patcher = mock.patch('movie_runner.MovieRunner._getLocalMoviePaths')
        self.mock__getLocalMoviePaths = self._getLocalMoviePaths_patcher.start()

        self._getLocalMoviePathsSetting_patcher = mock.patch('movie_runner.MovieRunner._getLocalMoviePathsSetting')
        self.mock__getLocalMoviePathsSetting = self._getLocalMoviePathsSetting_patcher.start()


        self.movieRunner = MovieRunner()
        self.movieRunner._postMovie = mock.MagicMock()

    def tearDown(self):
        self.post_patcher.stop()
        self._getLocalMoviePathsSetting_patcher.stop()
        self._getLocalMoviePaths_patcher.stop()
        self.reencodeFilesInDirectory_patcher.stop()
        self.requests_patcher.stop()
        self.getMoviePathByLocalPathAndRemotePath_patcher.stop()
        self.exists_patcher.stop()

    @mock.patch('movie_runner.MovieRunner.postMovies')
    def test_run(self,
                 mock_postMovies):
        self.movieRunner.run()
        self.assertEquals(1, mock_postMovies.call_count)

    def test_postMovies(self):
        def gen_test_data(num):
            return [dict(results=[dict(pk=i)]) for i in xrange(1, num + 1)]

        self.mock_exists.return_value = True
        self.mock_getMoviePathByLocalPathAndRemotePath.side_effect = gen_test_data(5)
        self.mock__getLocalMoviePathsSetting.return_value = ['/path/to/movies']
        self.mock__getLocalMoviePaths.return_value = ['movie1', 'movie2', 'movie3']
        mock_json = mock.MagicMock()
        mock_json.json.return_value = dict(next=None,
                                           results=[{'filename': 'movie1',
                                                     'localpath': '/path/to/movies'},
                                                    {'filename': 'movie3',
                                                     'localpath': '/path/to/movies'}])

        self.mock_requests.get.return_value = mock_json
        self.movieRunner.postMovies()

        self.movieRunner._postMovie.assert_has_calls([call('movie2', 1)],
                                                      any_order=True)
        self.assertEqual(1, self.movieRunner._postMovie.call_count)

        self.mock_reencodeFilesInDirectory.assert_has_calls([call('/path/to/movies/movie2', 1, dryRun=False)],
                                                        any_order=True)
        self.assertEqual(1, self.mock_reencodeFilesInDirectory.call_count)

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
