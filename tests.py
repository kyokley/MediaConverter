import unittest
import mock
from tv_runner import TvRunner

class TestTvRunner(unittest.TestCase):
    def setUp(self):
        self.tvRunner = TvRunner()

    @mock.patch('path.Path')
    def test_loadPaths(self, mock_path):
        fake_paths = [object() for i in xrange(3)]
        mock_path.getAllPaths.return_value = fake_paths
        self.tvRunner.loadPaths()
        self.assertEquals(fake_paths, self.tvRunner.paths)
