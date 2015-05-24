import unittest
import mock
from tv_runner import TvRunner

class TestTvRunner(unittest.TestCase):
    def setUp(self):
        self.tvRunner = TvRunner()

    @mock.patch('tv_runner.Path')
    def test_loadPaths(self, mock_path):
        fake_paths = [object() for i in xrange(3)]
        mock_path.getAllPaths.return_value = fake_paths
        self.tvRunner.loadPaths()
        self.assertEquals(fake_paths, self.tvRunner.paths)

    @mock.patch('tv_runner.Path')
    def test_getOrCreateRemotePath(self, mock_path):
        expectedPathID = 123
        testData = {'results': [{'pk': expectedPathID}]}
        testPath = 'test path'
        
        mock_path.getPathByLocalPathAndRemotePath.return_value = testData

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
        mock_file.getFileSet = lambda x: testData.get(x)
        
        actualSet = self.tvRunner.buildRemoteFileSetForPathIDs([-1,
                                                                1,
                                                                12,
                                                                123])
        self.assertEquals(expectedSet, actualSet)

    @mock.patch('tv_runner.os.path.getsize')
    @mock.patch('tv_runner.os.path.exists')
    @mock.patch('tv_runner.TvRunner.getOrCreateRemotePath')
    @mock.patch('tv_runner.makeFileStreamable')
    @mock.patch('tv_runner.File', autospec=True)
    def test_updateFileRecords(self,
            mock_file,
            mock_makeFileStreamable,
            mock_getOrCreateRemotePath,
            mock_os_path_exists,
            mock_os_path_getsize):
        mock_getOrCreateRemotePath.return_value = 1
        mock_os_path_exists.return_value = True
        mock_os_path_getsize.return_value = 1

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
        pass
