import unittest
import mock
import tempfile
import os
import shutil

from tv_runner import TvRunner
from utils import MissingPathException


class TestBuildLocalFileSetFunctional(unittest.TestCase):
    def setUp(self):
        self.SMALL_FILE_SIZE_patcher = mock.patch("tv_runner.SMALL_FILE_SIZE", 201)
        self.SMALL_FILE_SIZE_patcher.start()

        self.temp_dir = tempfile.mkdtemp()

        self.tv_runner = TvRunner()

    def tearDown(self):
        self.SMALL_FILE_SIZE_patcher.stop()
        shutil.rmtree(self.temp_dir)

    def test_file_does_not_exist(self):
        path_name = os.path.join(self.temp_dir, "test_file")
        self.assertRaises(
            MissingPathException, self.tv_runner.buildLocalFileSet, path_name
        )

    def test_files_exist(self):
        files = [tempfile.mkstemp(dir=self.temp_dir) for i in range(4)]

        for i, file in enumerate(files):
            with open(file[1], "wb") as f:
                f.write(os.urandom(i * 100))

        expected = set(
            [os.path.basename(x[1]) for x in files if os.path.getsize(x[1]) > 201]
        )
        actual = self.tv_runner.buildLocalFileSet(self.temp_dir)
        self.assertEqual(expected, actual)
