import mock
import unittest

from movie_runner import MovieRunner


def gen_data(num):
    return [dict(results=[dict(pk=i)]) for i in range(1, num + 1)]


class TestPostMovies(unittest.TestCase):
    def setUp(self):
        self.LOCAL_MOVIE_PATHS_patcher = mock.patch(
            'movie_runner.LOCAL_MOVIE_PATHS', ['/path/to/movies'])
        self.LOCAL_MOVIE_PATHS_patcher.start()

        self.promoteSubtitles_patcher = mock.patch(
            'movie_runner.MovieRunner.promoteSubtitles')
        self.mock_promoteSubtitles = self.promoteSubtitles_patcher.start()

        self.Path_patcher = mock.patch('movie_runner.Path')
        self.mock_Path = self.Path_patcher.start()

        self.getMovieFileSet_patcher = mock.patch(
            'movie_runner.File.getMovieFileSet')
        self.mock_getMovieFileSet = self.getMovieFileSet_patcher.start()

        self.exists_patcher = mock.patch('movie_runner.os.path.exists')
        self.mock_exists = self.exists_patcher.start()

        self.reencodeFilesInDirectory_patcher = mock.patch(
            'movie_runner.reencodeFilesInDirectory')
        self.mock_reencodeFilesInDirectory = (
            self.reencodeFilesInDirectory_patcher.start())

        self._getLocalMoviePaths_patcher = mock.patch(
            'movie_runner.MovieRunner._getLocalMoviePaths')
        self.mock_getLocalMoviePaths = self._getLocalMoviePaths_patcher.start()

        self.log_patcher = mock.patch('movie_runner.log')
        self.mock_log = self.log_patcher.start()

        self._postMovie_patcher = mock.patch(
            'movie_runner.MovieRunner._postMovie')
        self.mock_postMovie = self._postMovie_patcher.start()

        self.mock_exists.return_value = True
        self.mock_Path.getMoviePathByLocalPathAndRemotePath.side_effect = (
            gen_data(5))
        self.mock_getMovieFileSet.return_value = set(['movie1', 'movie3'])
        self.mock_getLocalMoviePaths.return_value = ['movie1',
                                                     'movie2',
                                                     'movie3']
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

        self.mock_Path.assert_called_once_with(
            '/path/to/movies', '/path/to/movies')
        self.mock_Path.return_value.postMovie.assert_called_once_with()
        (self.mock_Path
         .getMoviePathByLocalPathAndRemotePath
         .assert_called_once_with('/path/to/movies',
                                  '/path/to/movies'))

        self.mock_log.info.assert_has_calls([
            mock.call('Found /path/to/movies/movie2'),
            mock.call('Starting re-encoding of /path/to/movies/movie2...'),
            mock.call('Posting /path/to/movies/movie2'),
        ])
        self.assertFalse(self.mock_log.error.called)

        self.mock_postMovie.assert_called_once_with('movie2', 1)
        self.mock_reencodeFilesInDirectory.assert_called_once_with(
            '/path/to/movies/movie2')
        self.mock_promoteSubtitles.assert_called_once_with(
            '/path/to/movies/movie2')

    def test_reencodeErrors(self):
        self.mock_reencodeFilesInDirectory.return_value = ['test_error']

        expected = None
        actual = self.movieRunner.postMovies()
        self.assertEqual(expected, actual)
        self.assertEqual(self.movieRunner.errors, ['test_error'])

        self.mock_Path.assert_called_once_with(
            '/path/to/movies', '/path/to/movies')
        self.mock_Path.return_value.postMovie.assert_called_once_with()
        (self.mock_Path
         .getMoviePathByLocalPathAndRemotePath
         .assert_called_once_with('/path/to/movies',
                                  '/path/to/movies'))

        self.mock_log.info.assert_has_calls([
            mock.call('Found /path/to/movies/movie2'),
            mock.call('Starting re-encoding of /path/to/movies/movie2...'),
        ])
        self.assertFalse(self.mock_log.error.called)

        self.assertFalse(self.mock_postMovie.called)
        self.mock_reencodeFilesInDirectory.assert_called_once_with(
            '/path/to/movies/movie2')
        self.mock_promoteSubtitles.assert_called_once_with(
            '/path/to/movies/movie2')

    def test_unhandledException(self):
        self.mock_reencodeFilesInDirectory.side_effect = Exception(
            'Oh no! Something bad happened')

        self.assertRaises(Exception,
                          self.movieRunner.postMovies)

        self.mock_Path.assert_called_once_with(
            '/path/to/movies', '/path/to/movies')
        self.mock_Path.return_value.postMovie.assert_called_once_with()
        (self.mock_Path
         .getMoviePathByLocalPathAndRemotePath
         .assert_called_once_with('/path/to/movies',
                                  '/path/to/movies'))

        self.mock_log.info.assert_has_calls([
            mock.call('Found /path/to/movies/movie2'),
            mock.call('Starting re-encoding of /path/to/movies/movie2...'),
        ])
        self.mock_log.error.assert_has_calls([
            mock.call('Error processing /path/to/movies/movie2'),
            mock.call('Oh no! Something bad happened'),
        ])

        self.assertFalse(self.mock_postMovie.called)
        self.mock_reencodeFilesInDirectory.assert_called_once_with(
            '/path/to/movies/movie2')
        self.mock_promoteSubtitles.assert_called_once_with(
            '/path/to/movies/movie2')


