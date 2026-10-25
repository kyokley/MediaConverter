import json
import pytest
import uuid
from pathlib import Path

import mock
from mock import call
from convert import AlreadyEncoded, SkipProcessing
from tv_runner import TvRunner, Tv
from utils import EncoderException


class TestTvRunner:
    @pytest.fixture(autouse=True)
    def setUp(self, mocker, temp_directory):
        mocker.patch("tv_runner.LOCAL_TV_SHOWS_PATHS", [str(temp_directory)])
        self.mock_sort_unsorted_files = mocker.patch(
            "tv_runner.TvRunner._sort_unsorted_files"
        )
        mocker.patch("tv_runner.MediaFile.get_all_filenames", return_value=set())

        self.tvRunner = TvRunner()

    def test_load_paths(self, mocker):
        mock_tv = mocker.patch("tv_runner.Tv")

        fake_path = mock.MagicMock()
        fake_pks = mock.MagicMock()
        fake_paths = {
            fake_path: {
                "pks": fake_pks,
                "finished": False,
            },
            mock.MagicMock(): {
                "pks": mock.MagicMock(),
                "finished": True,
            },
        }

        expected = {fake_path: fake_pks}

        mock_tv.get_all_tv.return_value = fake_paths
        self.tvRunner.load_paths()
        assert expected == self.tvRunner.paths

    def test_build_remote_media_file_set(self, mocker):
        mock_tv = mocker.patch("tv_runner.Tv")

        testData = {
            -1: {"media_files": ["invalid"]},
            1: {"media_files": ["test1"]},
            12: {"media_files": ["test12"]},
            123: {"media_files": ["test123"]},
        }
        expectedSet = set(
            [
                "test1",
                "test12",
                "test123",
            ]
        )
        mock_tv.get_media_path = lambda x: testData.get(x)

        actualSet = self.tvRunner.build_remote_media_file_set([-1, 1, 12, 123])
        assert expectedSet == actualSet

    def test_updateFileRecords(self, mocker):
        mock_post_media_file = mocker.patch("tv_runner.MediaFile.post_media_file")
        mock_makeFileStreamable = mocker.patch("tv_runner.makeFileStreamable")
        mock_get_or_create_media_path = mocker.patch(
            "tv_runner.TvRunner.get_or_create_media_path"
        )
        mocker.patch("tv_runner.B2_ENABLED", False)
        mock_os_path_exists = mocker.patch("tv_runner.os.path.exists")
        mock_os_path_getsize = mocker.patch("tv_runner.os.path.getsize")
        mock_os_path_basename = mocker.patch("tv_runner.os.path.basename")

        mock_get_or_create_media_path.return_value = {"pk": 1, "skip": False}
        mock_os_path_exists.return_value = True
        mock_os_path_getsize.return_value = 1
        mock_os_path_basename.return_value = "basename"

        test_path = "/a/local/path"
        test_localFileSet = set(
            [
                "file1",
                "file2",
                "file3",
                "newfile",
            ]
        )
        test_remoteFileSet = set(
            [
                "file1",
                "file2",
                "file3",
            ]
        )

        self.tvRunner.updateFileRecords(
            test_path, test_localFileSet, test_remoteFileSet
        )
        mock_makeFileStreamable.assert_called_with(
            Path("/a/local/path/newfile"),
            appendSuffix=True,
            removeOriginal=True,
            dryRun=False,
        )
        mock_post_media_file.assert_called_once_with(
            mock_makeFileStreamable().name,
            1,
            mock_makeFileStreamable().stat().st_size,
            subtitle_files=[],
        )

    def test_media_file_posts_uuid_and_json_subtitle_names(self, mocker):
        from tv_runner import MediaFile

        response = mock.Mock()
        response.json.return_value = {"pk": 5}
        post = mocker.patch("tv_runner.post_data", return_value=response)
        b2_uuid = "01234567-89ab-cdef-0123-456789abcdef"
        subtitles = ["abcdefab-cdef-abcd-efab-cdefabcdefab.vtt"]

        MediaFile.post_media_file(
            "original.converted.mp4",
            42,
            123,
            subtitle_files=subtitles,
            b2_uuid=b2_uuid,
        )

        payload = post.call_args.args[0]
        assert payload["filename"] == "original.converted.mp4"
        assert payload["media_path"] == 42
        assert payload["size"] == 123
        assert json.loads(payload["subtitle_files"]) == subtitles
        assert payload["b2_uuid"] == b2_uuid

    def test_run(self):
        test_data = {
            "asdf": [1],
            "sdfg": [12, 23],
        }
        self.tvRunner.paths = test_data
        self.tvRunner.load_paths = mock.MagicMock()

        self.tvRunner.buildLocalFileSet = mock.MagicMock()
        self.tvRunner.buildLocalFileSet.return_value = set(["some", "paths"])

        self.tvRunner.fetch_remote_media_path_details = mock.MagicMock()
        self.tvRunner.fetch_remote_media_path_details.return_value = [
            {"pk": 1, "media_files": ["some", "remote", "paths"]}
        ]

        self.tvRunner.updateFileRecords = mock.MagicMock()

        self.tvRunner.handleDirs = mock.MagicMock()

        self.tvRunner.run()

        self.mock_sort_unsorted_files.assert_called_once_with(dry_run=False)
        self.tvRunner.buildLocalFileSet.assert_has_calls(
            [call("sdfg"), call("asdf")], any_order=True
        )
        assert 2 == self.tvRunner.buildLocalFileSet.call_count
        self.tvRunner.fetch_remote_media_path_details.assert_has_calls(
            [call([1]), call([12, 23])], any_order=True
        )
        assert 2 == self.tvRunner.fetch_remote_media_path_details.call_count

        self.tvRunner.updateFileRecords.assert_has_calls(
            [
                call(
                    "sdfg",
                    set(["paths", "some"]),
                    set(["remote", "some", "paths"]),
                    dry_run=False,
                    media_path_details=[
                        {"pk": 1, "media_files": ["some", "remote", "paths"]}
                    ],
                ),
                call(
                    "asdf",
                    set(["paths", "some"]),
                    set(["remote", "some", "paths"]),
                    dry_run=False,
                    media_path_details=[
                        {"pk": 1, "media_files": ["some", "remote", "paths"]}
                    ],
                ),
            ],
            any_order=True,
        )
        assert 2 == self.tvRunner.updateFileRecords.call_count

        self.tvRunner.handleDirs.assert_has_calls(
            [call("asdf", dry_run=False), call("sdfg", dry_run=False)]
        )

    def test_get_or_create_media_path_b2_enabled(self, mocker):
        mocker.patch("tv_runner.B2_ENABLED", True)
        mock_post = mocker.patch("tv_runner.Tv.post_media_path")
        mock_post.return_value = {
            "pk": 1,
            "skip": False,
            "bucket": "bucket",
            "b2_upload_prefix": "tv/42/",
        }
        mock_uri = mocker.patch("tv_runner.get_b2_uri_for_local_path")
        mock_uri.return_value = "b2://bucket/prefix/Show.Name/"

        result = TvRunner.get_or_create_media_path(Path("/base/tv_shows/Show.Name"))

        assert result == {
            "pk": 1,
            "skip": False,
            "bucket": "bucket",
            "b2_upload_prefix": "tv/42/",
        }
        mock_uri.assert_called_once_with(Path("/base/tv_shows/Show.Name"))
        mock_post.assert_called_once_with("b2://bucket/prefix/Show.Name/")

    def test_get_or_create_media_path_b2_disabled(self, mocker):
        mocker.patch("tv_runner.B2_ENABLED", False)
        mock_post = mocker.patch("tv_runner.Tv.post_media_path")
        mock_post.return_value = {"pk": 1, "skip": False}

        result = TvRunner.get_or_create_media_path(Path("/base/tv_shows/Show.Name"))

        assert result == {
            "pk": 1,
            "skip": False,
            "bucket": None,
            "b2_upload_prefix": None,
        }
        mock_post.assert_called_once_with(Path("/base/tv_shows/Show.Name"))

    def test_updateFileRecords_b2_enabled(self, mocker):
        mocker.patch("tv_runner.B2_ENABLED", True)
        mock_upload = mocker.patch("tv_runner.b2.get_b2_client")
        mock_post_media_file = mocker.patch("tv_runner.MediaFile.post_media_file")
        mock_upload_subtitle_files = mocker.patch(
            "tv_runner.upload_subtitle_files", return_value=["subtitle.vtt"]
        )
        mock_makeFileStreamable = mocker.patch("tv_runner.makeFileStreamable")
        mock_get_or_create_media_path = mocker.patch(
            "tv_runner.TvRunner.get_or_create_media_path"
        )
        mock_os_path_exists = mocker.patch("tv_runner.os.path.exists")
        mock_os_path_getsize = mocker.patch("tv_runner.os.path.getsize")
        mock_os_path_basename = mocker.patch("tv_runner.os.path.basename")

        mock_get_or_create_media_path.return_value = {
            "pk": 1,
            "skip": False,
            "bucket": "bucket",
            "b2_upload_prefix": "prefix/path/",
        }
        mock_os_path_exists.return_value = True
        mock_os_path_getsize.return_value = 1
        mock_os_path_basename.return_value = "basename"
        mock_makeFileStreamable.return_value.name = "newfile"
        mock_makeFileStreamable.return_value.suffix = ".mp4"

        test_path = "/a/local/path"
        test_localFileSet = set(["newfile"])
        test_remoteFileSet = set()

        self.tvRunner.updateFileRecords(
            test_path, test_localFileSet, test_remoteFileSet
        )
        key = mock_upload.return_value.upload_file.call_args.args[2]
        assert key.startswith("prefix/path/") and key.endswith(".mp4")
        assert "newfile" not in key
        mock_upload_subtitle_files.assert_called_once_with(
            mock_makeFileStreamable(),
            test_path,
            bucket="bucket",
            key_prefix="prefix/path/",
        )
        mock_post_media_file.assert_called_once_with(
            mock_makeFileStreamable().name,
            1,
            mock_makeFileStreamable().stat().st_size,
            subtitle_files=["subtitle.vtt"],
            b2_uuid=key.removeprefix("prefix/path/").removesuffix(".mp4"),
        )

    def test_global_source_filename_match_skips_before_media_path_or_conversion(
        self, mocker, temp_directory
    ):
        mocker.patch("tv_runner.B2_ENABLED", True)
        mocker.patch(
            "tv_runner.MediaFile.get_all_filenames", return_value={"episode.mkv"}
        )
        encode = mocker.patch("tv_runner.makeFileStreamable")
        create_path = mocker.patch("tv_runner.TvRunner.get_or_create_media_path")
        upload = mocker.patch("tv_runner.b2.get_b2_client")
        post = mocker.patch("tv_runner.MediaFile.post_media_file")

        self.tvRunner.updateFileRecords(temp_directory, {"episode.mkv"}, set())

        encode.assert_not_called()
        create_path.assert_not_called()
        upload.assert_not_called()
        post.assert_not_called()

    def test_global_encoded_filename_match_skips_upload_and_publication(
        self, mocker, temp_directory
    ):
        mocker.patch("tv_runner.B2_ENABLED", True)
        source = temp_directory / "episode.mkv"
        encoded = temp_directory / "episode.converted.mp4"
        source.write_bytes(b"source")
        encoded.write_bytes(b"encoded")
        mocker.patch(
            "tv_runner.MediaFile.get_all_filenames",
            return_value={encoded.name},
        )
        mocker.patch("tv_runner.stripUnicode", return_value=source)
        mocker.patch("tv_runner.makeFileStreamable", return_value=encoded)
        upload = mocker.patch("tv_runner.b2.get_b2_client")
        post = mocker.patch("tv_runner.MediaFile.post_media_file")

        self.tvRunner.updateFileRecords(
            temp_directory,
            {source.name},
            set(),
            media_path_details=[
                {
                    "pk": 1,
                    "path": "b2://bucket/Show/",
                    "bucket": "bucket",
                    "b2_upload_prefix": "tv/42/",
                }
            ],
        )

        upload.assert_not_called()
        post.assert_not_called()

    def test_select_existing_b2_path(self, mocker):
        mocker.patch("tv_runner.B2_ENABLED", True)
        details = [
            {
                "pk": 9,
                "path": "b2://remote-bucket/archive/nested/Show/",
                "skip": False,
                "bucket": "remote-bucket",
                "b2_upload_prefix": "archive/42/",
            },
            {
                "pk": 3,
                "path": "b2://remote-bucket/archive/nested/Show/",
                "skip": False,
                "bucket": "remote-bucket",
                "b2_upload_prefix": "archive/42/",
            },
        ]

        destination = self.tvRunner._select_b2_destination("/local/Show", details)

        assert destination == {
            "pk": 3,
            "skip": False,
            "bucket": "remote-bucket",
            "b2_upload_prefix": "archive/42/",
        }

    def test_recorded_filename_updates_only_selected_media_path(
        self, mocker, temp_directory
    ):
        mocker.patch("tv_runner.B2_ENABLED", True)
        source = temp_directory / "episode.mkv"
        output = temp_directory / "episode.mp4"
        source.write_bytes(b"source")
        output.write_bytes(b"encoded")
        first_detail = {
            "pk": 1,
            "path": "/local/show/",
            "media_files": ["other.mp4"],
        }
        selected_detail = {
            "pk": 2,
            "path": "b2://bucket/nested/Show/",
            "bucket": "bucket",
            "b2_upload_prefix": "numeric/42/",
            "media_files": [],
        }
        details = [first_detail, selected_detail]
        mocker.patch("tv_runner.stripUnicode", return_value=source)
        mocker.patch("tv_runner.makeFileStreamable", return_value=output)
        mocker.patch("tv_runner.b2.get_b2_client")
        mocker.patch("tv_runner.upload_subtitle_files", return_value=[])
        mocker.patch("tv_runner.MediaFile.post_media_file")

        self.tvRunner.updateFileRecords(
            temp_directory,
            {source.name},
            set(),
            media_path_details=details,
        )

        assert first_detail["media_files"] == ["other.mp4"]
        assert selected_detail["media_files"] == [output.name]

    def test_b2_key_prefix_uses_server_prefix_not_logical_uri(self):
        destination = self.tvRunner._select_b2_destination(
            "/local/Show",
            [
                {
                    "pk": 1,
                    "path": "b2://bucket/archive/Show/",
                    "bucket": "bucket",
                    "b2_upload_prefix": "tv/42/",
                }
            ],
        )

        assert destination["b2_upload_prefix"] == "tv/42/"

    def test_existing_b2_destination_uploads_and_records(self, mocker, temp_directory):
        mocker.patch("tv_runner.B2_ENABLED", True)
        source = temp_directory / "episode.mkv"
        encoded = temp_directory / "episode.mv-encoded.mp4"
        source.write_bytes(b"source")
        encoded.write_bytes(b"encoded-video")
        details = [
            {
                "pk": 42,
                "path": "b2://remote-bucket/archive/nested/Show",
                "skip": False,
                "media_files": [],
                "bucket": "remote-bucket",
                "b2_upload_prefix": "archive/42/",
            }
        ]
        mocker.patch("tv_runner.makeFileStreamable", return_value=encoded)
        mocker.patch("tv_runner.stripUnicode", return_value=source)
        mock_upload = mocker.patch("tv_runner.b2.get_b2_client")
        mock_subtitles = mocker.patch(
            "tv_runner.upload_subtitle_files", return_value=["episode.vtt"]
        )
        mock_post = mocker.patch("tv_runner.MediaFile.post_media_file")
        mock_create = mocker.patch("tv_runner.Tv.post_media_path")
        events = []
        mock_upload.return_value.upload_file.side_effect = lambda *args: events.append(
            ("video", args)
        )
        mock_subtitles.side_effect = lambda *args, **kwargs: (
            events.append(("subtitles", args, kwargs)) or ["episode.vtt"]
        )
        mock_post.side_effect = lambda *args, **kwargs: events.append(
            ("record", args, kwargs)
        )

        self.tvRunner.updateFileRecords(
            temp_directory,
            {source.name},
            set(),
            media_path_details=details,
        )

        key = mock_upload.return_value.upload_file.call_args.args[2]
        assert key.startswith("archive/42/") and key.endswith(".mp4")
        assert "episode" not in key
        mock_subtitles.assert_called_once_with(
            encoded,
            temp_directory,
            bucket="remote-bucket",
            key_prefix="archive/42/",
        )
        mock_post.assert_called_once()
        assert mock_post.call_args.args == (
            encoded.name,
            42,
            len(b"encoded-video"),
        )
        assert mock_post.call_args.kwargs["subtitle_files"] == ["episode.vtt"]
        assert mock_post.call_args.kwargs["b2_uuid"] == key.removeprefix(
            "archive/42/"
        ).removesuffix(".mp4")
        assert [event[0] for event in events] == ["video", "subtitles", "record"]
        mock_create.assert_not_called()

    def test_run_fetches_details_and_uses_existing_b2_destination(
        self, mocker, temp_directory
    ):
        mocker.patch("tv_runner.B2_ENABLED", True)
        source = temp_directory / "episode.mkv"
        encoded = temp_directory / "episode.mp4"
        source.write_bytes(b"source")
        encoded.write_bytes(b"encoded")
        detail = {
            "pk": 17,
            "path": "b2://other-bucket/deep/Show/",
            "skip": False,
            "media_files": [],
            "bucket": "other-bucket",
            "b2_upload_prefix": "deep/42/",
        }
        get_path = mocker.patch("tv_runner.Tv.get_media_path", return_value=detail)
        self.tvRunner.load_paths = lambda: setattr(
            self.tvRunner, "paths", {temp_directory: {17, -1}}
        )
        self.tvRunner.handleDirs = mocker.Mock()
        self.tvRunner.buildLocalFileSet = lambda path: {source.name}
        mocker.patch("tv_runner.stripUnicode", return_value=source)
        mocker.patch("tv_runner.makeFileStreamable", return_value=encoded)
        mock_upload = mocker.patch("tv_runner.b2.get_b2_client")
        mocker.patch("tv_runner.upload_subtitle_files", return_value=[])
        mock_post = mocker.patch("tv_runner.MediaFile.post_media_file")
        mock_create = mocker.patch("tv_runner.Tv.post_media_path")

        self.tvRunner.run()

        get_path.assert_called_once_with(17)
        key = mock_upload.return_value.upload_file.call_args.args[2]
        assert key.startswith("deep/42/") and key.endswith(".mp4")
        assert "episode" not in key
        mock_post.assert_called_once()
        assert mock_post.call_args.args == (encoded.name, 17, len(b"encoded"))
        assert mock_post.call_args.kwargs["b2_uuid"] == key.removeprefix(
            "deep/42/"
        ).removesuffix(".mp4")
        mock_create.assert_not_called()

    def test_dry_run_does_not_encode_or_write(self, mocker, temp_directory):
        mocker.patch("tv_runner.B2_ENABLED", True)
        encode = mocker.patch("tv_runner.makeFileStreamable")
        create = mocker.patch("tv_runner.Tv.post_media_path")
        upload = mocker.patch("tv_runner.b2.get_b2_client")
        post = mocker.patch("tv_runner.MediaFile.post_media_file")

        self.tvRunner.updateFileRecords(
            temp_directory,
            {"episode.mkv"},
            set(),
            dry_run=True,
            media_path_details=[
                {
                    "pk": 1,
                    "path": "b2://bucket/Show/",
                    "skip": False,
                    "bucket": "bucket",
                    "b2_upload_prefix": "tv/42/",
                }
            ],
        )

        encode.assert_not_called()
        create.assert_not_called()
        upload.assert_not_called()
        post.assert_not_called()

    def test_selected_skip_path_does_not_write(self, mocker, temp_directory):
        mocker.patch("tv_runner.B2_ENABLED", True)
        encode = mocker.patch("tv_runner.makeFileStreamable")
        upload = mocker.patch("tv_runner.b2.get_b2_client")
        post = mocker.patch("tv_runner.MediaFile.post_media_file")

        self.tvRunner.updateFileRecords(
            temp_directory,
            {"episode.mkv"},
            set(),
            media_path_details=[
                {
                    "pk": 1,
                    "path": "b2://bucket/Show/",
                    "skip": True,
                    "bucket": "bucket",
                    "b2_upload_prefix": "tv/42/",
                }
            ],
        )

        encode.assert_not_called()
        upload.assert_not_called()
        post.assert_not_called()

    @pytest.mark.parametrize("failure", ["video", "subtitle"])
    def test_upload_failures_do_not_post_record(self, mocker, temp_directory, failure):
        mocker.patch("tv_runner.B2_ENABLED", True)
        source = temp_directory / "episode.mkv"
        encoded = temp_directory / "episode.mp4"
        source.write_bytes(b"source")
        encoded.write_bytes(b"encoded")
        mocker.patch("tv_runner.stripUnicode", return_value=source)
        mocker.patch("tv_runner.makeFileStreamable", return_value=encoded)
        upload = mocker.patch("tv_runner.b2.get_b2_client")
        subtitles = mocker.patch("tv_runner.upload_subtitle_files", return_value=[])
        post = mocker.patch("tv_runner.MediaFile.post_media_file")
        error = RuntimeError(f"{failure} upload failed")
        if failure == "video":
            upload.return_value.upload_file.side_effect = error
        else:
            subtitles.side_effect = error

        with pytest.raises(RuntimeError, match=f"{failure} upload failed"):
            self.tvRunner.updateFileRecords(
                temp_directory,
                {source.name},
                set(),
                media_path_details=[
                    {
                        "pk": 1,
                        "path": "b2://bucket/Show/",
                        "skip": False,
                        "bucket": "bucket",
                        "b2_upload_prefix": "tv/42/",
                    }
                ],
            )

        assert encoded.exists()
        post.assert_not_called()

    def test_api_failure_leaves_encoded_file(self, mocker, temp_directory):
        mocker.patch("tv_runner.B2_ENABLED", False)
        source = temp_directory / "episode.mkv"
        encoded = temp_directory / "episode.mp4"
        source.write_bytes(b"source")
        encoded.write_bytes(b"encoded")
        mocker.patch("tv_runner.stripUnicode", return_value=source)
        mocker.patch("tv_runner.makeFileStreamable", return_value=encoded)
        mocker.patch(
            "tv_runner.TvRunner.get_or_create_media_path",
            return_value={"pk": 1, "skip": False},
        )
        post = mocker.patch(
            "tv_runner.MediaFile.post_media_file",
            side_effect=RuntimeError("API failed"),
        )

        remote_names = set()
        with pytest.raises(RuntimeError, match="API failed"):
            self.tvRunner.updateFileRecords(temp_directory, {source.name}, remote_names)

        assert encoded.exists()
        assert remote_names == set()
        post.assert_called_once()

    def test_missing_server_b2_contract_fails_without_filename_fallback(
        self, mocker, temp_directory
    ):
        mocker.patch("tv_runner.B2_ENABLED", True)
        source = temp_directory / "episode.mkv"
        encoded = temp_directory / "episode.mp4"
        source.write_bytes(b"source")
        encoded.write_bytes(b"encoded")
        mocker.patch("tv_runner.stripUnicode", return_value=source)
        mocker.patch("tv_runner.makeFileStreamable", return_value=encoded)
        upload = mocker.patch("tv_runner.b2.get_b2_client")
        post = mocker.patch("tv_runner.MediaFile.post_media_file")

        with pytest.raises(ValueError, match="missing b2_upload_prefix"):
            self.tvRunner.updateFileRecords(
                temp_directory,
                {source.name},
                set(),
                media_path_details=[{"pk": 2, "path": "b2://bucket/real-show-name/"}],
            )

        assert encoded.exists()
        upload.assert_not_called()
        post.assert_not_called()

    def test_already_encoded_mp4_uploads_and_posts(self, mocker, temp_directory):
        mocker.patch("tv_runner.B2_ENABLED", True)
        video = temp_directory / "episode.mp4"
        video.write_bytes(b"encoded")
        mocker.patch("tv_runner.stripUnicode", return_value=video)
        mocker.patch(
            "tv_runner.makeFileStreamable", side_effect=AlreadyEncoded("already")
        )
        upload = mocker.patch("tv_runner.b2.get_b2_client")
        mocker.patch("tv_runner.upload_subtitle_files", return_value=[])
        post = mocker.patch("tv_runner.MediaFile.post_media_file")

        self.tvRunner.updateFileRecords(
            temp_directory,
            {video.name},
            set(),
            media_path_details=[
                {
                    "pk": 1,
                    "path": "b2://bucket/Show/",
                    "bucket": "bucket",
                    "b2_upload_prefix": "tv/42/",
                }
            ],
        )

        key = upload.return_value.upload_file.call_args.args[2]
        assert key.startswith("tv/42/") and key.endswith(".mp4")
        assert video.name not in key
        post.assert_called_once()
        assert post.call_args.args == (video.name, 1, len(b"encoded"))
        assert post.call_args.kwargs["b2_uuid"] == key.removeprefix(
            "tv/42/"
        ).removesuffix(".mp4")

    @pytest.mark.parametrize(
        "configured_suffix", ["mv-encoded.mp4", "custom-encode.mp4"]
    )
    @pytest.mark.parametrize(
        "prefix",
        [
            pytest.param("tv/42/", id="legacy-flat"),
            pytest.param("001/234/567/", id="nested-v2"),
        ],
    )
    def test_lanterns_already_encoded_upload_and_publish_real_subtitle_tracks(
        self, mocker, temp_directory, configured_suffix, prefix
    ):
        mocker.patch("tv_runner.B2_ENABLED", True)
        mocker.patch("utils.MEDIAVIEWER_SUFFIX", configured_suffix)
        stem = "Lanterns.S01E01.1080p.WEBRip.10Bit.DDP5.1.x265-NeoNoir.mp4.ALFRED-ENCODED.mp4"
        video = temp_directory / f"{stem}.{configured_suffix}"
        video.write_bytes(b"video")
        subtitles = [temp_directory / f"{stem}-{track}.vtt" for track in (0, 1)]
        for subtitle in subtitles:
            subtitle.write_bytes(b"subtitle")
        (temp_directory / f"{stem.replace('S01E01', 'S01E02')}-0.vtt").write_bytes(
            b"decoy"
        )
        mocker.patch("tv_runner.stripUnicode", return_value=video)
        mocker.patch(
            "tv_runner.makeFileStreamable",
            side_effect=AlreadyEncoded("new unpublished"),
        )
        transfers = []
        client = mocker.patch("tv_runner.b2.get_b2_client").return_value
        client.upload_file.side_effect = lambda *args: transfers.append(args)
        record = mocker.patch("tv_runner.MediaFile.post_media_file")
        remote_names = set()

        self.tvRunner.updateFileRecords(
            temp_directory,
            {video.name},
            remote_names,
            media_path_details=[
                {
                    "pk": 42,
                    "path": "b2://bucket/Show/",
                    "skip": False,
                    "bucket": "bucket",
                    "b2_upload_prefix": prefix,
                    "media_files": [],
                }
            ],
        )

        video_uuid = record.call_args.kwargs["b2_uuid"]
        posted_subtitles = record.call_args.kwargs["subtitle_files"]
        assert record.call_args.args[0] == video.name
        assert str(uuid.UUID(video_uuid)) == video_uuid
        assert len(posted_subtitles) == 2
        assert {Path(upload[0]).name for upload in transfers[1:]} == {
            p.name for p in subtitles
        }
        assert {upload[2] for upload in transfers[1:]} == {
            f"{prefix}{name}" for name in posted_subtitles
        }
        assert transfers[0][2] == f"{prefix}{video_uuid}{video.suffix}"
        assert all(
            upload[1] == "bucket" and upload[2].startswith(prefix)
            for upload in transfers
        )
        assert all("Lanterns" not in upload[2] for upload in transfers)
        assert remote_names == {video.name}

    def test_lanterns_subtitle_upload_failure_does_not_publish_or_complete(
        self, mocker, temp_directory
    ):
        mocker.patch("tv_runner.B2_ENABLED", True)
        prefix = "tv/42/"
        stem = "Lanterns.S01E01.1080p.WEBRip.10Bit.DDP5.1.x265-NeoNoir.mp4.ALFRED-ENCODED.mp4"
        video = temp_directory / f"{stem}.mv-encoded.mp4"
        subtitle = temp_directory / f"{stem}-0.vtt"
        video.write_bytes(b"video")
        subtitle.write_bytes(b"subtitle")
        mocker.patch("tv_runner.stripUnicode", return_value=video)
        mocker.patch(
            "tv_runner.makeFileStreamable",
            side_effect=AlreadyEncoded("new unpublished"),
        )
        client = mocker.patch("tv_runner.b2.get_b2_client").return_value
        client.upload_file.side_effect = lambda _file, _bucket, key: (
            (_ for _ in ()).throw(RuntimeError("subtitle upload failed"))
            if key.endswith(".vtt")
            else None
        )
        record = mocker.patch("tv_runner.MediaFile.post_media_file")
        remote_names = set()

        with pytest.raises(RuntimeError, match="subtitle upload failed"):
            self.tvRunner.updateFileRecords(
                temp_directory,
                {video.name},
                remote_names,
                media_path_details=[
                    {
                        "pk": 42,
                        "path": "b2://bucket/Show/",
                        "skip": False,
                        "bucket": "bucket",
                        "b2_upload_prefix": prefix,
                        "media_files": [],
                    }
                ],
            )

        record.assert_not_called()
        assert remote_names == set()
        assert video.exists() and subtitle.exists()

    @pytest.mark.parametrize(
        ("filename", "exists"), [("episode.mkv", True), ("episode.mp4", False)]
    )
    def test_already_encoded_non_mp4_or_missing_skips(
        self, mocker, temp_directory, filename, exists
    ):
        mocker.patch("tv_runner.B2_ENABLED", True)
        path = temp_directory / filename
        if exists:
            path.write_bytes(b"media")
        mocker.patch("tv_runner.stripUnicode", return_value=path)
        mocker.patch(
            "tv_runner.makeFileStreamable", side_effect=AlreadyEncoded("already")
        )
        upload = mocker.patch("tv_runner.b2.get_b2_client")
        post = mocker.patch("tv_runner.MediaFile.post_media_file")

        self.tvRunner.updateFileRecords(
            temp_directory,
            {filename},
            set(),
            media_path_details=[
                {
                    "pk": 1,
                    "path": "b2://bucket/Show/",
                    "bucket": "bucket",
                    "b2_upload_prefix": "tv/42/",
                }
            ],
        )

        upload.assert_not_called()
        post.assert_not_called()

    @pytest.mark.parametrize("error", [SkipProcessing("skip"), EncoderException("bad")])
    def test_skip_processing_and_encoder_error_do_not_upload(
        self, mocker, temp_directory, error
    ):
        mocker.patch("tv_runner.B2_ENABLED", True)
        source = temp_directory / "episode.mkv"
        source.write_bytes(b"source")
        mocker.patch("tv_runner.stripUnicode", return_value=source)
        mocker.patch("tv_runner.makeFileStreamable", side_effect=error)
        upload = mocker.patch("tv_runner.b2.get_b2_client")
        post = mocker.patch("tv_runner.MediaFile.post_media_file")

        self.tvRunner.updateFileRecords(
            temp_directory,
            {source.name},
            set(),
            media_path_details=[
                {
                    "pk": 1,
                    "path": "b2://bucket/Show/",
                    "bucket": "bucket",
                    "b2_upload_prefix": "tv/42/",
                }
            ],
        )

        upload.assert_not_called()
        post.assert_not_called()

    def test_ambiguous_paths_prefer_configured_destination_when_present(self, mocker):
        mocker.patch(
            "tv_runner.get_b2_uri_for_local_path",
            return_value="b2://configured/prefix/Show/",
        )
        destination = self.tvRunner._select_b2_destination(
            "/local/Show",
            [
                {
                    "pk": 1,
                    "path": "b2://other/Show/",
                    "bucket": "other",
                    "b2_upload_prefix": "other/42/",
                },
                {
                    "pk": 2,
                    "path": "b2://configured/prefix/Show/",
                    "bucket": "configured",
                    "b2_upload_prefix": "custom/42/",
                },
            ],
        )

        assert destination["pk"] == 2
        assert destination["bucket"] == "configured"
        assert destination["b2_upload_prefix"] == "custom/42/"

    def test_b2_disabled_and_existing_remote_names_are_not_uploaded(
        self, mocker, temp_directory
    ):
        mocker.patch("tv_runner.B2_ENABLED", False)
        mocker.patch(
            "tv_runner.TvRunner.get_or_create_media_path",
            return_value={"pk": 1, "skip": False},
        )
        source = temp_directory / "episode.mkv"
        encoded = temp_directory / "episode.mp4"
        source.write_bytes(b"source")
        encoded.write_bytes(b"encoded")
        mocker.patch("tv_runner.stripUnicode", return_value=source)
        encode = mocker.patch("tv_runner.makeFileStreamable", return_value=encoded)
        upload = mocker.patch("tv_runner.b2.get_b2_client")
        post = mocker.patch("tv_runner.MediaFile.post_media_file")

        self.tvRunner.updateFileRecords(
            temp_directory,
            {source.name},
            {encoded.name},
        )

        encode.assert_called_once()
        upload.assert_not_called()
        post.assert_not_called()

    def test_b2_upload_uses_uuid_key_and_keeps_original_api_filename(
        self, mocker, temp_directory
    ):
        mocker.patch("tv_runner.B2_ENABLED", True)
        source = temp_directory / "episode.mkv"
        encoded = temp_directory / "episode.converted.mp4"
        source.write_bytes(b"source")
        encoded.write_bytes(b"encoded")
        mocker.patch("tv_runner.stripUnicode", return_value=source)
        mocker.patch("tv_runner.makeFileStreamable", return_value=encoded)
        upload = mocker.patch("tv_runner.b2.get_b2_client")
        mocker.patch("tv_runner.upload_subtitle_files", return_value=[])
        post = mocker.patch("tv_runner.MediaFile.post_media_file")

        self.tvRunner.updateFileRecords(
            temp_directory,
            {source.name},
            set(),
            media_path_details=[
                {
                    "pk": 9,
                    "path": "b2://remote/archive/Show/",
                    "bucket": "remote",
                    "b2_upload_prefix": "archive/42/",
                }
            ],
        )

        key = upload.return_value.upload_file.call_args.args[2]
        assert key.startswith("archive/42/")
        assert key.endswith(encoded.suffix)
        assert encoded.name not in key
        post.assert_called_once()
        assert post.call_args.args[:2] == (encoded.name, 9)
        assert post.call_args.kwargs["b2_uuid"] == key.removeprefix(
            "archive/42/"
        ).removesuffix(encoded.suffix)

    def test_existing_source_filename_is_ignored(self, mocker, temp_directory):
        mocker.patch("tv_runner.B2_ENABLED", True)
        encode = mocker.patch("tv_runner.makeFileStreamable")
        upload = mocker.patch("tv_runner.b2.get_b2_client")
        post = mocker.patch("tv_runner.MediaFile.post_media_file")

        self.tvRunner.updateFileRecords(
            temp_directory,
            {"episode.mkv"},
            {"episode.mkv"},
            media_path_details=[
                {
                    "pk": 1,
                    "path": "b2://bucket/Show/",
                    "bucket": "bucket",
                    "b2_upload_prefix": "tv/42/",
                }
            ],
        )

        encode.assert_not_called()
        upload.assert_not_called()
        post.assert_not_called()

    def test_select_ambiguous_b2_paths_fails(self):
        with pytest.raises(ValueError, match="Ambiguous B2 media paths"):
            self.tvRunner._select_b2_destination(
                "/local/Show",
                [
                    {
                        "pk": 1,
                        "path": "b2://one/Show/",
                        "bucket": "one",
                        "b2_upload_prefix": "one/42/",
                    },
                    {
                        "pk": 2,
                        "path": "b2://two/Show/",
                        "bucket": "two",
                        "b2_upload_prefix": "two/42/",
                    },
                ],
            )

    def test_get_all_tv_b2_reverse_mapping(self, mocker, temp_directory):
        mocker.patch("utils.BASE_PATH", temp_directory)
        mocker.patch("tv_runner.LOCAL_TV_SHOWS_PATHS", ["tv_shows"])
        local_dir = temp_directory / "tv_shows" / "Show.Name"
        local_dir.mkdir(parents=True)

        mock_response = mock.MagicMock()
        mock_response.json.return_value = {
            "results": [
                {
                    "media_paths": [{"pk": 1, "path": "b2://bucket/prefix/Show.Name/"}],
                    "finished": False,
                }
            ],
            "next": "",
        }
        mocker.patch("tv_runner.get_data", return_value=mock_response)

        paths = Tv.get_all_tv()

        assert paths == {local_dir: {"pks": {1}, "finished": False}}

    def test_get_all_media_paths_follows_pages(self, mocker):
        first = mock.Mock()
        first.json.return_value = {"results": [{"pk": 1}], "next": "page-2"}
        second = mock.Mock()
        second.json.return_value = {"results": [{"pk": 2}], "next": ""}
        get = mocker.patch("tv_runner.get_data", side_effect=[first, second])

        assert Tv.get_all_media_paths() == [{"pk": 1}, {"pk": 2}]
        assert get.call_args_list == [
            call(Tv.MEDIAVIEWER_MEDIAPATH_URL),
            call("page-2"),
        ]

    def test_media_file_inventory_follows_all_pages_and_includes_primary_names(
        self, mocker
    ):
        from tv_runner import MediaFile

        first = mock.Mock()
        first.json.return_value = {
            "results": [
                {"filename": "legacy.mp4", "media_files": ["hidden-like.mkv"]},
                {"filename": None, "media_files": []},
            ],
            "next": "tv-page-2",
        }
        second = mock.Mock()
        second.json.return_value = {
            "results": [{"filename": "movie.mp4", "media_files": ["movie.vtt"]}],
            "next": "",
        }
        third = mock.Mock()
        third.json.return_value = {
            "results": [{"filename": "old-movie.mp4", "media_files": []}],
            "next": None,
        }
        mocker.stopall()
        get = mocker.patch("tv_runner.get_data", side_effect=[first, second, third])

        assert MediaFile.get_all_filenames() == {
            "legacy.mp4",
            "hidden-like.mkv",
            "movie.mp4",
            "movie.vtt",
            "old-movie.mp4",
        }
        from settings import DOMAIN

        assert get.call_args_list == [
            call(f"{DOMAIN}/mediaviewer/api/tvmediapath/"),
            call("tv-page-2"),
            call(f"{DOMAIN}/mediaviewer/api/moviemediapath/"),
        ]

    def test_unsorted_remote_file_creates_and_uploads_without_local_show_path(
        self, mocker, temp_directory
    ):
        mocker.patch("tv_runner.B2_ENABLED", True)
        mocker.patch("tv_runner.UNSORTED_PATHS", [str(temp_directory)])
        mocker.patch("tv_runner.MINIMUM_FILE_SIZE", 0)
        mocker.patch(
            "tv_runner.get_media_path_by_filename",
            return_value="b2://remote-bucket/deep/Show.Name/",
        )
        mocker.patch("tv_runner.Tv.get_all_media_paths", return_value=[])
        mock_create = mocker.patch(
            "tv_runner.Tv.post_media_path",
            return_value={
                "pk": 77,
                "skip": False,
                "bucket": "remote-bucket",
                "b2_upload_prefix": "deep/77/",
            },
        )
        mocker.patch(
            "tv_runner.TvRunner.load_paths",
            side_effect=lambda: setattr(self.tvRunner, "paths", {}),
        )
        mocker.stop(self.mock_sort_unsorted_files)
        sources = [
            temp_directory / "Show.Name.S01E01.mkv",
            temp_directory / "Show.Name.S01E02.mkv",
        ]
        outputs = [source.with_suffix(".mp4") for source in sources]
        for source in sources:
            source.write_bytes(b"source")

        def encode(source, **kwargs):
            output = Path(source).with_suffix(".mp4")
            output.write_bytes(b"encoded")
            return output

        mocker.patch("tv_runner.makeFileStreamable", side_effect=encode)
        mocker.patch(
            "tv_runner.stripUnicode",
            side_effect=lambda filename, path: Path(path) / filename,
        )
        mock_upload = mocker.patch("tv_runner.b2.get_b2_client")
        mocker.patch("tv_runner.upload_subtitle_files", return_value=["episode.vtt"])
        mock_record = mocker.patch("tv_runner.MediaFile.post_media_file")

        self.tvRunner.run()

        mock_create.assert_called_once_with("b2://remote-bucket/deep/Show.Name/")
        assert mock_create.call_count == 1
        assert mock_upload.return_value.upload_file.call_count == 2
        assert mock_record.call_count == 2
        assert {record.args[0] for record in mock_record.call_args_list} == {
            output.name for output in outputs
        }
        assert all(
            record.args[1:] == (77, len(b"encoded"))
            and record.kwargs["subtitle_files"] == ["episode.vtt"]
            and record.kwargs["b2_uuid"]
            for record in mock_record.call_args_list
        )

    @pytest.mark.parametrize(
        "prefix",
        [
            pytest.param("nested/12/", id="legacy-flat"),
            pytest.param("001/234/567/", id="nested-v2"),
        ],
    )
    def test_unsorted_existing_remote_path_uses_detail_pk(
        self, mocker, temp_directory, prefix
    ):
        mocker.patch("tv_runner.B2_ENABLED", True)
        mocker.patch("tv_runner.UNSORTED_PATHS", [str(temp_directory)])
        mocker.patch("tv_runner.MINIMUM_FILE_SIZE", 0)
        uri = "b2://stored-bucket/nested/Show.Name"
        inferred_uri = mocker.patch(
            "tv_runner.get_media_path_by_filename", return_value=f"{uri}/"
        )
        mocker.patch(
            "tv_runner.Tv.get_all_media_paths",
            return_value=[
                {
                    "pk": 12,
                    "path": uri,
                    "bucket": "stored-bucket",
                    "b2_upload_prefix": prefix,
                }
            ],
        )
        detail = {
            "pk": 12,
            "path": uri,
            "skip": False,
            "media_files": [],
            "bucket": "stored-bucket",
            "b2_upload_prefix": prefix,
        }
        get_detail = mocker.patch("tv_runner.Tv.get_media_path", return_value=detail)
        mocker.patch(
            "tv_runner.TvRunner.load_paths",
            side_effect=lambda: setattr(self.tvRunner, "paths", {}),
        )
        mocker.stop(self.mock_sort_unsorted_files)
        source = temp_directory / "Show.Name.S01E03.mkv"
        output = temp_directory / "Show.Name.S01E03.mp4"
        source.write_bytes(b"source")

        def encode(source, **kwargs):
            output.write_bytes(b"encoded")
            return output

        mocker.patch("tv_runner.makeFileStreamable", side_effect=encode)
        mocker.patch("tv_runner.stripUnicode", return_value=source)
        mock_upload = mocker.patch("tv_runner.b2.get_b2_client")
        mocker.patch("tv_runner.upload_subtitle_files", return_value=[])
        mock_record = mocker.patch("tv_runner.MediaFile.post_media_file")
        mock_create = mocker.patch("tv_runner.Tv.post_media_path")

        self.tvRunner.run()

        get_detail.assert_called_once_with(12)
        inferred_uri.assert_called_once_with(source.name)
        key = mock_upload.return_value.upload_file.call_args.args[2]
        assert key.startswith(prefix) and key.endswith(".mp4")
        assert "Show.Name" not in key
        mock_record.assert_called_once()
        assert mock_record.call_args.kwargs["b2_uuid"] == key.removeprefix(
            prefix
        ).removesuffix(".mp4")
        mock_create.assert_not_called()

    def test_unsorted_local_inference_maps_and_uses_created_destination(
        self, mocker, temp_directory
    ):
        mocker.patch("tv_runner.B2_ENABLED", True)
        mocker.patch("tv_runner.UNSORTED_PATHS", [str(temp_directory)])
        mocker.patch("tv_runner.MINIMUM_FILE_SIZE", 0)
        mocker.patch("utils.B2_BUCKET_NAME", "configured-bucket")
        mocker.patch("utils.B2_NAME_PREFIX", "configured-prefix/")
        mocker.patch(
            "tv_runner.get_media_path_by_filename", return_value="/tv/Show.Name/"
        )
        mapped_uri = "b2://configured-bucket/configured-prefix/Show.Name/"
        mocker.patch("tv_runner.Tv.get_all_media_paths", return_value=[])
        create = mocker.patch(
            "tv_runner.Tv.post_media_path",
            return_value={
                "pk": 77,
                "skip": False,
                "bucket": "configured-bucket",
                "b2_upload_prefix": "tv/77/",
            },
        )
        source = temp_directory / "Show.Name.S01E01.mkv"
        output = temp_directory / "Show.Name.S01E01.mp4"
        source.write_bytes(b"source")

        def encode(*args, **kwargs):
            output.write_bytes(b"encoded")
            return output

        mocker.patch("tv_runner.makeFileStreamable", side_effect=encode)
        mocker.patch("tv_runner.stripUnicode", return_value=source)
        upload = mocker.patch("tv_runner.b2.get_b2_client")
        mocker.patch("tv_runner.upload_subtitle_files", return_value=[])
        record = mocker.patch("tv_runner.MediaFile.post_media_file")
        mocker.stop(self.mock_sort_unsorted_files)

        self.tvRunner._sort_unsorted_files()

        create.assert_called_once_with(mapped_uri)
        key = upload.return_value.upload_file.call_args.args[2]
        assert key.startswith("tv/77/") and key.endswith(".mp4")
        assert "Show.Name" not in key
        record.assert_called_once()
        assert record.call_args.kwargs["b2_uuid"] == key.removeprefix(
            "tv/77/"
        ).removesuffix(".mp4")

    def test_unsorted_local_inference_reuses_mapped_destination(
        self, mocker, temp_directory
    ):
        mocker.patch("tv_runner.B2_ENABLED", True)
        mocker.patch("tv_runner.UNSORTED_PATHS", [str(temp_directory)])
        mocker.patch("tv_runner.MINIMUM_FILE_SIZE", 0)
        mocker.patch(
            "tv_runner.get_media_path_by_filename", return_value="/tv/Show.Name/"
        )
        mapped_uri = "b2://configured-bucket/configured-prefix/Show.Name/"
        mocker.patch("utils.B2_BUCKET_NAME", "configured-bucket")
        mocker.patch("utils.B2_NAME_PREFIX", "configured-prefix/")
        mocker.patch(
            "tv_runner.Tv.get_all_media_paths",
            return_value=[
                {
                    "pk": 12,
                    "path": mapped_uri,
                    "bucket": "configured-bucket",
                    "b2_upload_prefix": "configured-prefix/12/",
                }
            ],
        )
        detail = {
            "pk": 12,
            "path": mapped_uri,
            "skip": False,
            "media_files": [],
            "bucket": "configured-bucket",
            "b2_upload_prefix": "configured-prefix/12/",
        }
        get_detail = mocker.patch("tv_runner.Tv.get_media_path", return_value=detail)
        create = mocker.patch("tv_runner.Tv.post_media_path")
        source = temp_directory / "Show.Name.S01E02.mkv"
        output = temp_directory / "Show.Name.S01E02.mp4"
        source.write_bytes(b"source")

        def encode(*args, **kwargs):
            output.write_bytes(b"encoded")
            return output

        mocker.patch("tv_runner.makeFileStreamable", side_effect=encode)
        mocker.patch("tv_runner.stripUnicode", return_value=source)
        upload = mocker.patch("tv_runner.b2.get_b2_client")
        mocker.patch("tv_runner.upload_subtitle_files", return_value=[])
        record = mocker.patch("tv_runner.MediaFile.post_media_file")
        mocker.stop(self.mock_sort_unsorted_files)

        self.tvRunner._sort_unsorted_files()

        get_detail.assert_called_once_with(12)
        create.assert_not_called()
        key = upload.return_value.upload_file.call_args.args[2]
        assert key.startswith("configured-prefix/12/") and key.endswith(".mp4")
        assert "Show.Name" not in key
        record.assert_called_once()
        assert record.call_args.kwargs["b2_uuid"] == key.removeprefix(
            "configured-prefix/12/"
        ).removesuffix(".mp4")

    def test_unsorted_local_inference_dry_run_does_not_write(
        self, mocker, temp_directory
    ):
        mocker.patch("tv_runner.B2_ENABLED", True)
        mocker.patch("tv_runner.UNSORTED_PATHS", [str(temp_directory)])
        mocker.patch("tv_runner.MINIMUM_FILE_SIZE", 0)
        mocker.patch(
            "tv_runner.get_media_path_by_filename", return_value="/tv/Show.Name/"
        )
        mocker.patch(
            "tv_runner.get_b2_uri_for_local_path",
            return_value="b2://bucket/prefix/Show.Name/",
        )
        mocker.patch("tv_runner.Tv.get_all_media_paths", return_value=[])
        source = temp_directory / "episode.mkv"
        source.write_bytes(b"video")
        create = mocker.patch("tv_runner.Tv.post_media_path")
        encode = mocker.patch("tv_runner.makeFileStreamable")
        upload = mocker.patch("tv_runner.b2.get_b2_client")
        post_file = mocker.patch("tv_runner.MediaFile.post_media_file")
        mocker.stop(self.mock_sort_unsorted_files)

        self.tvRunner._sort_unsorted_files(dry_run=True)

        create.assert_not_called()
        encode.assert_not_called()
        upload.assert_not_called()
        post_file.assert_not_called()

    def test_unsorted_skip_and_dry_run_do_not_mutate(self, mocker, temp_directory):
        mocker.patch("tv_runner.B2_ENABLED", True)
        mocker.patch("tv_runner.UNSORTED_PATHS", [str(temp_directory)])
        mocker.patch("tv_runner.MINIMUM_FILE_SIZE", 0)
        mocker.patch(
            "tv_runner.get_media_path_by_filename",
            return_value="b2://bucket/Show/",
        )
        mocker.patch(
            "tv_runner.Tv.get_all_media_paths",
            return_value=[
                {
                    "pk": 4,
                    "path": "b2://bucket/Show/",
                    "bucket": "bucket",
                    "b2_upload_prefix": "tv/4/",
                }
            ],
        )
        mocker.patch(
            "tv_runner.Tv.get_media_path",
            return_value={
                "pk": 4,
                "path": "b2://bucket/Show/",
                "skip": False,
                "media_files": [],
                "bucket": "bucket",
                "b2_upload_prefix": "tv/4/",
            },
        )
        source = temp_directory / "episode.mkv"
        source.write_bytes(b"video")
        encode = mocker.patch("tv_runner.makeFileStreamable")
        upload = mocker.patch("tv_runner.b2.get_b2_client")
        post_file = mocker.patch("tv_runner.MediaFile.post_media_file")
        post_path = mocker.patch("tv_runner.Tv.post_media_path")
        mocker.stop(self.mock_sort_unsorted_files)

        self.tvRunner._sort_unsorted_files(dry_run=True)

        assert source.exists()
        encode.assert_not_called()
        upload.assert_not_called()
        post_file.assert_not_called()
        post_path.assert_not_called()

    def test_unsorted_dry_run_missing_destination_does_not_create_or_encode(
        self, mocker, temp_directory
    ):
        mocker.patch("tv_runner.B2_ENABLED", True)
        mocker.patch("tv_runner.UNSORTED_PATHS", [str(temp_directory)])
        mocker.patch("tv_runner.MINIMUM_FILE_SIZE", 0)
        mocker.patch(
            "tv_runner.get_media_path_by_filename",
            return_value="b2://bucket/new/Show/",
        )
        mocker.patch("tv_runner.Tv.get_all_media_paths", return_value=[])
        source = temp_directory / "episode.mkv"
        source.write_bytes(b"video")
        encode = mocker.patch("tv_runner.makeFileStreamable")
        upload = mocker.patch("tv_runner.b2.get_b2_client")
        post_file = mocker.patch("tv_runner.MediaFile.post_media_file")
        post_path = mocker.patch("tv_runner.Tv.post_media_path")
        mocker.stop(self.mock_sort_unsorted_files)

        self.tvRunner._sort_unsorted_files(dry_run=True)

        assert source.exists()
        encode.assert_not_called()
        upload.assert_not_called()
        post_file.assert_not_called()
        post_path.assert_not_called()

    def test_unsorted_duplicate_encoded_name_uploads_and_records_once(
        self, mocker, temp_directory
    ):
        mocker.patch("tv_runner.B2_ENABLED", True)
        mocker.patch("tv_runner.UNSORTED_PATHS", [str(temp_directory)])
        mocker.patch("tv_runner.MINIMUM_FILE_SIZE", 0)
        mocker.patch(
            "tv_runner.get_media_path_by_filename",
            return_value="b2://bucket/Show/",
        )
        mocker.patch("tv_runner.Tv.get_all_media_paths", return_value=[])
        mocker.patch(
            "tv_runner.Tv.post_media_path",
            return_value={
                "pk": 8,
                "skip": False,
                "bucket": "bucket",
                "b2_upload_prefix": "tv/8/",
            },
        )
        sources = [temp_directory / "first.mkv", temp_directory / "second.mkv"]
        for source in sources:
            source.write_bytes(b"video")
        output = temp_directory / "shared.mp4"

        def encode(source, **kwargs):
            output.write_bytes(b"encoded")
            return output

        mocker.patch("tv_runner.makeFileStreamable", side_effect=encode)
        mocker.patch(
            "tv_runner.stripUnicode",
            side_effect=lambda filename, path: Path(path) / filename,
        )
        upload = mocker.patch("tv_runner.b2.get_b2_client")
        mocker.patch("tv_runner.upload_subtitle_files", return_value=[])
        post_file = mocker.patch("tv_runner.MediaFile.post_media_file")
        mocker.stop(self.mock_sort_unsorted_files)

        self.tvRunner._sort_unsorted_files()

        key = upload.return_value.upload_file.call_args.args[2]
        assert key.startswith("tv/8/") and key.endswith(".mp4")
        assert "shared" not in key
        post_file.assert_called_once()
        assert post_file.call_args.kwargs["b2_uuid"] == key.removeprefix(
            "tv/8/"
        ).removesuffix(".mp4")

    @pytest.mark.parametrize("inferred", [None, "b2://bucket/?invalid"])
    def test_unsorted_invalid_inference_is_ignored(
        self, mocker, temp_directory, inferred
    ):
        mocker.patch("tv_runner.B2_ENABLED", True)
        mocker.patch("tv_runner.UNSORTED_PATHS", [str(temp_directory)])
        mocker.patch("tv_runner.MINIMUM_FILE_SIZE", 0)
        infer = mocker.patch(
            "tv_runner.get_media_path_by_filename", return_value=inferred
        )
        list_paths = mocker.patch("tv_runner.Tv.get_all_media_paths")
        source = temp_directory / "episode.mkv"
        source.write_bytes(b"video")
        (temp_directory / "captions.srt").write_text("subtitle")
        (temp_directory / "folder").mkdir()
        (temp_directory / "notes.txt").write_text("ignore")
        mocker.stop(self.mock_sort_unsorted_files)

        self.tvRunner._sort_unsorted_files()

        assert source.exists()
        infer.assert_called_once_with(source.name)
        list_paths.assert_not_called()


