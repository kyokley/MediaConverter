import pytest
import mock
import requests
from pathlib import Path

from utils import get_localpath_by_filename, upload_subtitle_files


class TestGetLocalpathByFilename:
    @pytest.fixture(autouse=True)
    def setUp(self, mocker):
        mocker.patch("utils.WAITER_USERNAME", "waiter_username")

        mocker.patch("utils.WAITER_PASSWORD", "waiter_password")

        mocker.patch("utils.mediaviewer_infer_scrapers_url", lambda: "test_url")

        self.mock_get = mocker.patch("utils.requests.get")

        self.test_filename = "test_filename.S02E10.mpg"

        self.mock_response = mock.MagicMock(requests.models.Response)
        self.mock_response.json.return_value = {
            "path": "/path/to/media/test_filename",
        }

        self.mock_get.return_value = self.mock_response

    def test_success(self):
        expected = Path("/path/to/media/test_filename")
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


class TestUploadSubtitleFiles:
    def test_uploads_matching_vtt_files(self, mocker, temp_directory):
        mocker.patch("utils.B2_BUCKET_NAME", "bucket")
        mocker.patch("utils.B2_NAME_PREFIX", "prefix/")
        mock_upload = mocker.patch("utils.b2.get_b2_client")

        video_dir = temp_directory / "Show.Name"
        video_dir.mkdir(parents=True)
        video_path = video_dir / "Show.Name.S01E01.mv-encoded.mp4"
        video_path.write_bytes(b"video")
        matching = video_dir / "Show.Name.S01E01.mv-encoded.mp4.mv-encoded.mp4-0.vtt"
        matching.write_bytes(b"subtitle")
        other = video_dir / "Show.Name.S01E02.mv-encoded.mp4.mv-encoded.mp4-0.vtt"
        other.write_bytes(b"other subtitle")

        result = upload_subtitle_files(video_path, video_dir)

        assert result == ["Show.Name.S01E01.mv-encoded.mp4.mv-encoded.mp4-0.vtt"]
        mock_upload.return_value.upload_file.assert_called_once_with(
            matching,
            "bucket",
            "prefix/Show.Name/Show.Name.S01E01.mv-encoded.mp4.mv-encoded.mp4-0.vtt",
        )

    def test_no_matching_vtt_files(self, mocker, temp_directory):
        mocker.patch("utils.B2_BUCKET_NAME", "bucket")
        mocker.patch("utils.B2_NAME_PREFIX", "prefix/")
        mock_upload = mocker.patch("utils.b2.get_b2_client")

        video_dir = temp_directory / "Show.Name"
        video_dir.mkdir(parents=True)
        video_path = video_dir / "Show.Name.S01E01.mv-encoded.mp4"
        video_path.write_bytes(b"video")

        result = upload_subtitle_files(video_path, video_dir)

        assert result == []
        assert not mock_upload.return_value.upload_file.called