class TestRun(unittest.TestCase):
    def setUp(self):
        self.postMovies_patcher = mock.patch(
            'movie_runner.MovieRunner.postMovies')
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


class TestPromoteSubtitles(unittest.TestCase):
    def setUp(self):
        self.SUBTITLE_FILES_patcher = mock.patch('movie_runner.SUBTITLE_FILES',
                                                 ('English.srt', '2_Eng.srt'))
        self.SUBTITLE_FILES_patcher.start()

        self.exists_patcher = mock.patch('movie_runner.os.path.exists')
        self.mock_exists = self.exists_patcher.start()

        self.walk_patcher = mock.patch('movie_runner.os.walk')
        self.mock_walk = self.walk_patcher.start()

        self.rename_patcher = mock.patch('movie_runner.os.rename')
        self.mock_rename = self.rename_patcher.start()

        self.mock_walk.return_value = [('/path/to/movies/test_movie',
                                        ['Subs'],
                                        ['file1.mp4']),
                                       ('/path/to/movies/test_movie/Subs',
                                        [],
                                        ['2_Eng.srt']),
                                       ]

        self.mock_exists.return_value = True

    def tearDown(self):
        self.SUBTITLE_FILES_patcher.stop()
        self.rename_patcher.stop()
        self.walk_patcher.stop()
        self.exists_patcher.stop()

    def test_path_does_not_exist(self):
        self.mock_exists.return_value = False

        expected = None
        actual = MovieRunner.promoteSubtitles('/path/to/movies/test_movie')

        self.assertEqual(expected, actual)
        self.assertFalse(self.mock_walk.called)
        self.assertFalse(self.mock_rename.called)

    def test_2_Eng_exists_at_top_level(self):
        self.mock_walk.return_value = [('/path/to/movies/test_movie',
                                        [],
                                        ['file1.mp4', '2_Eng.srt']),
                                       ]

        expected = None
        actual = MovieRunner.promoteSubtitles('/path/to/movies/test_movie')

        self.assertEqual(expected, actual)
        self.mock_walk.assert_called_once_with('/path/to/movies/test_movie')
        self.assertFalse(self.mock_rename.called)

    def test_English_exists_at_top_level(self):
        self.mock_walk.return_value = [('/path/to/movies/test_movie',
                                        [],
                                        ['file1.mp4', 'English.srt']),
                                       ]

        expected = None
        actual = MovieRunner.promoteSubtitles('/path/to/movies/test_movie')

        self.assertEqual(expected, actual)
        self.mock_walk.assert_called_once_with('/path/to/movies/test_movie')
        self.assertFalse(self.mock_rename.called)

    def test_rename_2_Eng(self):
        expected = None
        actual = MovieRunner.promoteSubtitles('/path/to/movies/test_movie')

        self.assertEqual(expected, actual)
        self.mock_walk.assert_called_once_with('/path/to/movies/test_movie')
        self.mock_rename.assert_called_once_with(
            '/path/to/movies/test_movie/Subs/2_Eng.srt',
            '/path/to/movies/test_movie/2_Eng.srt')

    def test_rename_English(self):
        self.mock_walk.return_value = [('/path/to/movies/test_movie',
                                        ['Subs'],
                                        ['file1.mp4']),
                                       ('/path/to/movies/test_movie/Subs',
                                        [],
                                        ['English.srt']),
                                       ]

        expected = None
        actual = MovieRunner.promoteSubtitles('/path/to/movies/test_movie')

        self.assertEqual(expected, actual)
        self.mock_walk.assert_called_once_with('/path/to/movies/test_movie')
        self.mock_rename.assert_called_once_with(
            '/path/to/movies/test_movie/Subs/English.srt',
            '/path/to/movies/test_movie/English.srt')


