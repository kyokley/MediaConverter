import unittest
import tempfile
import shutil
import os

import mock
from mock import call
from tv_runner import TvRunner
from utils import MissingPathException

class TestTvRunner(unittest.TestCase):
    def setUp(self):
        self.tvRunner = TvRunner()

    @mock.patch('tv_runner.Path')
    def test_loadPaths(self, mock_path):
        fake_paths = [object() for i in xrange(3)]
        mock_path.getAllTVPaths.return_value = fake_paths
        self.tvRunner.loadPaths()
        self.assertEquals(fake_paths, self.tvRunner.paths)

    @mock.patch('tv_runner.Path')
    def test_getOrCreateRemotePath(self, mock_path):
        expectedPathID = 123
        testData = {'results': [{'pk': expectedPathID}]}
        testPath = 'test path'

        mock_path.getTVPathByLocalPathAndRemotePath.return_value = testData

        actualPathID = self.tvRunner.getOrCreateRemotePath(testPath)
        self.assertEquals(expectedPathID, actualPathID)

    @mock.patch('tv_runner.File')
    def test_buildRemoteFileSetForPathIDs(self, mock_file):
        testData = {-1: ['invalid'],
                    1: ['test1'],
                    12: ['test12'],
                    123: ['test123'],
                    }
        expectedSet = set(['test1',
                           'test12',
                           'test123',
                           ])
        mock_file.getTVFileSet = lambda x: testData.get(x)

        actualSet = self.tvRunner.buildRemoteFileSetForPathIDs([-1,
                                                                1,
                                                                12,
                                                                123])
        self.assertEquals(expectedSet, actualSet)

    # TODO: Switch to using setUp/tearDown patching
    @mock.patch('tv_runner.os.path.basename')
    @mock.patch('tv_runner.os.path.getsize')
    @mock.patch('tv_runner.os.path.exists')
    @mock.patch('tv_runner.TvRunner.getOrCreateRemotePath')
    @mock.patch('tv_runner.makeFileStreamable')
    @mock.patch('tv_runner.File')
    def test_updateFileRecords(self,
                               mock_file,
                               mock_makeFileStreamable,
                               mock_getOrCreateRemotePath,
                               mock_os_path_exists,
                               mock_os_path_getsize,
                               mock_os_path_basename):
        mock_getOrCreateRemotePath.return_value = 1
        mock_os_path_exists.return_value = True
        mock_os_path_getsize.return_value = 1
        mock_os_path_basename.return_value = 'basename'

        test_path = '/a/local/path'
        test_localFileSet = set(['file1',
                                 'file2',
                                 'file3',
                                 'newfile',
                                 ])
        test_remoteFileSet = set(['file1',
                                 'file2',
                                 'file3',
                                 ])

        self.tvRunner.updateFileRecords(test_path, test_localFileSet, test_remoteFileSet)
        mock_makeFileStreamable.assert_called_with('/a/local/path/newfile',
                                                   appendSuffix=True,
                                                   removeOriginal=True,
                                                   dryRun=False)
        mock_file.assert_called_with('basename',
                                     1,
                                     1,
                                     True)

    def test_run(self):
        test_data = {'asdf': [1],
                     'sdfg': [12, 23],
                     }
        self.tvRunner.paths = test_data
        self.tvRunner.loadPaths = mock.MagicMock()

        self.tvRunner.buildLocalFileSet = mock.MagicMock()
        self.tvRunner.buildLocalFileSet.return_value = set(['some', 'paths'])

        self.tvRunner.buildRemoteFileSetForPathIDs = mock.MagicMock()
        self.tvRunner.buildRemoteFileSetForPathIDs.return_value = set(['some', 'remote', 'paths'])

        self.tvRunner.updateFileRecords = mock.MagicMock()

        self.tvRunner.handleDirs = mock.MagicMock()

        self.tvRunner.run()

        self.tvRunner.buildLocalFileSet.assert_has_calls([call('sdfg'),
                                                          call('asdf')],
                                                          any_order=True)
        self.assertEqual(2, self.tvRunner.buildLocalFileSet.call_count)
        self.tvRunner.buildRemoteFileSetForPathIDs.assert_has_calls([call([1]),
                                                                     call([12, 23])],
                                                                     any_order=True)
        self.assertEqual(2, self.tvRunner.buildRemoteFileSetForPathIDs.call_count)

        self.tvRunner.updateFileRecords.assert_has_calls(
            [call('sdfg',
                  set(['paths', 'some']),
                  set(['remote', 'some', 'paths'])),
             call('asdf',
                  set(['paths', 'some']),
                  set(['remote', 'some', 'paths']))],
            any_order=True)
        self.assertEqual(2, self.tvRunner.updateFileRecords.call_count)

        self.tvRunner.handleDirs.assert_has_calls([call('sdfg'),
                                                   call('asdf')])

