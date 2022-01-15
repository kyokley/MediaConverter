import unittest
import tempfile
import shutil
import os

from path import Path


class TestGetLocalPathsFunctional(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.path = Path("localpath", "remotepath")

    def tearDown(self):
        shutil.rmtree(self.temp_dir)

    def test_path_does_not_exist(self):
        filepath = os.path.join(self.temp_dir, "test_file")
        expected = set()
        actual = self.path._buildLocalPaths([filepath])
        self.assertEqual(expected, actual)

    def test_paths_exist(self):
        files = set([tempfile.mkstemp(dir=self.temp_dir)[1] for i in range(3)])
        expected = files
        actual = self.path._buildLocalPaths([self.temp_dir])
        self.assertEqual(expected, actual)
