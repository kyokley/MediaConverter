import unittest
import mock
import tempfile
import shutil
import os

from path import Path

class TestPostMovie(unittest.TestCase):
    def setUp(self):
        self._post_patcher = mock.patch('path.Path._post')
        self.mock_post = self._post_patcher.start()

        self.path = Path('/path/to/local', '/path/to/remote')

    def tearDown(self):
        self._post_patcher.stop()

    def test_postMovie(self):
        expected = None
        actual = self.path.postMovie()

        self.assertEqual(expected, actual)
        self.mock_post.assert_called_once_with(useMovieURL=True)

class TestPostTVShow(unittest.TestCase):
    def setUp(self):
        self._post_patcher = mock.patch('path.Path._post')
        self.mock_post = self._post_patcher.start()

        self.path = Path('/path/to/local', '/path/to/remote')

    def tearDown(self):
        self._post_patcher.stop()

    def test_postTVShow(self):
        expected = None
        actual = self.path.postTVShow()

        self.assertEqual(expected, actual)
        self.mock_post.assert_called_once_with(useMovieURL=False)

class TestPost(unittest.TestCase):
    def setUp(self):
        self.postData_patcher = mock.patch('path.postData')
        self.mock_postData = self.postData_patcher.start()

        self.MEDIAVIEWER_MOVIE_PATH_URL_patcher = mock.patch('path.MEDIAVIEWER_MOVIE_PATH_URL', 'test_movie_url')
        self.MEDIAVIEWER_MOVIE_PATH_URL_patcher.start()

        self.MEDIAVIEWER_TV_PATH_URL_patcher = mock.patch('path.MEDIAVIEWER_TV_PATH_URL', 'test_tv_url')
        self.MEDIAVIEWER_TV_PATH_URL_patcher.start()

        self.SERVER_NAME_patcher = mock.patch('path.SERVER_NAME', 'test_server_name')
        self.SERVER_NAME_patcher.start()

        self.path = Path('/path/to/local', '/path/to/remote')

    def tearDown(self):
        self.postData_patcher.stop()
        self.MEDIAVIEWER_TV_PATH_URL_patcher.stop()
        self.MEDIAVIEWER_MOVIE_PATH_URL_patcher.stop()
        self.SERVER_NAME_patcher.stop()

    def test_useMovieURL(self):
        expected = None
        actual = self.path._post(useMovieURL=True)

        expected_values = {'localpath': '/path/to/local',
                           'remotepath': '/path/to/remote',
                           'skip': False,
                           'server': 'test_server_name',
                           }

        self.assertEqual(expected, actual)
        self.mock_postData.assert_called_once_with(expected_values, 'test_movie_url')

    def test_not_useMovieURL(self):
        expected = None
        actual = self.path._post(useMovieURL=False)

        expected_values = {'localpath': '/path/to/local',
                           'remotepath': '/path/to/remote',
                           'skip': False,
                           'server': 'test_server_name',
                           }

        self.assertEqual(expected, actual)
        self.mock_postData.assert_called_once_with(expected_values, 'test_tv_url')

class TestGetPaths(unittest.TestCase):
    def setUp(self):
        self.MEDIAVIEWER_MOVIE_PATH_URL_patcher = mock.patch('path.MEDIAVIEWER_MOVIE_PATH_URL', 'test_movie_url')
        self.MEDIAVIEWER_MOVIE_PATH_URL_patcher.start()

        self.MEDIAVIEWER_TV_PATH_URL_patcher = mock.patch('path.MEDIAVIEWER_TV_PATH_URL', 'test_tv_url')
        self.MEDIAVIEWER_TV_PATH_URL_patcher.start()

        self.VERIFY_REQUESTS_patcher = mock.patch('path.VERIFY_REQUESTS', True)
        self.VERIFY_REQUESTS_patcher.start()

        self.WAITER_USERNAME_patcher = mock.patch('path.WAITER_USERNAME', 'test_waiter_username')
        self.WAITER_USERNAME_patcher.start()

        self.WAITER_PASSWORD_patcher = mock.patch('path.WAITER_PASSWORD', 'test_waiter_password')
        self.WAITER_PASSWORD_patcher.start()

        self.get_patcher = mock.patch('path.requests.get')
        self.mock_get = self.get_patcher.start()

        self.path = Path('/path/to/local', '/path/to/remote')
        self.mock_get.return_value.json.side_effect = [{'results': [{'localpath': 'some.local.path',
                                                                     'pk': 123},
                                                                    {'localpath': 'another.local.path',
                                                                     'pk': 124},
                                                                    ],
                                                        'next': 'next.url'},
                                                       {'results': [{'localpath': 'some.local.path',
                                                                     'pk': 125}],
                                                        'next': None}]

    def tearDown(self):
        self.mock_get = self.get_patcher.stop()
        self.WAITER_PASSWORD_patcher.stop()
        self.WAITER_USERNAME_patcher.stop()
        self.VERIFY_REQUESTS_patcher.stop()
        self.MEDIAVIEWER_TV_PATH_URL_patcher.stop()
        self.MEDIAVIEWER_MOVIE_PATH_URL_patcher.stop()

    def test_getMovies(self):
        expected = {'some.local.path': set([123, 125]),
                    'another.local.path': set([124])}
        actual = self.path._getPaths(getMovies=True)

        self.assertEqual(expected, actual)
        self.mock_get.assert_has_calls([mock.call('test_movie_url',
                                                  verify=True,
                                                  auth=('test_waiter_username', 'test_waiter_password')),
                                        mock.call().raise_for_status(),
                                        mock.call().json(),
                                        mock.call('next.url',
                                                  verify=True,
                                                  auth=('test_waiter_username', 'test_waiter_password')),
                                        mock.call().raise_for_status(),
                                        mock.call().json(),
                                       ])

    def test_getTVShows(self):
        expected = {'some.local.path': set([123, 125]),
                    'another.local.path': set([124])}
        actual = self.path._getPaths(getMovies=False)

        self.assertEqual(expected, actual)
        self.mock_get.assert_has_calls([mock.call('test_tv_url',
                                                  verify=True,
                                                  auth=('test_waiter_username', 'test_waiter_password')),
                                        mock.call().raise_for_status(),
                                        mock.call().json(),
                                        mock.call('next.url',
                                                  verify=True,
                                                  auth=('test_waiter_username', 'test_waiter_password')),
                                        mock.call().raise_for_status(),
                                        mock.call().json(),
                                       ])

