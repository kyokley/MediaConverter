import pytest
import mock
from file import File, MEDIAVIEWER_TV_FILE_URL


class TestFile:
    @pytest.fixture(autouse=True)
    def setUp(self):
        self.file = File("testfilename", 123, 234, True)

    def test_getFileSet(self, mocker):
        mock_requests = mocker.patch("file.requests")

        test_data = {
            "next": None,
            "results": [
                {"filename": "file1"},
                {"filename": "file2"},
                {"filename": "file3"},
            ],
        }
        mock_request = mock.MagicMock()
        mock_request.json.return_value = test_data

        mock_requests.get.return_value = mock_request

        expectedSet = set(
            [
                "file1",
                "file2",
                "file3",
            ]
        )

        assert expectedSet == self.file.getTVFileSet(1)

    def test_post(self, mocker):
        mock_postData = mocker.patch("file.postData")
        expected = {
            "path": 123,
            "filename": "testfilename",
            "skip": False,
            "size": 234,
            "finished": True,
            "streamable": True,
        }
        self.file.postTVFile()
        mock_postData.assert_called_once_with(expected, MEDIAVIEWER_TV_FILE_URL)
