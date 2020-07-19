import unittest

import mock

from path import Path


class TestPostMovie(unittest.TestCase):
    def setUp(self):
        self._post_patcher = mock.patch("path.Path._post")
        self.mock_post = self._post_patcher.start()

        self.path = Path("/path/to/local", "/path/to/remote")

    def tearDown(self):
        self._post_patcher.stop()

    def test_postMovie(self):
        expected = None
        actual = self.path.postMovie()

        self.assertEqual(expected, actual)
        self.mock_post.assert_called_once_with(useMovieURL=True)


class TestPostTVShow(unittest.TestCase):
    def setUp(self):
        self._post_patcher = mock.patch("path.Path._post")
        self.mock_post = self._post_patcher.start()

        self.path = Path("/path/to/local", "/path/to/remote")

    def tearDown(self):
        self._post_patcher.stop()

    def test_postTVShow(self):
        expected = None
        actual = self.path.postTVShow()

        self.assertEqual(expected, actual)
        self.mock_post.assert_called_once_with(useMovieURL=False)


class TestPost(unittest.TestCase):
    def setUp(self):
        self.postData_patcher = mock.patch("path.postData")
        self.mock_postData = self.postData_patcher.start()

        self.MEDIAVIEWER_MOVIE_PATH_URL_patcher = mock.patch(
            "path.MEDIAVIEWER_MOVIE_PATH_URL", "test_movie_url"
        )
        self.MEDIAVIEWER_MOVIE_PATH_URL_patcher.start()

        self.MEDIAVIEWER_TV_PATH_URL_patcher = mock.patch(
            "path.MEDIAVIEWER_TV_PATH_URL", "test_tv_url"
        )
        self.MEDIAVIEWER_TV_PATH_URL_patcher.start()

        self.SERVER_NAME_patcher = mock.patch("path.SERVER_NAME", "test_server_name")
        self.SERVER_NAME_patcher.start()

        self.path = Path("/path/to/local", "/path/to/remote")

    def tearDown(self):
        self.postData_patcher.stop()
        self.MEDIAVIEWER_TV_PATH_URL_patcher.stop()
        self.MEDIAVIEWER_MOVIE_PATH_URL_patcher.stop()
        self.SERVER_NAME_patcher.stop()

    def test_useMovieURL(self):
        expected = None
        actual = self.path._post(useMovieURL=True)

        expected_values = {
            "localpath": "/path/to/local",
            "remotepath": "/path/to/remote",
            "skip": False,
            "server": "test_server_name",
        }

        self.assertEqual(expected, actual)
        self.mock_postData.assert_called_once_with(expected_values, "test_movie_url")

    def test_not_useMovieURL(self):
        expected = None
        actual = self.path._post(useMovieURL=False)

        expected_values = {
            "localpath": "/path/to/local",
            "remotepath": "/path/to/remote",
            "skip": False,
            "server": "test_server_name",
        }

        self.assertEqual(expected, actual)
        self.mock_postData.assert_called_once_with(expected_values, "test_tv_url")