class TestBuildLocalFileSetFunctional(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()

        self.tv_runner = TvRunner()

    def tearDown(self):
        shutil.rmtree(self.temp_dir)

    def test_file_does_not_exist(self):
        path_name = os.path.join(self.temp_dir, 'test_file')
        self.assertRaises(MissingPathException,
                          self.tv_runner.buildLocalFileSet,
                          path_name)

    def test_files_exist(self):
        files = [tempfile.mkstemp(dir=self.temp_dir)
                    for i in xrange(3)]
        expected = set([os.path.basename(x[1]) for x in files])
        actual = self.tv_runner.buildLocalFileSet(self.temp_dir)
        self.assertEqual(expected, actual)

class TestHandlDirs(unittest.TestCase):
    def setUp(self):
        self.test_walk = [('/path/to/tv_path/Test.Dir.Path',
                              ['Test.Dir.Path.S04E03.WEBRip.x264-MV'],
                              ['Test.Dir.Path.S04E02.WEBRip.x264-MV.mp4']),
                          ('/path/to/tv_path/Test.Dir.Path/Test.Dir.Path.S04E03.WEBRip.x264-MV',
                              ['Subs'],
                              ['Test.Dir.Path.S04E03.WEBRip.x264-MV.mp4', 'info.txt']),
                          ('/path/to/tv_path/Test.Dir.Path/Test.Dir.Path.S04E03.WEBRip.x264-MV/Subs', [], ['2_Eng.srt'])]

        self.walk_patcher = mock.patch('tv_runner.os.walk')
        self.mock_walk = self.walk_patcher.start()
        self.mock_walk.return_value = self.test_walk

        self.exists_patcher = mock.patch('tv_runner.os.path.exists')
        self.mock_exists = self.exists_patcher.start()
        self.mock_exists.return_value = True

        self.isdir_patcher = mock.patch('tv_runner.os.path.isdir')
        self.mock_isdir = self.isdir_patcher.start()
        self.mock_isdir.side_effect = [False, True, True, True]

        self.rename_patcher = mock.patch('tv_runner.os.rename')
        self.mock_rename = self.rename_patcher.start()

        self.rmtree_patcher = mock.patch('tv_runner.shutil.rmtree')
        self.mock_rmtree = self.rmtree_patcher.start()

        self.tv_runner = TvRunner()

    def tearDown(self):
        self.walk_patcher.stop()
        self.exists_patcher.stop()
        self.isdir_patcher.stop()
        self.rename_patcher.stop()
        self.rmtree_patcher.stop()

    def test_path_does_not_exist(self):
        self.mock_exists.return_value = False
        self.tv_runner.handleDirs('/path/to/tv_path/Test.Dir.Path')
        self.assertFalse(self.mock_rename.called)
        self.assertFalse(self.mock_rmtree.called)

    def test_(self):
        self.tv_runner.handleDirs('/path/to/tv_path/Test.Dir.Path')
        self.mock_rename.assert_has_calls([mock.call('/path/to/tv_path/Test.Dir.Path/Test.Dir.Path.S04E03.WEBRip.x264-MV/Test.Dir.Path.S04E03.WEBRip.x264-MV.mp4',
                                                     '/path/to/tv_path/Test.Dir.Path/Test.Dir.Path.S04E03.WEBRip.x264-MV.mp4'),
                                           mock.call('/path/to/tv_path/Test.Dir.Path/Test.Dir.Path.S04E03.WEBRip.x264-MV/Subs/2_Eng.srt',
                                                     '/path/to/tv_path/Test.Dir.Path/Test.Dir.Path.S04E03.WEBRip.x264-MV.srt'),
                                           ])
        self.mock_rmtree.assert_called_once_with('/path/to/tv_path/Test.Dir.Path/Test.Dir.Path.S04E03.WEBRip.x264-MV')