class TestGetTVPaths(unittest.TestCase):
    def setUp(self):
        self._getPaths_patcher = mock.patch('path.Path._getPaths')
        self.mock_getPaths = self._getPaths_patcher.start()

        self.path = Path('/path/to/local', '/path/to/remote')

    def tearDown(self):
        self._getPaths_patcher.stop()

    def test_getTVPaths(self):
        expected = self.mock_getPaths.return_value
        actual = self.path.getTVPaths()

        self.assertEqual(expected, actual)
        self.mock_getPaths.assert_called_once_with(getMovies=False)

class TestGetMoviePaths(unittest.TestCase):
    def setUp(self):
        self._getPaths_patcher = mock.patch('path.Path._getPaths')
        self.mock_getPaths = self._getPaths_patcher.start()

        self.path = Path('/path/to/local', '/path/to/remote')

    def tearDown(self):
        self._getPaths_patcher.stop()

    def test_getTVPaths(self):
        expected = self.mock_getPaths.return_value
        actual = self.path.getMoviePaths()

        self.assertEqual(expected, actual)
        self.mock_getPaths.assert_called_once_with(getMovies=True)

class TestGetLocalPaths(unittest.TestCase):
    def setUp(self):
        self.LOCAL_TV_SHOWS_PATHS_patcher = mock.patch('path.LOCAL_TV_SHOWS_PATHS', 'test_local_tv_path')
        self.LOCAL_TV_SHOWS_PATHS_patcher.start()

        self.LOCAL_MOVIE_PATHS_patcher = mock.patch('path.LOCAL_MOVIE_PATHS', 'test_local_movie_path')
        self.LOCAL_MOVIE_PATHS_patcher.start()

        self._buildLocalPaths_patcher = mock.patch('path.Path._buildLocalPaths')
        self.mock_buildLocalPaths = self._buildLocalPaths_patcher.start()

    def tearDown(self):
        self.LOCAL_MOVIE_PATHS_patcher.stop()
        self.LOCAL_TV_SHOWS_PATHS_patcher.stop()
        self._buildLocalPaths_patcher.stop()

    def test_getLocalMovies(self):
        expected = self.mock_buildLocalPaths.return_value
        actual = Path._getLocalPaths(getMovies=True)

        self.assertEqual(expected, actual)
        self.mock_buildLocalPaths.assert_called_once_with('test_local_movie_path')

    def test_getLocalTVShows(self):
        expected = self.mock_buildLocalPaths.return_value
        actual = Path._getLocalPaths(getMovies=False)

        self.assertEqual(expected, actual)
        self.mock_buildLocalPaths.assert_called_once_with('test_local_tv_path')

class TestBuildLocalPaths(unittest.TestCase):
    def setUp(self):
        self.error_patcher = mock.patch('path.log.error')
        self.mock_error = self.error_patcher.start()

        self.exists_patcher = mock.patch('path.os.path.exists')
        self.mock_exists = self.exists_patcher.start()

        self.listdir_patcher = mock.patch('path.os.listdir')
        self.mock_listdir = self.listdir_patcher.start()

    def tearDown(self):
        self.error_patcher.stop()
        self.listdir_patcher.stop()
        self.exists_patcher.stop()

    def test_buildLocalPaths(self):
        test_paths = ['file_path1',
                      'file_path2',
                      'file_path3']

        self.mock_exists.side_effect = [True, False, True]
        self.mock_listdir.side_effect = [('listdir_path1',
                                          'listdir_path2'),
                                         ('listdir_path3',
                                          'listdir_path4'),
                                         ]

        expected = set(['file_path1/listdir_path1',
                        'file_path1/listdir_path2',
                        'file_path3/listdir_path3',
                        'file_path3/listdir_path4',
                        ])
        actual = Path._buildLocalPaths(test_paths)

        self.assertEqual(expected, actual)
        self.mock_exists.assert_has_calls([mock.call('file_path1'),
                                           mock.call('file_path2'),
                                           mock.call('file_path3'),
                                           ])
        self.mock_error.assert_called_once_with('file_path2 does not exist. Continuing...')
        self.mock_listdir.assert_has_calls([mock.call('file_path1'),
                                            mock.call('file_path3'),
                                            ])

class TestGetLocalPathsFunctional(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.path = Path('localpath', 'remotepath')

    def tearDown(self):
        shutil.rmtree(self.temp_dir)

    def test_path_does_not_exist(self):
        filepath = os.path.join(self.temp_dir, 'test_file')
        expected = set()
        actual = self.path._buildLocalPaths([filepath])
        self.assertEqual(expected, actual)

    def test_paths_exist(self):
        files = set([tempfile.mkstemp(dir=self.temp_dir)[1]
                    for i in xrange(3)])
        expected = files
        actual = self.path._buildLocalPaths([self.temp_dir])
        self.assertEqual(expected, actual)