class TestGetPaths(unittest.TestCase):
    def setUp(self):
        self.MEDIAVIEWER_MOVIE_PATH_URL_patcher = mock.patch(
            "path.MEDIAVIEWER_MOVIE_PATH_URL", "test_movie_url"
        )
        self.MEDIAVIEWER_MOVIE_PATH_URL_patcher.start()

        self.MEDIAVIEWER_TV_PATH_URL_patcher = mock.patch(
            "path.MEDIAVIEWER_TV_PATH_URL", "test_tv_url"
        )
        self.MEDIAVIEWER_TV_PATH_URL_patcher.start()

        self.VERIFY_REQUESTS_patcher = mock.patch("path.VERIFY_REQUESTS", True)
        self.VERIFY_REQUESTS_patcher.start()

        self.WAITER_USERNAME_patcher = mock.patch(
            "path.WAITER_USERNAME", "test_waiter_username"
        )
        self.WAITER_USERNAME_patcher.start()

        self.WAITER_PASSWORD_patcher = mock.patch(
            "path.WAITER_PASSWORD", "test_waiter_password"
        )
        self.WAITER_PASSWORD_patcher.start()

        self.BASE_PATH_patcher = mock.patch("path.BASE_PATH", "")
        self.BASE_PATH_patcher.start()

        self.get_patcher = mock.patch("path.requests.get")
        self.mock_get = self.get_patcher.start()

        self.path = Path("/path/to/local", "/path/to/remote")
        self.mock_get.return_value.json.side_effect = [
            {
                "results": [
                    {
                        "localpath": "some.local.path",
                        "remotepath": "some.local.path",
                        "pk": 123,
                        "finished": False,
                    },
                    {
                        "localpath": "another.local.path",
                        "remotepath": "another.local.path",
                        "pk": 124,
                        "finished": False,
                    },
                ],
                "next": "next.url",
            },
            {
                "results": [
                    {
                        "localpath": "some.local.path",
                        "remotepath": "some.local.path",
                        "pk": 125,
                        "finished": False,
                    }
                ],
                "next": None,
            },
        ]

    def tearDown(self):
        self.mock_get = self.get_patcher.stop()
        self.WAITER_PASSWORD_patcher.stop()
        self.WAITER_USERNAME_patcher.stop()
        self.VERIFY_REQUESTS_patcher.stop()
        self.MEDIAVIEWER_TV_PATH_URL_patcher.stop()
        self.MEDIAVIEWER_MOVIE_PATH_URL_patcher.stop()
        self.BASE_PATH_patcher.stop()

    def test_getMovies(self):
        expected = {
            "some.local.path": {"pks": set([123, 125]), "finished": False},
            "another.local.path": {"pks": set([124]), "finished": False},
        }
        actual = self.path._getPaths(getMovies=True)

        self.assertEqual(expected, actual)
        self.mock_get.assert_has_calls(
            [
                mock.call(
                    "test_movie_url",
                    verify=True,
                    auth=("test_waiter_username", "test_waiter_password"),
                ),
                mock.call().raise_for_status(),
                mock.call().json(),
                mock.call(
                    "next.url",
                    verify=True,
                    auth=("test_waiter_username", "test_waiter_password"),
                ),
                mock.call().raise_for_status(),
                mock.call().json(),
            ]
        )

    def test_getTVShows(self):
        expected = {
            "some.local.path": {"pks": set([123, 125]), "finished": False},
            "another.local.path": {"pks": set([124]), "finished": False},
        }
        actual = self.path._getPaths(getMovies=False)

        self.assertEqual(expected, actual)
        self.mock_get.assert_has_calls(
            [
                mock.call(
                    "test_tv_url",
                    verify=True,
                    auth=("test_waiter_username", "test_waiter_password"),
                ),
                mock.call().raise_for_status(),
                mock.call().json(),
                mock.call(
                    "next.url",
                    verify=True,
                    auth=("test_waiter_username", "test_waiter_password"),
                ),
                mock.call().raise_for_status(),
                mock.call().json(),
            ]
        )


class TestGetTVPaths(unittest.TestCase):
    def setUp(self):
        self._getPaths_patcher = mock.patch("path.Path._getPaths")
        self.mock_getPaths = self._getPaths_patcher.start()

        self.path = Path("/path/to/local", "/path/to/remote")

    def tearDown(self):
        self._getPaths_patcher.stop()

    def test_getTVPaths(self):
        expected = self.mock_getPaths.return_value
        actual = self.path.getTVPaths()

        self.assertEqual(expected, actual)
        self.mock_getPaths.assert_called_once_with(getMovies=False)


class TestGetMoviePaths(unittest.TestCase):
    def setUp(self):
        self._getPaths_patcher = mock.patch("path.Path._getPaths")
        self.mock_getPaths = self._getPaths_patcher.start()

        self.path = Path("/path/to/local", "/path/to/remote")

    def tearDown(self):
        self._getPaths_patcher.stop()

    def test_getTVPaths(self):
        expected = self.mock_getPaths.return_value
        actual = self.path.getMoviePaths()

        self.assertEqual(expected, actual)
        self.mock_getPaths.assert_called_once_with(getMovies=True)


class TestGetLocalPaths(unittest.TestCase):
    def setUp(self):
        self.LOCAL_TV_SHOWS_PATHS_patcher = mock.patch(
            "path.LOCAL_TV_SHOWS_PATHS", "test_local_tv_path"
        )
        self.LOCAL_TV_SHOWS_PATHS_patcher.start()

        self.LOCAL_MOVIE_PATHS_patcher = mock.patch(
            "path.LOCAL_MOVIE_PATHS", "test_local_movie_path"
        )
        self.LOCAL_MOVIE_PATHS_patcher.start()

        self._buildLocalPaths_patcher = mock.patch("path.Path._buildLocalPaths")
        self.mock_buildLocalPaths = self._buildLocalPaths_patcher.start()

    def tearDown(self):
        self.LOCAL_MOVIE_PATHS_patcher.stop()
        self.LOCAL_TV_SHOWS_PATHS_patcher.stop()
        self._buildLocalPaths_patcher.stop()

    def test_getLocalMovies(self):
        expected = self.mock_buildLocalPaths.return_value
        actual = Path._getLocalPaths(getMovies=True)

        self.assertEqual(expected, actual)
        self.mock_buildLocalPaths.assert_called_once_with("test_local_movie_path")

    def test_getLocalTVShows(self):
        expected = self.mock_buildLocalPaths.return_value
        actual = Path._getLocalPaths(getMovies=False)

        self.assertEqual(expected, actual)
        self.mock_buildLocalPaths.assert_called_once_with("test_local_tv_path")


