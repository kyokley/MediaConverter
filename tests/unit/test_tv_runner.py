import pytest

import mock
from mock import call
from tv_runner import TvRunner


class TestTvRunner:
    @pytest.fixture(autouse=True)
    def setUp(self, mocker):
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

    def test_get_or_create_media_path(self, mocker):
        mock_tv = mocker.patch("tv_runner.Tv")

        expectedPathID = 123
        testData = {"pk": expectedPathID}
        testPath = "test path"

        mock_tv.post_media_path.return_value = testData

        actualPathID = self.tvRunner.get_or_create_media_path(testPath)
        assert expectedPathID == actualPathID

    def test_buildRemoteFileSetForPathIDs(self, mocker):
        mock_file = mocker.patch("tv_runner.File")

        testData = {
            -1: ["invalid"],
            1: ["test1"],
            12: ["test12"],
            123: ["test123"],
        }
        expectedSet = set(
            [
                "test1",
                "test12",
                "test123",
            ]
        )
        mock_file.getTVFileSet = lambda x: testData.get(x)

        actualSet = self.tvRunner.buildRemoteFileSetForPathIDs([-1, 1, 12, 123])
        assert expectedSet == actualSet

    def test_updateFileRecords(self, mocker):
        mock_file = mocker.patch("tv_runner.File")
        mock_makeFileStreamable = mocker.patch("tv_runner.makeFileStreamable")
        mock_getOrCreateRemotePath = mocker.patch(
            "tv_runner.TvRunner.getOrCreateRemotePath"
        )
        mock_os_path_exists = mocker.patch("tv_runner.os.path.exists")
        mock_os_path_getsize = mocker.patch("tv_runner.os.path.getsize")
        mock_os_path_basename = mocker.patch("tv_runner.os.path.basename")

        mock_getOrCreateRemotePath.return_value = 1
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
            "/a/local/path/newfile",
            appendSuffix=True,
            removeOriginal=True,
            dryRun=False,
        )
        mock_file.assert_called_with("basename", 1, 1, True)

    def test_run(self):
        test_data = {
            "asdf": [1],
            "sdfg": [12, 23],
        }
        self.tvRunner.paths = test_data
        self.tvRunner.loadPaths = mock.MagicMock()

        self.tvRunner.buildLocalFileSet = mock.MagicMock()
        self.tvRunner.buildLocalFileSet.return_value = set(["some", "paths"])

        self.tvRunner.buildRemoteFileSetForPathIDs = mock.MagicMock()
        self.tvRunner.buildRemoteFileSetForPathIDs.return_value = set(
            ["some", "remote", "paths"]
        )

        self.tvRunner.updateFileRecords = mock.MagicMock()

        self.tvRunner.handleDirs = mock.MagicMock()

        self.tvRunner.run()

        self.mock_sort_unsorted_files.assert_called_once_with()
        self.tvRunner.buildLocalFileSet.assert_has_calls(
            [call("sdfg"), call("asdf")], any_order=True
        )
        assert 2 == self.tvRunner.buildLocalFileSet.call_count
        self.tvRunner.buildRemoteFileSetForPathIDs.assert_has_calls(
            [call([1]), call([12, 23])], any_order=True
        )
        assert 2 == self.tvRunner.buildRemoteFileSetForPathIDs.call_count

        self.tvRunner.updateFileRecords.assert_has_calls(
            [
                call("sdfg", set(["paths", "some"]), set(["remote", "some", "paths"])),
                call("asdf", set(["paths", "some"]), set(["remote", "some", "paths"])),
            ],
            any_order=True,
        )
        assert 2 == self.tvRunner.updateFileRecords.call_count

        self.tvRunner.handleDirs.assert_has_calls([call("asdf"), call("sdfg")])
