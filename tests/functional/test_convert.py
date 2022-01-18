import pytest
import tempfile
import shutil
import os

from convert import (
    _getFilesInDirectory,
)


class TestGetFilesInDirectory:
    @pytest.fixture(autouse=True)
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()

        yield
        shutil.rmtree(self.temp_dir)

    def test_path_does_not_exist(self):
        non_existent_path = os.path.join(self.temp_dir, "test_file")
        expected = set()
        actual = _getFilesInDirectory(non_existent_path)
        assert expected == actual

    def test_path_is_empty(self):
        expected = set()
        actual = _getFilesInDirectory(self.temp_dir)
        assert expected == actual

    def test_files_exist(self):
        files = [tempfile.mkstemp(dir=self.temp_dir) for i in range(3)]
        expected = set([x[1].encode("utf-8") for x in files])
        actual = _getFilesInDirectory(self.temp_dir)
        assert expected == actual

    def test_nested_files_exist(self):
        expected = set()
        dirs = [tempfile.mkdtemp(dir=self.temp_dir) for i in range(3)]
        for dir in dirs:
            files = [tempfile.mkstemp(dir=dir)[1].encode("utf-8") for i in range(3)]
            expected.update(files)

        actual = _getFilesInDirectory(self.temp_dir)
        assert expected == actual
