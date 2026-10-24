import pytest
import mock
import requests
import uuid
from pathlib import Path

from utils import (
    get_localpath_by_filename,
    get_media_path_by_filename,
    upload_subtitle_files,
)


class TestGetLocalpathByFilename:
    @pytest.fixture(autouse=True)
    def setUp(self, mocker):
        mocker.patch("utils.WAITER_USERNAME", "waiter_username")

        mocker.patch("utils.WAITER_PASSWORD", "waiter_password")

        mocker.patch("utils.TIMEOUT", 5)

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
            timeout=5,
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
            timeout=5,
        )

    def test_returns_raw_b2_media_path(self):
        uri = "b2://bucket/prefix//Show%20Name/"
        self.mock_response.json.return_value = {"path": uri}

        assert get_media_path_by_filename(self.test_filename) == uri
        assert self.mock_get.call_args.kwargs["timeout"]


class TestUploadSubtitleFiles:
    @pytest.mark.parametrize(
        "configured_suffix", ["mv-encoded.mp4", "custom-encode.mp4"]
    )
    def test_lanterns_encoded_tracks_upload_as_uuid_objects(
        self, mocker, temp_directory, configured_suffix
    ):
        mocker.patch("utils.MEDIAVIEWER_SUFFIX", configured_suffix)
        mock_upload = mocker.patch("utils.b2.get_b2_client")
        prefix = "server/42/"
        original = "Lanterns.S01E01.1080p.WEBRip.10Bit.DDP5.1.x265-NeoNoir.mp4.ALFRED-ENCODED.mp4"
        video = temp_directory / f"{original}.{configured_suffix}"
        video.write_bytes(b"encoded video")
        tracks = [temp_directory / f"{original}-{index}.vtt" for index in (0, 1)]
        for track in tracks:
            track.write_bytes(b"subtitle")
        decoy = temp_directory / f"{original.replace('S01E01', 'S01E02')}-0.vtt"
        decoy.write_bytes(b"other episode")

        names = upload_subtitle_files(video, temp_directory, "test-bucket", prefix)

        assert len(names) == 2
        uploads = mock_upload.return_value.upload_file.call_args_list
        assert {call.args[0] for call in uploads} == set(tracks)
        assert len(uploads) == 2
        for name, call in zip(names, uploads):
            object_uuid, extension = name.split(".")
            assert str(uuid.UUID(object_uuid)) == object_uuid
            assert extension == "vtt"
            assert call.args[1:] == ("test-bucket", f"{prefix}{name}")
            assert str(
                uuid.UUID(call.args[2].removeprefix(prefix).removesuffix(".vtt"))
            )
            assert "Lanterns" not in call.args[2]

    def test_uploads_to_explicit_destination(self, mocker, temp_directory):
        mock_upload = mocker.patch("utils.b2.get_b2_client")
        video = temp_directory / "Episode.mv-encoded.mp4"
        video.write_bytes(b"video")
        subtitle = temp_directory / "Episode.mv-encoded.mp4-0.vtt"
        subtitle.write_bytes(b"subtitle")

        result = upload_subtitle_files(
            video,
            temp_directory,
            bucket="remote-bucket",
            key_prefix="archive/nested/Show/",
        )

        assert len(result) == 1
        assert result[0].endswith(".vtt")
        assert str(uuid.UUID(result[0][:-4])) == result[0][:-4]
        mock_upload.return_value.upload_file.assert_called_once_with(
            subtitle, "remote-bucket", f"archive/nested/Show/{result[0]}"
        )

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

        assert len(result) == 1
        assert result[0].endswith(".vtt")
        assert str(uuid.UUID(result[0][:-4])) == result[0][:-4]
        mock_upload.return_value.upload_file.assert_called_once_with(
            matching,
            "bucket",
            f"prefix/Show.Name/{result[0]}",
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

    def test_matches_precise_original_and_language_subtitles_and_converts_srt(
        self, mocker, temp_directory
    ):
        mock_upload = mocker.patch("utils.b2.get_b2_client")
        convert = mocker.patch("convert._convertSrtToVtt")
        video = temp_directory / "Episode.S01E01.mv-encoded.mp4"
        video.write_bytes(b"video")
        original = temp_directory / "Episode.S01E01.VTT"
        original.write_bytes(b"vtt")
        srt = temp_directory / "Episode.S01E01.en.SRT"
        srt.write_bytes(b"srt")
        converted = temp_directory / "converted.vtt"
        converted.write_bytes(b"converted")
        convert.return_value = converted
        adjacent = temp_directory / "Episode.S01E010.eng.srt"
        adjacent.write_bytes(b"wrong")
        unrelated = temp_directory / "Other.English.srt"
        unrelated.write_bytes(b"wrong")

        result = upload_subtitle_files(video, temp_directory, "bucket", "server/42/")

        assert len(result) == 2
        uploaded = mock_upload.return_value.upload_file.call_args_list
        assert {call.args[0] for call in uploaded} == {original, converted}
        assert all(
            call.args[1] == "bucket" and call.args[2].startswith("server/42/")
            for call in uploaded
        )
        assert all(name.endswith(".vtt") for name in result)
        convert.assert_called_once_with(srt)

    def test_prefers_vtt_for_same_track_and_matches_generated_name(
        self, mocker, temp_directory
    ):
        mock_upload = mocker.patch("utils.b2.get_b2_client")
        video = temp_directory / "Episode.mp4.mv-encoded.mp4"
        video.write_bytes(b"video")
        subtitle = temp_directory / "Episode.mp4.mv-encoded.mp4-0.VTT"
        subtitle.write_bytes(b"vtt")
        srt = temp_directory / "Episode.mp4.mv-encoded.mp4-0.srt"
        srt.write_bytes(b"srt")

        result = upload_subtitle_files(video, temp_directory, "bucket", "server/42/")

        assert len(result) == 1
        mock_upload.return_value.upload_file.assert_called_once_with(
            subtitle, "bucket", f"server/42/{result[0]}"
        )
