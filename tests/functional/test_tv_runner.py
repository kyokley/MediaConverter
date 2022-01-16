import pytest
import mock
import tempfile
import os
import shutil

from pathlib import Path
from tv_runner import TvRunner
from utils import MissingPathException


class TestBuildLocalFileSetFunctional:
    @pytest.fixture(autouse=True)
    def setUp(self):
        self.SMALL_FILE_SIZE_patcher = mock.patch("tv_runner.SMALL_FILE_SIZE", 201)
        self.SMALL_FILE_SIZE_patcher.start()

        self.temp_dir = tempfile.mkdtemp()

        self.tv_runner = TvRunner()

        yield
        self.SMALL_FILE_SIZE_patcher.stop()
        shutil.rmtree(self.temp_dir)

    def test_file_does_not_exist(self):
        path_name = os.path.join(self.temp_dir, "test_file")
        with pytest.raises(MissingPathException):
            self.tv_runner.buildLocalFileSet(path_name)

    def test_files_exist(self):
        files = [tempfile.mkstemp(dir=self.temp_dir) for i in range(4)]

        for i, file in enumerate(files):
            with open(file[1], "wb") as f:
                f.write(os.urandom(i * 100))

        expected = set(
            [os.path.basename(x[1]).encode('utf-8') for x in files if os.path.getsize(x[1]) > 201]
        )
        actual = self.tv_runner.buildLocalFileSet(self.temp_dir)
        assert expected == actual


class TestSortUnsortedFiles:
    @pytest.fixture(autouse=True)
    def setUp(self, mocker):
        self.temp_dir = tempfile.mkdtemp()
        self.temp_dir_path = Path(self.temp_dir)

        self.unsorted_path = self.temp_dir_path / 'unsorted'
        self.unsorted_path.mkdir()

        mocker.patch(
            "tv_runner.UNSORTED_PATHS", [str(self.unsorted_path)]
        )

        self.mock_get_localpath_by_filename = mocker.patch(
            "tv_runner.get_localpath_by_filename"
        )

        self.tv_runner = TvRunner()

        yield
        shutil.rmtree(self.temp_dir)

    def test_unsorted_path_does_not_exist(self):
        self.unsorted_path.rmdir()

        assert self.tv_runner._sort_unsorted_files() is None
