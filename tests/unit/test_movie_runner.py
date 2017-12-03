import mock
import unittest

from movie_runner import MovieRunner

def gen_data(num):
    return [dict(results=[dict(pk=i)]) for i in xrange(1, num + 1)]

class TestPostMovies(unittest.TestCase):
    def setUp(self):
        self.LOCAL_MOVIE_PATHS_patcher = mock.patch('movie_runner.LOCAL_MOVIE_PATHS', ['/path/to/movies'])
        self.LOCAL_MOVIE_PATHS_patcher.start()

        self.promoteSubtitles_patcher = mock.patch('movie_runner.MovieRunner.promoteSubtitles')
        self.mock_promoteSubtitles = self.promoteSubtitles_patcher.start()

        self.Path_patcher = mock.patch('movie_runner.Path')
        self.mock_Path = self.Path_patcher.start()

        self.getMovieFileSet_patcher = mock.patch('movie_runner.File.getMovieFileSet')
        self.mock_getMovieFileSet = self.getMovieFileSet_patcher.start()

        self.exists_patcher = mock.patch('movie_runner.os.path.exists')
        self.mock_exists = self.exists_patcher.start()

        self.reencodeFilesInDirectory_patcher = mock.patch('movie_runner.reencodeFilesInDirectory')
        self.mock_reencodeFilesInDirectory = self.reencodeFilesInDirectory_patcher.start()

        self._getLocalMoviePaths_patcher = mock.patch('movie_runner.MovieRunner._getLocalMoviePaths')
        self.mock_getLocalMoviePaths = self._getLocalMoviePaths_patcher.start()

        self.log_patcher = mock.patch('movie_runner.log')
        self.mock_log = self.log_patcher.start()

        self._postMovie_patcher = mock.patch('movie_runner.MovieRunner._postMovie')
        self.mock_postMovie = self._postMovie_patcher.start()

        self.mock_exists.return_value = True
        self.mock_Path.getMoviePathByLocalPathAndRemotePath.side_effect = gen_data(5)
        self.mock_getMovieFileSet.return_value = set(['movie1', 'movie3'])
        self.mock_getLocalMoviePaths.return_value = ['movie1', 'movie2', 'movie3']
        self.mock_reencodeFilesInDirectory.return_value = None

        self.movieRunner = MovieRunner()

    def tearDown(self):
        self.LOCAL_MOVIE_PATHS_patcher.stop()
        self.Path_patcher.stop()
        self.getMovieFileSet_patcher.stop()
        self._getLocalMoviePaths_patcher.stop()
        self.reencodeFilesInDirectory_patcher.stop()
        self.exists_patcher.stop()
        self.promoteSubtitles_patcher.stop()
        self.log_patcher.stop()
        self._postMovie_patcher.stop()

    def test_postMovies(self):
        expected = None
        actual = self.movieRunner.postMovies()
        self.assertEqual(expected, actual)
        self.assertEqual(self.movieRunner.errors, [])

        self.mock_Path.assert_called_once_with('/path/to/movies', '/path/to/movies')
        self.mock_Path.return_value.postMovie.assert_called_once_with()
        self.mock_Path.getMoviePathByLocalPathAndRemotePath.assert_called_once_with('/path/to/movies',
                                                                                    '/path/to/movies')

        self.mock_log.info.assert_has_calls([mock.call('Found /path/to/movies/movie2'),
                                             mock.call('Starting re-encoding of /path/to/movies/movie2...'),
                                             mock.call('Posting /path/to/movies/movie2'),
                                             ])
        self.assertFalse(self.mock_log.error.called)

        self.mock_postMovie.assert_called_once_with('movie2', 1)
        self.mock_reencodeFilesInDirectory.assert_called_once_with('/path/to/movies/movie2')
        self.mock_promoteSubtitles.assert_called_once_with('/path/to/movies/movie2')

    def test_reencodeErrors(self):
        self.mock_reencodeFilesInDirectory.return_value = ['test_error']

        expected = None
        actual = self.movieRunner.postMovies()
        self.assertEqual(expected, actual)
        self.assertEqual(self.movieRunner.errors, ['test_error'])

        self.mock_Path.assert_called_once_with('/path/to/movies', '/path/to/movies')
        self.mock_Path.return_value.postMovie.assert_called_once_with()
        self.mock_Path.getMoviePathByLocalPathAndRemotePath.assert_called_once_with('/path/to/movies',
                                                                                    '/path/to/movies')

        self.mock_log.info.assert_has_calls([mock.call('Found /path/to/movies/movie2'),
                                             mock.call('Starting re-encoding of /path/to/movies/movie2...'),
                                             ])
        self.assertFalse(self.mock_log.error.called)

        self.assertFalse(self.mock_postMovie.called)
        self.mock_reencodeFilesInDirectory.assert_called_once_with('/path/to/movies/movie2')
        self.mock_promoteSubtitles.assert_called_once_with('/path/to/movies/movie2')

    def test_unhandledException(self):
        self.mock_reencodeFilesInDirectory.side_effect = Exception('Oh no! Something bad happened')

        self.assertRaises(Exception,
                          self.movieRunner.postMovies)

        self.mock_Path.assert_called_once_with('/path/to/movies', '/path/to/movies')
        self.mock_Path.return_value.postMovie.assert_called_once_with()
        self.mock_Path.getMoviePathByLocalPathAndRemotePath.assert_called_once_with('/path/to/movies',
                                                                                    '/path/to/movies')

        self.mock_log.info.assert_has_calls([mock.call('Found /path/to/movies/movie2'),
                                             mock.call('Starting re-encoding of /path/to/movies/movie2...'),
                                             ])
        self.mock_log.error.assert_has_calls([mock.call('Error processing /path/to/movies/movie2'),
                                              mock.call('Oh no! Something bad happened'),
                                              ])

        self.assertFalse(self.mock_postMovie.called)
        self.mock_reencodeFilesInDirectory.assert_called_once_with('/path/to/movies/movie2')
        self.mock_promoteSubtitles.assert_called_once_with('/path/to/movies/movie2')



class TestRun(unittest.TestCase):
    def setUp(self):
        self.postMovies_patcher = mock.patch('movie_runner.MovieRunner.postMovies')
        self.mock_postMovies = self.postMovies_patcher.start()

        self.debug_patcher = mock.patch('movie_runner.log.debug')
        self.mock_debug = self.debug_patcher.start()

        self.movieRunner = MovieRunner()
        self.errors = mock.MagicMock()
        self.movieRunner.errors = self.errors

    def tearDown(self):
        self.postMovies_patcher.stop()
        self.debug_patcher.stop()

    def test_run(self):
        expected = self.errors
        actual = self.movieRunner.run()

        self.assertEqual(expected, actual)
        self.mock_postMovies.assert_called_once_with()
        self.mock_debug.assert_called_once_with('Done running movies')
