import pytest
from pathlib import Path

import mock
from mock import call
from tv_runner import TvRunner


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
