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