class TestBuildLocalPaths(unittest.TestCase):
    def setUp(self):
        self.error_patcher = mock.patch("path.log.error")
        self.mock_error = self.error_patcher.start()

        self.exists_patcher = mock.patch("path.os.path.exists")
        self.mock_exists = self.exists_patcher.start()

        self.listdir_patcher = mock.patch("path.os.listdir")
        self.mock_listdir = self.listdir_patcher.start()

    def tearDown(self):
        self.error_patcher.stop()
        self.listdir_patcher.stop()
        self.exists_patcher.stop()

    def test_buildLocalPaths(self):
        test_paths = ["file_path1", "file_path2", "file_path3"]

        self.mock_exists.side_effect = [True, False, True]
        self.mock_listdir.side_effect = [
            ("listdir_path1", "listdir_path2"),
            ("listdir_path3", "listdir_path4"),
        ]

        expected = set(
            [
                "file_path1/listdir_path1",
                "file_path1/listdir_path2",
                "file_path3/listdir_path3",
                "file_path3/listdir_path4",
            ]
        )
        actual = Path._buildLocalPaths(test_paths)

        self.assertEqual(expected, actual)
        self.mock_exists.assert_has_calls(
            [mock.call("file_path1"), mock.call("file_path2"), mock.call("file_path3"),]
        )
        self.mock_error.assert_called_once_with(
            "file_path2 does not exist. Continuing..."
        )
        self.mock_listdir.assert_has_calls(
            [mock.call("file_path1"), mock.call("file_path3"),]
        )


class TestGetLocalTVAndMoviePaths(unittest.TestCase):
    def setUp(self):
        self._getLocalPaths_patcher = mock.patch("path.Path._getLocalPaths")
        self.mock_getLocalPaths = self._getLocalPaths_patcher.start()

    def tearDown(self):
        self._getLocalPaths_patcher.stop()

    def test_getLocalTVPaths(self):
        expected = self.mock_getLocalPaths.return_value
        actual = Path.getLocalTVPaths()

        self.assertEqual(expected, actual)
        self.mock_getLocalPaths.assert_called_once_with(getMovies=False)

    def test_getLocalMoviePaths(self):
        expected = self.mock_getLocalPaths.return_value
        actual = Path.getLocalMoviePaths()

        self.assertEqual(expected, actual)
        self.mock_getLocalPaths.assert_called_once_with(getMovies=True)


class TestGetAllPaths(unittest.TestCase):
    def setUp(self):
        self._getPaths_patcher = mock.patch("path.Path._getPaths")
        self.mock_getPaths = self._getPaths_patcher.start()

        self._getLocalPaths_patcher = mock.patch("path.Path._getLocalPaths")
        self.mock_getLocalPaths = self._getLocalPaths_patcher.start()

        self.mock_getPaths.return_value = {
            "test_path1": {"pks": set([123, 124]), "finished": False},
            "test_path2": {"pks": set([100, 101]), "finished": False},
        }
        self.mock_getLocalPaths.return_value = set(["test_path3", "test_path4"])

    def tearDown(self):
        self._getLocalPaths_patcher.stop()
        self._getPaths_patcher.stop()

    def test_getMovies(self):
        expected = {
            "test_path1": {"pks": set([123, 124]), "finished": False},
            "test_path2": {"pks": set([100, 101]), "finished": False},
            "test_path3": {"pks": set([-1]), "finished": False},
            "test_path4": {"pks": set([-1]), "finished": False},
        }
        actual = Path._getAllPaths(getMovies=True)

        self.assertEqual(expected, actual)
        self.mock_getPaths.assert_called_once_with(getMovies=True)
        self.mock_getLocalPaths.assert_called_once_with(getMovies=True)

    def test_not_getMovies(self):
        expected = {
            "test_path1": {"pks": set([123, 124]), "finished": False},
            "test_path2": {"pks": set([100, 101]), "finished": False},
            "test_path3": {"pks": set([-1]), "finished": False},
            "test_path4": {"pks": set([-1]), "finished": False},
        }
        actual = Path._getAllPaths(getMovies=False)

        self.assertEqual(expected, actual)
        self.mock_getPaths.assert_called_once_with(getMovies=False)
        self.mock_getLocalPaths.assert_called_once_with(getMovies=False)


