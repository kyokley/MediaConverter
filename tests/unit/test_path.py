import pytest
import mock

from path import Path


class TestPostMovie:
    @pytest.fixture(autouse=True)
    def setUp(self, mocker):
        self.mock_post = mocker.patch("path.Path._post")

        self.path = Path("/path/to/local", "/path/to/remote")

    def test_postMovie(self):
        expected = None
        actual = self.path.postMovie()

        assert expected == actual
        self.mock_post.assert_called_once_with(useMovieURL=True)


class TestPostTVShow:
    @pytest.fixture(autouse=True)
    def setUp(self, mocker):
        self.mock_post = mocker.patch("path.Path._post")

        self.path = Path("/path/to/local", "/path/to/remote")

    def test_postTVShow(self):
        expected = None
        actual = self.path.postTVShow()

        assert expected == actual
        self.mock_post.assert_called_once_with(useMovieURL=False)


class TestPost:
    @pytest.fixture(autouse=True)
    def setUp(self, mocker):
        self.mock_postData = mocker.patch("path.postData")
        mocker.patch("path.MEDIAVIEWER_MOVIE_PATH_URL", "test_movie_url")
        mocker.patch("path.MEDIAVIEWER_TV_PATH_URL", "test_tv_url")
        mocker.patch("path.SERVER_NAME", "test_server_name")

        self.path = Path("/path/to/local", "/path/to/remote")

    def test_useMovieURL(self):
        expected = None
        actual = self.path._post(useMovieURL=True)

        expected_values = {
            "localpath": "/path/to/local",
            "remotepath": "/path/to/remote",
            "skip": False,
            "server": "test_server_name",
        }

        assert expected == actual
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

        assert expected == actual
        self.mock_postData.assert_called_once_with(expected_values, "test_tv_url")


class TestGetPaths:
    @pytest.fixture(autouse=True)
    def setUp(self, mocker):
        mocker.patch("path.MEDIAVIEWER_MOVIE_PATH_URL", "test_movie_url")
        mocker.patch("path.MEDIAVIEWER_TV_PATH_URL", "test_tv_url")
        mocker.patch("path.VERIFY_REQUESTS", True)
        mocker.patch("path.WAITER_USERNAME", "test_waiter_username")
        mocker.patch("path.WAITER_PASSWORD", "test_waiter_password")
        mocker.patch("path.BASE_PATH", "")
        self.mock_get = mocker.patch("path.requests.get")

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

    def test_getMovies(self):
        expected = {
            "some.local.path": {"pks": set([123, 125]), "finished": False},
            "another.local.path": {"pks": set([124]), "finished": False},
        }
        actual = self.path._getPaths(getMovies=True)

        assert expected == actual
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

        assert expected == actual
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


class TestGetTVPaths:
    @pytest.fixture(autouse=True)
    def setUp(self, mocker):
        self.mock_getPaths = mocker.patch("path.Path._getPaths")

        self.path = Path("/path/to/local", "/path/to/remote")

    def test_getTVPaths(self):
        expected = self.mock_getPaths.return_value
        actual = self.path.getTVPaths()

        assert expected == actual
        self.mock_getPaths.assert_called_once_with(getMovies=False)


class TestGetMoviePaths:
    @pytest.fixture(autouse=True)
    def setUp(self, mocker):
        self.mock_getPaths = mocker.patch("path.Path._getPaths")

        self.path = Path("/path/to/local", "/path/to/remote")

    def test_getTVPaths(self):
        expected = self.mock_getPaths.return_value
        actual = self.path.getMoviePaths()

        assert expected == actual
        self.mock_getPaths.assert_called_once_with(getMovies=True)


class TestGetLocalPaths:
    @pytest.fixture(autouse=True)
    def setUp(self, mocker):
        mocker.patch("path.LOCAL_TV_SHOWS_PATHS", "test_local_tv_path")

        mocker.patch("path.LOCAL_MOVIE_PATHS", "test_local_movie_path")

        self.mock_buildLocalPaths = mocker.patch("path.Path._buildLocalPaths")

    def test_getLocalMovies(self):
        expected = self.mock_buildLocalPaths.return_value
        actual = Path._getLocalPaths(getMovies=True)

        assert expected == actual
        self.mock_buildLocalPaths.assert_called_once_with("test_local_movie_path")

    def test_getLocalTVShows(self):
        expected = self.mock_buildLocalPaths.return_value
        actual = Path._getLocalPaths(getMovies=False)

        assert expected == actual
        self.mock_buildLocalPaths.assert_called_once_with("test_local_tv_path")


class TestBuildLocalPaths:
    @pytest.fixture(autouse=True)
    def setUp(self, mocker):
        self.mock_error = mocker.patch("path.log.error")
        self.mock_exists = mocker.patch("path.os.path.exists")
        self.mock_listdir = mocker.patch("path.os.listdir")

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

        assert expected == actual
        self.mock_exists.assert_has_calls(
            [
                mock.call("file_path1"),
                mock.call("file_path2"),
                mock.call("file_path3"),
            ]
        )
        self.mock_error.assert_called_once_with(
            "file_path2 does not exist. Continuing..."
        )
        self.mock_listdir.assert_has_calls(
            [
                mock.call("file_path1"),
                mock.call("file_path3"),
            ]
        )


