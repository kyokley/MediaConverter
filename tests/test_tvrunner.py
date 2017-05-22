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

        self.Path_patcher = mock.patch('tv_runner.Path')
        self.mock_Path = self.Path_patcher.start()

        self.File_patcher = mock.patch('tv_runner.File')
        self.mock_File = self.File_patcher.start()

        self.basename_patcher = mock.patch('tv_runner.os.path.basename')
        self.mock_basename = self.basename_patcher.start()

        self.getsize_patcher = mock.patch('tv_runner.os.path.getsize')
        self.mock_getsize = self.getsize_patcher.start()

        self.exists_patcher = mock.patch('tv_runner.os.path.exists')
        self.mock_exists = self.exists_patcher.start()

        self.getOrCreateRemotePath_patcher = mock.patch('tv_runner.TvRunner.getOrCreateRemotePath')
        self.mock_getOrCreateRemotePath = self.getOrCreateRemotePath_patcher.start()

        self.makeFileStreamable_patcher = mock.patch('tv_runner.makeFileStreamable')
        self.mock_makeFileStreamable = self.makeFileStreamable_patcher.start()

        self.File_patcher = mock.patch('tv_runner.File')
        self.mock_File = self.File_patcher.start()

    def tearDown(self):
        self.File_patcher.stop()
        self.makeFileStreamable_patcher.stop()
        self.getOrCreateRemotePath_patcher.stop()
        self.exists_patcher.stop()
        self.getsize_patcher.stop()
        self.basename_patcher.stop()
        self.Path_patcher.stop()

    def test_loadPaths(self):
        fake_paths = [object() for i in xrange(3)]
        self.mock_Path.getAllTVPaths.return_value = fake_paths
        self.tvRunner.loadPaths()
        self.assertEquals(fake_paths, self.tvRunner.paths)

    def test_buildRemoteFileSetForPathIDs(self):
        testData = {-1: ['invalid'],
                    1: ['test1'],
                    12: ['test12'],
                    123: ['test123'],
                    }
        expectedSet = set(['test1',
                           'test12',
                           'test123',
                           ])
        self.mock_File.getTVFileSet = lambda x: testData.get(x)

        actualSet = self.tvRunner.buildRemoteFileSetForPathIDs([-1,
                                                                1,
                                                                12,
                                                                123])
        self.assertEquals(expectedSet, actualSet)

    def test_updateFileRecords(self):
        self.mock_getOrCreateRemotePath.return_value = 1
        self.mock_exists.return_value = True
        self.mock_getsize.return_value = 1
        self.mock_basename.return_value = 'basename'

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
        self.mock_makeFileStreamable.delay.assert_called_with('/a/local/path/newfile',
                                                              1,
                                                              appendSuffix=True,
                                                              removeOriginal=True,
                                                              dryRun=False)

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
                  set(['remote', 'some', 'paths']),
                  dryRun=False),
             call('asdf',
                  set(['paths', 'some']),
                  set(['remote', 'some', 'paths']),
                  dryRun=False)],
            any_order=True)
        self.assertEqual(2, self.tvRunner.updateFileRecords.call_count)

class TestTvRunnerGetOrCreateRemotePath(unittest.TestCase):
    def setUp(self):
        self.tvRunner = TvRunner()

        self.Path_patcher = mock.patch('tv_runner.Path')
        self.mock_Path = self.Path_patcher.start()

        self.File_patcher = mock.patch('tv_runner.File')
        self.mock_File = self.File_patcher.start()

        self.basename_patcher = mock.patch('tv_runner.os.path.basename')
        self.mock_basename = self.basename_patcher.start()

        self.getsize_patcher = mock.patch('tv_runner.os.path.getsize')
        self.mock_getsize = self.getsize_patcher.start()

        self.exists_patcher = mock.patch('tv_runner.os.path.exists')
        self.mock_exists = self.exists_patcher.start()

        self.makeFileStreamable_patcher = mock.patch('tv_runner.makeFileStreamable')
        self.mock_makeFileStreamable = self.makeFileStreamable_patcher.start()

        self.File_patcher = mock.patch('tv_runner.File')
        self.mock_File = self.File_patcher.start()

    def test_getOrCreateRemotePath(self):
        expectedPathID = 123
        testData = {'results': [{'pk': expectedPathID}]}
        testPath = 'test path'

        self.mock_Path.getTVPathByLocalPathAndRemotePath.return_value = testData

        actualPathID = self.tvRunner.getOrCreateRemotePath(testPath)
        self.assertEquals(expectedPathID, actualPathID)

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