class TestGetLocalMoviePaths(unittest.TestCase):
    def setUp(self):
        self.exists_patcher = mock.patch('movie_runner.os.path.exists')
        self.mock_exists = self.exists_patcher.start()

        self.listdir_patcher = mock.patch('movie_runner.os.listdir')
        self.mock_listdir = self.listdir_patcher.start()

        self.mock_exists.return_value = True

    def tearDown(self):
        self.listdir_patcher.stop()
        self.exists_patcher.stop()

    def test_path_does_not_exist(self):
        self.mock_exists.return_value = False

        expected = set()
        actual = MovieRunner._getLocalMoviePaths('test_path')

        self.assertEqual(expected, actual)
        self.mock_exists.assert_called_once_with('test_path')
        self.assertFalse(self.mock_listdir.called)

    def test_path_exists(self):
        expected = set(self.mock_listdir.return_value)
        actual = MovieRunner._getLocalMoviePaths('test_path')

        self.assertEqual(expected, actual)
        self.mock_exists.assert_called_once_with('test_path')
        self.mock_listdir.assert_called_once_with('test_path')


class TestPostMovie(unittest.TestCase):
    def setUp(self):
        self.MEDIAVIEWER_MOVIE_FILE_URL_patcher = mock.patch(
            'movie_runner.MEDIAVIEWER_MOVIE_FILE_URL', 'test_movie_file_url')
        self.MEDIAVIEWER_MOVIE_FILE_URL_patcher.start()

        self.postData_patcher = mock.patch('movie_runner.postData')
        self.mock_postData = self.postData_patcher.start()

        self.error_patcher = mock.patch('movie_runner.log.error')
        self.mock_error = self.error_patcher.start()

        self.movie_runner = MovieRunner()

    def tearDown(self):
        self.MEDIAVIEWER_MOVIE_FILE_URL_patcher.stop()
        self.postData_patcher.stop()
        self.error_patcher.stop()

    def test_invalid_name(self):
        expected = None
        actual = self.movie_runner._postMovie(None, 123)

        self.assertEqual(expected, actual)
        self.mock_error.assert_has_calls([
            mock.call('Invalid request'),
            mock.call('Filename: None Pathid: 123')])
        self.assertFalse(self.mock_postData.called)

    def test_invalid_pathid(self):
        expected = None
        actual = self.movie_runner._postMovie('test_name', 0)

        self.assertEqual(expected, actual)
        self.mock_error.assert_has_calls([
            mock.call('Invalid request'),
            mock.call('Filename: test_name Pathid: 0')])
        self.assertFalse(self.mock_postData.called)

    def test_valid(self):
        expected = None
        actual = self.movie_runner._postMovie('test_name', 123)

        self.assertEqual(expected, actual)
        self.assertFalse(self.mock_error.called)
        self.mock_postData.assert_called_once_with({'path': 123,
                                                    'filename': 'test_name',
                                                    'skip': 1,
                                                    'size': 0,
                                                    'finished': 1,
                                                    'streamable': True,
                                                    },
                                                   'test_movie_file_url')
