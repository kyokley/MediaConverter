import pytest
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

    def test_run(self):
        test_data = {
            "asdf": [1],
            "sdfg": [12, 23],
        }
        self.tvRunner.paths = test_data
        self.tvRunner.load_paths = mock.MagicMock()

        self.tvRunner.buildLocalFileSet = mock.MagicMock()
        self.tvRunner.buildLocalFileSet.return_value = set(["some", "paths"])

        self.tvRunner.build_remote_media_file_set = mock.MagicMock()
        self.tvRunner.build_remote_media_file_set.return_value = set(
            ["some", "remote", "paths"]
        )

        self.tvRunner.updateFileRecords = mock.MagicMock()

        self.tvRunner.handleDirs = mock.MagicMock()

        self.tvRunner.run()

        self.mock_sort_unsorted_files.assert_called_once_with(dry_run=False)
        self.tvRunner.buildLocalFileSet.assert_has_calls(
            [call("sdfg"), call("asdf")], any_order=True
        )
        assert 2 == self.tvRunner.buildLocalFileSet.call_count
        self.tvRunner.build_remote_media_file_set.assert_has_calls(
            [call([1]), call([12, 23])], any_order=True
        )
        assert 2 == self.tvRunner.build_remote_media_file_set.call_count

        self.tvRunner.updateFileRecords.assert_has_calls(
            [
                call(
                    "sdfg",
                    set(["paths", "some"]),
                    set(["remote", "some", "paths"]),
                    dry_run=False,
                ),
                call(
                    "asdf",
                    set(["paths", "some"]),
                    set(["remote", "some", "paths"]),
                    dry_run=False,
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
        mock_post.return_value = {"pk": 1, "skip": False}
        mock_uri = mocker.patch("tv_runner.get_b2_uri_for_local_path")
        mock_uri.return_value = "b2://bucket/prefix/Show.Name/"

        result = TvRunner.get_or_create_media_path(Path("/base/tv_shows/Show.Name"))

        assert result == {"pk": 1, "skip": False}
        mock_uri.assert_called_once_with(Path("/base/tv_shows/Show.Name"))
        mock_post.assert_called_once_with("b2://bucket/prefix/Show.Name/")

    def test_get_or_create_media_path_b2_disabled(self, mocker):
        mocker.patch("tv_runner.B2_ENABLED", False)
        mock_post = mocker.patch("tv_runner.Tv.post_media_path")
        mock_post.return_value = {"pk": 1, "skip": False}

        result = TvRunner.get_or_create_media_path(Path("/base/tv_shows/Show.Name"))

        assert result == {"pk": 1, "skip": False}
        mock_post.assert_called_once_with(Path("/base/tv_shows/Show.Name"))

    def test_updateFileRecords_b2_enabled(self, mocker):
        mocker.patch("tv_runner.B2_ENABLED", True)
        mocker.patch("tv_runner.B2_BUCKET_NAME", "bucket")
        mocker.patch("tv_runner.B2_NAME_PREFIX", "prefix/")
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

        mock_get_or_create_media_path.return_value = {"pk": 1, "skip": False}
        mock_os_path_exists.return_value = True
        mock_os_path_getsize.return_value = 1
        mock_os_path_basename.return_value = "basename"
        mock_makeFileStreamable.return_value.name = "newfile"

        test_path = "/a/local/path"
        test_localFileSet = set(["newfile"])
        test_remoteFileSet = set()

        self.tvRunner.updateFileRecords(
            test_path, test_localFileSet, test_remoteFileSet
        )
        mock_upload.return_value.upload_file.assert_called_once_with(
            mock_makeFileStreamable(), "bucket", "prefix/path/newfile"
        )
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
        )

    def test_select_existing_b2_path(self, mocker):
        mocker.patch("tv_runner.B2_ENABLED", True)
        details = [
            {"pk": 9, "path": "b2://remote-bucket/archive/nested/Show/", "skip": False},
            {"pk": 3, "path": "b2://remote-bucket/archive/nested/Show/", "skip": False},
        ]

        destination = self.tvRunner._select_b2_destination("/local/Show", details)

        assert destination == {
            "pk": 3,
            "skip": False,
            "bucket": "remote-bucket",
            "key_prefix": "archive/nested/Show/",
        }

    @pytest.mark.parametrize(
        ("uri", "expected"),
        [
            ("b2://bucket/no-trailing", "no-trailing/"),
            ("b2://bucket/", ""),
            ("b2://bucket//literal/", "/literal/"),
            ("b2://bucket/a%2Fb/", "a%2Fb/"),
        ],
    )
    def test_b2_key_prefix_preserves_uri_path(self, uri, expected):
        destination = self.tvRunner._select_b2_destination(
            "/local/Show", [{"pk": 1, "path": uri}]
        )

        assert destination["key_prefix"] == expected

    def test_existing_b2_destination_uploads_and_records(self, mocker, temp_directory):
        mocker.patch("tv_runner.B2_ENABLED", True)
        mocker.patch("tv_runner.B2_BUCKET_NAME", "configured")
        mocker.patch("tv_runner.B2_NAME_PREFIX", "configured-prefix/")
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

        mock_upload.return_value.upload_file.assert_called_once_with(
            encoded, "remote-bucket", "archive/nested/Show/episode.mv-encoded.mp4"
        )
        mock_subtitles.assert_called_once_with(
            encoded,
            temp_directory,
            bucket="remote-bucket",
            key_prefix="archive/nested/Show/",
        )
        mock_post.assert_called_once_with(
            encoded.name, 42, len(b"encoded-video"), subtitle_files=["episode.vtt"]
        )
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
        mock_upload.return_value.upload_file.assert_called_once_with(
            encoded, "other-bucket", "deep/Show/episode.mp4"
        )
        mock_post.assert_called_once_with(
            encoded.name, 17, len(b"encoded"), subtitle_files=[]
        )
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
            media_path_details=[{"pk": 1, "path": "b2://bucket/Show/", "skip": False}],
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
            media_path_details=[{"pk": 1, "path": "b2://bucket/Show/", "skip": True}],
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
                    {"pk": 1, "path": "b2://bucket/Show/", "skip": False}
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

        with pytest.raises(RuntimeError, match="API failed"):
            self.tvRunner.updateFileRecords(temp_directory, {source.name}, set())

        assert encoded.exists()
        post.assert_called_once()

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
            media_path_details=[{"pk": 1, "path": "b2://bucket/Show/"}],
        )

        upload.return_value.upload_file.assert_called_once_with(
            video, "bucket", f"Show/{video.name}"
        )
        post.assert_called_once_with(video.name, 1, len(b"encoded"), subtitle_files=[])

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
            media_path_details=[{"pk": 1, "path": "b2://bucket/Show/"}],
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
            media_path_details=[{"pk": 1, "path": "b2://bucket/Show/"}],
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
                {"pk": 1, "path": "b2://other/Show/"},
                {"pk": 2, "path": "b2://configured/prefix/Show/"},
            ],
        )

        assert destination["pk"] == 2
        assert destination["bucket"] == "configured"

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

    def test_existing_source_filename_is_ignored(self, mocker, temp_directory):
        mocker.patch("tv_runner.B2_ENABLED", True)
        encode = mocker.patch("tv_runner.makeFileStreamable")
        upload = mocker.patch("tv_runner.b2.get_b2_client")
        post = mocker.patch("tv_runner.MediaFile.post_media_file")

        self.tvRunner.updateFileRecords(
            temp_directory,
            {"episode.mkv"},
            {"episode.mkv"},
            media_path_details=[{"pk": 1, "path": "b2://bucket/Show/"}],
        )

        encode.assert_not_called()
        upload.assert_not_called()
        post.assert_not_called()

    def test_select_ambiguous_b2_paths_fails(self):
        with pytest.raises(ValueError, match="Ambiguous B2 media paths"):
            self.tvRunner._select_b2_destination(
                "/local/Show",
                [
                    {"pk": 1, "path": "b2://one/Show/"},
                    {"pk": 2, "path": "b2://two/Show/"},
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
