import pytest
from pathlib import Path

import mock
from mock import call
from tv_runner import TvRunner, Tv


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

    def test_get_or_create_media_path_s3_enabled(self, mocker):
        mocker.patch("tv_runner.S3_ENABLED", True)
        mock_post = mocker.patch("tv_runner.Tv.post_media_path")
        mock_post.return_value = {"pk": 1, "skip": False}
        mock_uri = mocker.patch("tv_runner.get_s3_uri_for_local_path")
        mock_uri.return_value = "s3://bucket/prefix/Show.Name/"

        result = TvRunner.get_or_create_media_path(Path("/base/tv_shows/Show.Name"))

        assert result == {"pk": 1, "skip": False}
        mock_uri.assert_called_once_with(Path("/base/tv_shows/Show.Name"))
        mock_post.assert_called_once_with("s3://bucket/prefix/Show.Name/")

    def test_get_or_create_media_path_s3_disabled(self, mocker):
        mocker.patch("tv_runner.S3_ENABLED", False)
        mock_post = mocker.patch("tv_runner.Tv.post_media_path")
        mock_post.return_value = {"pk": 1, "skip": False}

        result = TvRunner.get_or_create_media_path(Path("/base/tv_shows/Show.Name"))

        assert result == {"pk": 1, "skip": False}
        mock_post.assert_called_once_with(Path("/base/tv_shows/Show.Name"))

    def test_updateFileRecords_s3_enabled(self, mocker):
        mocker.patch("tv_runner.S3_ENABLED", True)
        mocker.patch("tv_runner.S3_BUCKET_NAME", "bucket")
        mocker.patch("tv_runner.S3_KEY_PREFIX", "prefix/")
        mock_upload = mocker.patch("tv_runner.s3.get_s3_client")
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
            mock_makeFileStreamable(), test_path
        )
        mock_post_media_file.assert_called_once_with(
            mock_makeFileStreamable().name,
            1,
            mock_makeFileStreamable().stat().st_size,
            subtitle_files=["subtitle.vtt"],
        )

    def test_get_all_tv_s3_reverse_mapping(self, mocker, temp_directory):
        mocker.patch("utils.BASE_PATH", temp_directory)
        mocker.patch("tv_runner.LOCAL_TV_SHOWS_PATHS", ["tv_shows"])
        local_dir = temp_directory / "tv_shows" / "Show.Name"
        local_dir.mkdir(parents=True)

        mock_response = mock.MagicMock()
        mock_response.json.return_value = {
            "results": [
                {
                    "media_paths": [{"pk": 1, "path": "s3://bucket/prefix/Show.Name/"}],
                    "finished": False,
                }
            ],
            "next": "",
        }
        mocker.patch("tv_runner.get_data", return_value=mock_response)

        paths = Tv.get_all_tv()

        assert paths == {local_dir: {"pks": {1}, "finished": False}}
