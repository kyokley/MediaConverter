import unittest
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

    def test_loadPaths(self, mocker):
        mock_path = mocker.patch("tv_runner.Path")

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

        mock_path.getAllTVPaths.return_value = fake_paths
        self.tvRunner.loadPaths()
        assert expected == self.tvRunner.paths

    def test_getOrCreateRemotePath(self, mocker):
        mock_path = mocker.patch("tv_runner.Path")

        expectedPathID = 123
        testData = {"results": [{"pk": expectedPathID}]}
        testPath = "test path"

        mock_path.getTVPathByLocalPathAndRemotePath.return_value = testData

        actualPathID = self.tvRunner.getOrCreateRemotePath(testPath)
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

    def test_updateFileRecords(
        self,
        mocker
    ):
        mock_file = mocker.patch("tv_runner.File")
        mock_makeFileStreamable = mocker.patch("tv_runner.makeFileStreamable")
        mock_getOrCreateRemotePath = mocker.patch("tv_runner.TvRunner.getOrCreateRemotePath")
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


class TestHandleDirs(unittest.TestCase):
    def setUp(self):
        self.SMALL_FILE_SIZE_patcher = mock.patch("tv_runner.SMALL_FILE_SIZE", 100)
        self.SMALL_FILE_SIZE_patcher.start()

        self.test_walk = [
            (
                "/path/to/tv_path/Test.Dir.Path",
                ["Test.Dir.Path.S04E03.WEBRip.x264-MV"],
                ["Test.Dir.Path.S04E02.WEBRip.x264-MV.mp4"],
            ),
            (
                "/path/to/tv_path/Test.Dir.Path/Test.Dir.Path.S04E03.WEBRip.x264-MV",
                ["Subs"],
                ["Test.Dir.Path.S04E03.WEBRip.x264-MV.mp4", "info.txt", "Small.mp4"],
            ),
            (
                "/path/to/tv_path/Test.Dir.Path/Test.Dir.Path.S04E03.WEBRip.x264-MV/Subs",
                [],
                ["2_Eng.srt"],
            ),
        ]

        self.walk_patcher = mock.patch("tv_runner.os.walk")
        self.mock_walk = self.walk_patcher.start()
        self.mock_walk.return_value = self.test_walk

        self.exists_patcher = mock.patch("tv_runner.os.path.exists")
        self.mock_exists = self.exists_patcher.start()
        self.mock_exists.return_value = True

        self.isdir_patcher = mock.patch("tv_runner.os.path.isdir")
        self.mock_isdir = self.isdir_patcher.start()
        self.mock_isdir.side_effect = [False, True, True, True, True]

        self.getsize_patcher = mock.patch("tv_runner.os.path.getsize")
        self.mock_getsize = self.getsize_patcher.start()
        self.mock_getsize.side_effect = [1000, 10]

        self.rename_patcher = mock.patch("tv_runner.os.rename")
        self.mock_rename = self.rename_patcher.start()

        self.rmtree_patcher = mock.patch("tv_runner.shutil.rmtree")
        self.mock_rmtree = self.rmtree_patcher.start()

        self.tv_runner = TvRunner()

    def tearDown(self):
        self.SMALL_FILE_SIZE_patcher.stop()
        self.walk_patcher.stop()
        self.exists_patcher.stop()
        self.isdir_patcher.stop()
        self.getsize_patcher.stop()
        self.rename_patcher.stop()
        self.rmtree_patcher.stop()

    def test_path_does_not_exist(self):
        self.mock_exists.return_value = False
        self.tv_runner.handleDirs("/path/to/tv_path/Test.Dir.Path")
        self.assertFalse(self.mock_rename.called)
        self.assertFalse(self.mock_rmtree.called)

    def test_handleDirs(self):
        self.tv_runner.handleDirs("/path/to/tv_path/Test.Dir.Path")
        self.mock_rename.assert_has_calls(
            [
                mock.call(
                    "/path/to/tv_path/Test.Dir.Path/Test.Dir.Path.S04E03.WEBRip.x264-MV/Test.Dir.Path.S04E03.WEBRip.x264-MV.mp4",
                    "/path/to/tv_path/Test.Dir.Path/Test.Dir.Path.S04E03.WEBRip.x264-MV.mp4",
                ),
                mock.call(
                    "/path/to/tv_path/Test.Dir.Path/Test.Dir.Path.S04E03.WEBRip.x264-MV/Subs/2_Eng.srt",
                    "/path/to/tv_path/Test.Dir.Path/Test.Dir.Path.S04E03.WEBRip.x264-MV.srt",
                ),
            ]
        )
        self.mock_rmtree.assert_called_once_with(
            "/path/to/tv_path/Test.Dir.Path/Test.Dir.Path.S04E03.WEBRip.x264-MV"
        )


