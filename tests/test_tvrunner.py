import unittest
import tempfile
import shutil
import os

import mock
from mock import call
from tv_runner import TvRunner, FIND_FAIL_STRING
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

    @mock.patch('tv_runner.os.path.basename', side_effect=lambda x: x)
    @mock.patch('tv_runner.commands.getoutput')
    def test_buildLocalFileSet_valid_path(self,
                                          mock_commands_getoutput,
                                          mock_os_path_basename):
        mock_commands_getoutput.return_value = 'asdf\nsdfg\ndfgh'

        test_path = 'test_path'
        expectedFileSet = set(['asdf',
                               'sdfg',
                               'dfgh'])

        actualFileSet = self.tvRunner.buildLocalFileSet(test_path)

        self.assertEquals(expectedFileSet, actualFileSet)

    @mock.patch('tv_runner.commands.getoutput')
    def test_buildLocalFileSet_invalid_path(self,
                                          mock_commands_getoutput,
                                          ):
        mock_commands_getoutput.return_value = FIND_FAIL_STRING
        test_path = 'test_path'

        self.assertRaises(Exception, self.tvRunner.buildLocalFileSet, test_path)

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
                  set(['remote', 'some', 'paths'])),
             call('asdf',
                  set(['paths', 'some']),
                  set(['remote', 'some', 'paths']))],
            any_order=True)
        self.assertEqual(2, self.tvRunner.updateFileRecords.call_count)

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
