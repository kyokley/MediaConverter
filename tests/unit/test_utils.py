import pytest
import mock
import requests

from utils import get_localpath_by_filename


class TestGetLocalpathByFilename:
    @pytest.fixture(autouse=True)
    def setUp(self, mocker):
        mocker.patch("utils.WAITER_USERNAME", "waiter_username")

        mocker.patch("utils.WAITER_PASSWORD", "waiter_password")

        mocker.patch("utils.MEDIAVIEWER_INFER_SCRAPERS_URL", "test_url")

        self.mock_get = mocker.patch("utils.requests.get")

        self.test_filename = "test_filename.S02E10.mpg"

        self.mock_response = mock.MagicMock(requests.models.Response)
        self.mock_response.json.return_value = {
            "is_movie": False,
            "localpath": "/path/to/media/test_filename",
            "number_of_unwatched_shows": 0,
            "pk": 161,
            "remotepath": "/path/to/media/test_filename",
            "server": "localhost",
            "skip": True,
        }

        self.mock_get.return_value = self.mock_response

    def test_success(self):
        expected = "/path/to/media/test_filename"
        actual = get_localpath_by_filename(self.test_filename)

        assert expected == actual
        self.mock_get.assert_called_once_with(
            "test_url",
            params={"title": self.test_filename},
            auth=("waiter_username", "waiter_password"),
        )

    def test_failure(self):
        self.mock_response.raise_for_status.side_effect = requests.exceptions.HTTPError(
            "Failed"
        )

        expected = None
        actual = get_localpath_by_filename(self.test_filename)

        assert expected == actual
        self.mock_get.assert_called_once_with(
            "test_url",
            params={"title": self.test_filename},
            auth=("waiter_username", "waiter_password"),
        )