class TestGlobalFilenameInventory:
    @pytest.mark.parametrize(
        "payload",
        [
            {"results": []},
            {"next": None},
            {"next": None, "results": [{"filename": None}]},
            {"next": None, "results": [{"filename": 42, "media_files": []}]},
        ],
        ids=[
            "missing-next",
            "missing-results",
            "missing-media-files",
            "invalid-filename",
        ],
    )
    def test_malformed_inventory_payload_raises(self, mocker, payload):
        from tv_runner import MediaFile

        response = mock.Mock()
        response.json.return_value = payload
        mocker.patch("tv_runner.get_data", return_value=response)

        with pytest.raises(ValueError):
            MediaFile.get_all_filenames()

    def test_later_page_failure_raises_instead_of_returning_partial_inventory(
        self, mocker
    ):
        from tv_runner import MediaFile

        first = mock.Mock()
        first.json.return_value = {
            "results": [{"filename": "partial.mp4", "media_files": []}],
            "next": "later-page",
        }
        get = mocker.patch(
            "tv_runner.get_data",
            side_effect=[first, RuntimeError("page request failed")],
        )

        with pytest.raises(RuntimeError, match="page request failed"):
            MediaFile.get_all_filenames()

        assert get.call_count == 2

    def test_cyclic_pagination_raises(self, mocker):
        from tv_runner import MediaFile

        response = mock.Mock()
        response.json.return_value = {"results": [], "next": "page-1"}
        get = mocker.patch("tv_runner.get_data", return_value=response)

        with pytest.raises(ValueError, match="Cyclic MediaPath pagination"):
            MediaFile.get_all_filenames()

        assert get.call_count == 2

    def test_inventory_failure_prevents_tv_processing_writes(self, mocker, tmp_path):
        from tv_runner import TvRunner

        mocker.patch("tv_runner.B2_ENABLED", True)
        mocker.patch(
            "tv_runner.MediaFile.get_all_filenames",
            side_effect=RuntimeError("inventory unavailable"),
        )
        encode = mocker.patch("tv_runner.makeFileStreamable")
        create_path = mocker.patch("tv_runner.TvRunner.get_or_create_media_path")
        upload = mocker.patch("tv_runner.b2.get_b2_client")
        post_path = mocker.patch("tv_runner.Tv.post_media_path")
        post_file = mocker.patch("tv_runner.MediaFile.post_media_file")

        with pytest.raises(RuntimeError, match="inventory unavailable"):
            TvRunner().updateFileRecords(tmp_path, {"episode.mkv"}, set())

        encode.assert_not_called()
        create_path.assert_not_called()
        upload.assert_not_called()
        post_path.assert_not_called()
        post_file.assert_not_called()

    def test_run_refreshes_global_inventory_each_time(self, mocker):
        from tv_runner import TvRunner

        mocker.patch("tv_runner.B2_ENABLED", True)
        inventory = mocker.patch(
            "tv_runner.MediaFile.get_all_filenames",
            side_effect=[{"first.mp4"}, {"second.mp4"}],
        )
        runner = TvRunner()
        runner._sort_unsorted_files = mock.Mock()
        runner.load_paths = mock.Mock(side_effect=lambda: setattr(runner, "paths", {}))

        runner.run()
        assert runner._published_filenames == {"first.mp4"}
        runner.run()

        assert runner._published_filenames == {"second.mp4"}
        assert inventory.call_count == 2

    def test_filename_match_is_case_sensitive(self, mocker, tmp_path):
        from tv_runner import TvRunner

        mocker.patch("tv_runner.B2_ENABLED", True)
        mocker.patch(
            "tv_runner.MediaFile.get_all_filenames", return_value={"Episode.mkv"}
        )
        source = tmp_path / "episode.mkv"
        encoded = tmp_path / "episode.mp4"
        source.write_bytes(b"source")
        encoded.write_bytes(b"encoded")
        mocker.patch("tv_runner.stripUnicode", return_value=source)
        encode = mocker.patch("tv_runner.makeFileStreamable", return_value=encoded)
        mocker.patch(
            "tv_runner.TvRunner.get_or_create_media_path",
            return_value={
                "pk": 1,
                "skip": False,
                "bucket": "bucket",
                "b2_upload_prefix": "tv/1/",
            },
        )
        post = mocker.patch("tv_runner.MediaFile.post_media_file")
        mocker.patch("tv_runner.b2.get_b2_client")
        mocker.patch("tv_runner.upload_subtitle_files", return_value=[])

        TvRunner().updateFileRecords(tmp_path, {source.name}, set())

        encode.assert_called_once()
        post.assert_called_once()
