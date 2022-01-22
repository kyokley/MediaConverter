import pytest
import tempfile
import shutil
import os


from settings import MEDIAVIEWER_SUFFIX
from convert import (
    _getFilesInDirectory,
    makeFileStreamable,
    AlreadyEncoded,
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


class TestMakeFileStreamable:
    @pytest.fixture(autouse=True)
    def setUp(self, streamable_file_path):
        self.streamable_file_path = streamable_file_path

    def test_makeFileStreamable(self):
        expected_new_file_path = self.streamable_file_path.parent / (MEDIAVIEWER_SUFFIX % self.streamable_file_path.name)

        makeFileStreamable(str(self.streamable_file_path))
        assert expected_new_file_path.exists()
        assert not self.streamable_file_path.exists()

        with pytest.raises(AlreadyEncoded):
            makeFileStreamable(str(expected_new_file_path))

    def test_dryRun(self):
        expected_new_file_path = self.streamable_file_path.parent / (MEDIAVIEWER_SUFFIX % self.streamable_file_path.name)

        makeFileStreamable(str(self.streamable_file_path), dryRun=True)
        assert not expected_new_file_path.exists()
        assert self.streamable_file_path.exists()