class TestSortUnsortedFiles(unittest.TestCase):
    def setUp(self):
        self.UNSORTED_PATHS_patcher = mock.patch(
            "tv_runner.UNSORTED_PATHS", ["/path/to/unsorted"]
        )
        self.UNSORTED_PATHS_patcher.start()

        self.exists_patcher = mock.patch("tv_runner.os.path.exists")
        self.mock_exists = self.exists_patcher.start()

        self.listdir_patcher = mock.patch("tv_runner.os.listdir")
        self.mock_listdir = self.listdir_patcher.start()

        self.get_localpath_by_filename_patcher = mock.patch(
            "tv_runner.get_localpath_by_filename"
        )
        self.mock_get_localpath_by_filename = (
            self.get_localpath_by_filename_patcher.start()
        )

        self.move_patcher = mock.patch("tv_runner.shutil.move")
        self.mock_move = self.move_patcher.start()

        self.tv_runner = TvRunner()

    def tearDown(self):
        self.UNSORTED_PATHS_patcher.stop()
        self.exists_patcher.stop()
        self.listdir_patcher.stop()
        self.get_localpath_by_filename_patcher.stop()
        self.move_patcher.stop()

    def test_unsorted_path_does_not_exist(self):
        self.mock_exists.return_value = False

        expected = None
        actual = self.tv_runner._sort_unsorted_files()

        self.assertEqual(expected, actual)
        self.mock_exists.assert_called_once_with("/path/to/unsorted")
        self.assertFalse(self.mock_listdir.called)
        self.assertFalse(self.mock_get_localpath_by_filename.called)
        self.assertFalse(self.mock_move.called)

    def test_no_localpath_for_filename(self):
        self.mock_exists.return_value = True
        self.mock_listdir.return_value = ["new.show.s02e10"]
        self.mock_get_localpath_by_filename.return_value = None

        expected = None
        actual = self.tv_runner._sort_unsorted_files()

        self.assertEqual(expected, actual)
        self.mock_exists.assert_called_once_with("/path/to/unsorted")
        self.mock_get_localpath_by_filename.assert_called_once_with("new.show.s02e10")
        self.assertFalse(self.mock_move.called)

    def test_localpath_does_not_exist(self):
        self.mock_exists.side_effect = [True, False]
        self.mock_listdir.return_value = ["new.show.s02e10"]
        self.mock_get_localpath_by_filename.return_value = "/path/to/local/new.show"

        expected = None
        actual = self.tv_runner._sort_unsorted_files()

        self.assertEqual(expected, actual)
        self.mock_exists.assert_has_calls(
            [
                mock.call("/path/to/unsorted"),
                mock.call("/path/to/local/new.show"),
            ]
        )
        self.mock_get_localpath_by_filename.assert_called_once_with("new.show.s02e10")
        self.assertFalse(self.mock_move.called)

    def test_localpath_for_filename(self):
        self.mock_exists.return_value = True
        self.mock_listdir.return_value = ["new.show.s02e10"]
        self.mock_get_localpath_by_filename.return_value = "/path/to/local/new.show"

        expected = None
        actual = self.tv_runner._sort_unsorted_files()

        self.assertEqual(expected, actual)
        self.mock_exists.assert_has_calls(
            [
                mock.call("/path/to/unsorted"),
                mock.call("/path/to/local/new.show"),
            ]
        )
        self.mock_get_localpath_by_filename.assert_called_once_with("new.show.s02e10")
        self.mock_move.assert_called_once_with(
            "/path/to/unsorted/new.show.s02e10",
            "/path/to/local/new.show/new.show.s02e10",
        )