class TestGetLocalTVAndMoviePaths:
    @pytest.fixture(autouse=True)
    def setUp(self, mocker):
        self.mock_getLocalPaths = mocker.patch("path.Path._getLocalPaths")

    def test_getLocalTVPaths(self):
        expected = self.mock_getLocalPaths.return_value
        actual = Path.getLocalTVPaths()

        assert expected == actual
        self.mock_getLocalPaths.assert_called_once_with(getMovies=False)

    def test_getLocalMoviePaths(self):
        expected = self.mock_getLocalPaths.return_value
        actual = Path.getLocalMoviePaths()

        assert expected == actual
        self.mock_getLocalPaths.assert_called_once_with(getMovies=True)


class TestGetAllPaths:
    @pytest.fixture(autouse=True)
    def setUp(self, mocker):
        self.mock_getPaths = mocker.patch("path.Path._getPaths")

        self.mock_getLocalPaths = mocker.patch("path.Path._getLocalPaths")

        self.mock_getPaths.return_value = {
            "test_path1": {"pks": set([123, 124]), "finished": False},
            "test_path2": {"pks": set([100, 101]), "finished": False},
        }
        self.mock_getLocalPaths.return_value = set(["test_path3", "test_path4"])

    def test_getMovies(self):
        expected = {
            "test_path1": {"pks": set([123, 124]), "finished": False},
            "test_path2": {"pks": set([100, 101]), "finished": False},
            "test_path3": {"pks": set([-1]), "finished": False},
            "test_path4": {"pks": set([-1]), "finished": False},
        }
        actual = Path._getAllPaths(getMovies=True)

        assert expected == actual
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

        assert expected == actual
        self.mock_getPaths.assert_called_once_with(getMovies=False)
        self.mock_getLocalPaths.assert_called_once_with(getMovies=False)


class TestGetAllMovieAndTVPaths:
    @pytest.fixture(autouse=True)
    def setUp(self, mocker):
        self.mock_getAllPaths = mocker.patch("path.Path._getAllPaths")

    def test_getAllTVPaths(self):
        expected = self.mock_getAllPaths.return_value
        actual = Path.getAllTVPaths()

        assert expected == actual
        self.mock_getAllPaths.assert_called_once_with(getMovies=False)

    def test_getAllMoviePaths(self):
        expected = self.mock_getAllPaths.return_value
        actual = Path.getAllMoviePaths()

        assert expected == actual
        self.mock_getAllPaths.assert_called_once_with(getMovies=True)


class TestGetPathByLocalPathAndRemotePath:
    @pytest.fixture(autouse=True)
    def setUp(self, mocker):
        mocker.patch("path.MEDIAVIEWER_MOVIE_PATH_URL", "test_movie_url")
        mocker.patch("path.MEDIAVIEWER_TV_PATH_URL", "test_tv_url")
        mocker.patch("path.VERIFY_REQUESTS", True)
        mocker.patch("path.WAITER_USERNAME", "test_waiter_username")
        mocker.patch("path.WAITER_PASSWORD", "test_waiter_password")

        self.mock_get = mocker.patch("path.requests.get")

    def test_useMovieURL(self):
        expected = self.mock_get.return_value.json.return_value
        actual = Path._getPathByLocalPathAndRemotePath(
            "test_localpath", "test_remotepath", useMovieURL=True
        )

        assert expected == actual
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

        assert expected == actual
        self.mock_get.assert_called_once_with(
            "test_tv_url",
            params={"localpath": "test_localpath", "remotepath": "test_remotepath"},
            verify=True,
            auth=("test_waiter_username", "test_waiter_password"),
        )
        self.mock_get.return_value.raise_for_status.assert_called_once_with()
        self.mock_get.return_value.json.assert_called_once_with()


class TestGetMovieAndTVPathByLocalPathAndRemotePath:
    @pytest.fixture(autouse=True)
    def setUp(self, mocker):
        self.mock_getPathByLocalPathAndRemotePath = mocker.patch(
            "path.Path._getPathByLocalPathAndRemotePath"
        )

    def test_getTVPathByLocalPathAndRemotePath(self):
        expected = self.mock_getPathByLocalPathAndRemotePath.return_value
        actual = Path.getTVPathByLocalPathAndRemotePath(
            "test_localpath",
            "test_remotepath",
        )

        assert expected == actual
        self.mock_getPathByLocalPathAndRemotePath.assert_called_once_with(
            "test_localpath", "test_remotepath", useMovieURL=False
        )

    def test_getMoviePathByLocalPathAndRemotePath(self):
        expected = self.mock_getPathByLocalPathAndRemotePath.return_value
        actual = Path.getMoviePathByLocalPathAndRemotePath(
            "test_localpath",
            "test_remotepath",
        )

        assert expected == actual
        self.mock_getPathByLocalPathAndRemotePath.assert_called_once_with(
            "test_localpath", "test_remotepath", useMovieURL=True
        )