class TestGetAllMovieAndTVPaths(unittest.TestCase):
    def setUp(self):
        self._getAllPaths_patcher = mock.patch("path.Path._getAllPaths")
        self.mock_getAllPaths = self._getAllPaths_patcher.start()

    def tearDown(self):
        self._getAllPaths_patcher.stop()

    def test_getAllTVPaths(self):
        expected = self.mock_getAllPaths.return_value
        actual = Path.getAllTVPaths()

        self.assertEqual(expected, actual)
        self.mock_getAllPaths.assert_called_once_with(getMovies=False)

    def test_getAllMoviePaths(self):
        expected = self.mock_getAllPaths.return_value
        actual = Path.getAllMoviePaths()

        self.assertEqual(expected, actual)
        self.mock_getAllPaths.assert_called_once_with(getMovies=True)


class TestGetPathByLocalPathAndRemotePath(unittest.TestCase):
    def setUp(self):
        self.MEDIAVIEWER_MOVIE_PATH_URL_patcher = mock.patch(
            "path.MEDIAVIEWER_MOVIE_PATH_URL", "test_movie_url"
        )
        self.MEDIAVIEWER_MOVIE_PATH_URL_patcher.start()

        self.MEDIAVIEWER_TV_PATH_URL_patcher = mock.patch(
            "path.MEDIAVIEWER_TV_PATH_URL", "test_tv_url"
        )
        self.MEDIAVIEWER_TV_PATH_URL_patcher.start()

        self.VERIFY_REQUESTS_patcher = mock.patch("path.VERIFY_REQUESTS", True)
        self.VERIFY_REQUESTS_patcher.start()

        self.WAITER_USERNAME_patcher = mock.patch(
            "path.WAITER_USERNAME", "test_waiter_username"
        )
        self.WAITER_USERNAME_patcher.start()

        self.WAITER_PASSWORD_patcher = mock.patch(
            "path.WAITER_PASSWORD", "test_waiter_password"
        )
        self.WAITER_PASSWORD_patcher.start()

        self.get_patcher = mock.patch("path.requests.get")
        self.mock_get = self.get_patcher.start()

    def tearDown(self):
        self.get_patcher.stop()
        self.MEDIAVIEWER_TV_PATH_URL_patcher.stop()
        self.MEDIAVIEWER_MOVIE_PATH_URL_patcher.stop()
        self.WAITER_PASSWORD_patcher.stop()
        self.WAITER_USERNAME_patcher.stop()
        self.VERIFY_REQUESTS_patcher.stop()

    def test_useMovieURL(self):
        expected = self.mock_get.return_value.json.return_value
        actual = Path._getPathByLocalPathAndRemotePath(
            "test_localpath", "test_remotepath", useMovieURL=True
        )

        self.assertEqual(expected, actual)
        self.mock_get.assert_called_once_with(
            "test_movie_url",
            params={"localpath": "test_localpath", "remotepath": "test_remotepath"},
            verify=True,
            auth=("test_waiter_username", "test_waiter_password"),
        )
        self.mock_get.return_value.raise_for_status.assert_called_once_with()
        self.mock_get.return_value.json.assert_called_once_with()

    def test_not_useMovieURL(self):
        expected = self.mock_get.return_value.json.return_value
        actual = Path._getPathByLocalPathAndRemotePath(
            "test_localpath", "test_remotepath", useMovieURL=False
        )

        self.assertEqual(expected, actual)
        self.mock_get.assert_called_once_with(
            "test_tv_url",
            params={"localpath": "test_localpath", "remotepath": "test_remotepath"},
            verify=True,
            auth=("test_waiter_username", "test_waiter_password"),
        )
        self.mock_get.return_value.raise_for_status.assert_called_once_with()
        self.mock_get.return_value.json.assert_called_once_with()


class TestGetMovieAndTVPathByLocalPathAndRemotePath(unittest.TestCase):
    def setUp(self):
        self._getPathByLocalPathAndRmeotePath_patcher = mock.patch(
            "path.Path._getPathByLocalPathAndRemotePath"
        )
        self.mock_getPathByLocalPathAndRemotePath = (
            self._getPathByLocalPathAndRmeotePath_patcher.start()
        )

    def tearDown(self):
        self._getPathByLocalPathAndRmeotePath_patcher.stop()

    def test_getTVPathByLocalPathAndRemotePath(self):
        expected = self.mock_getPathByLocalPathAndRemotePath.return_value
        actual = Path.getTVPathByLocalPathAndRemotePath(
            "test_localpath", "test_remotepath",
        )

        self.assertEqual(expected, actual)
        self.mock_getPathByLocalPathAndRemotePath.assert_called_once_with(
            "test_localpath", "test_remotepath", useMovieURL=False
        )

    def test_getMoviePathByLocalPathAndRemotePath(self):
        expected = self.mock_getPathByLocalPathAndRemotePath.return_value
        actual = Path.getMoviePathByLocalPathAndRemotePath(
            "test_localpath", "test_remotepath",
        )

        self.assertEqual(expected, actual)
        self.mock_getPathByLocalPathAndRemotePath.assert_called_once_with(
            "test_localpath", "test_remotepath", useMovieURL=True
        )
