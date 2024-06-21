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
        self.MINIMUM_FILE_SIZE_patcher = mock.patch("tv_runner.MINIMUM_FILE_SIZE", 201)
        self.MINIMUM_FILE_SIZE_patcher.start()

        self.temp_dir = tempfile.mkdtemp()

        self.tv_runner = TvRunner()

        yield
        self.MINIMUM_FILE_SIZE_patcher.stop()
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
            [os.path.basename(x[1]) for x in files if os.path.getsize(x[1]) > 201]
        )
        actual = self.tv_runner.buildLocalFileSet(self.temp_dir)
        assert expected == actual


class TestSortUnsortedFiles:
    @pytest.fixture(autouse=True)
    def setUp(self, mocker):
        self.temp_dir = tempfile.mkdtemp()
        self.temp_dir_path = Path(self.temp_dir)

        self.unsorted_path = self.temp_dir_path / "unsorted"
        self.unsorted_path.mkdir()

        self.local_path = self.temp_dir_path / "local"
        self.local_path.mkdir()

        mocker.patch("tv_runner.UNSORTED_PATHS", [str(self.unsorted_path)])

        self.mock_get_localpath_by_filename = mocker.patch(
            "tv_runner.get_localpath_by_filename"
        )

        self.tv_runner = TvRunner()

        yield
        shutil.rmtree(self.temp_dir)

    def test_unsorted_path_does_not_exist(self):
        self.unsorted_path.rmdir()

        assert self.tv_runner._sort_unsorted_files() is None

    def test_no_localpath_for_filename(self):
        self.mock_get_localpath_by_filename.return_value = None
        new_path = self.local_path / "new.show.s02e10"

        unsorted_file_path = self.unsorted_path / "new.show.s02e10"
        unsorted_file_path.mkdir()
        assert self.tv_runner._sort_unsorted_files() is None
        assert unsorted_file_path.exists()
        assert not new_path.exists()

    def test_localpath_does_not_exist(self):
        self.local_path.rmdir()
        self.mock_get_localpath_by_filename.return_value = Path(self.local_path)
        new_path = self.local_path / "new.show.s02e10"

        unsorted_file_path = self.unsorted_path / "new.show.s02e10"
        unsorted_file_path.mkdir()

        assert self.tv_runner._sort_unsorted_files() is None
        assert unsorted_file_path.exists()
        assert not new_path.exists()

    def test_localpath_for_filename(self):
        self.mock_get_localpath_by_filename.return_value = Path(self.local_path)
        new_path = self.local_path / "new.show.s02e10"

        unsorted_file_path = self.unsorted_path / "new.show.s02e10"
        unsorted_file_path.mkdir()
        assert self.tv_runner._sort_unsorted_files() is None
        assert not unsorted_file_path.exists()
        assert new_path.exists()


class TestHandleDirs:
    @pytest.fixture(autouse=True)
    def setUp(self, mocker, temp_directory):
        mocker.patch("tv_runner.MINIMUM_FILE_SIZE", 100)

        self.temp_dir_path = temp_directory

        self.tv_dir = self.temp_dir_path / "Test.Dir.Path"
        self.tv_dir.mkdir()

        self.episode_dir = self.tv_dir / "Test.Dir.Path.S04E01.WEBRip.x264-MV"
        self.episode_dir.mkdir()

        self.episode_file = self.episode_dir / "Test.Dir.Path.S04E01.WEBRip.x264-MV.mp4"
        with open(self.episode_file, "w") as f:
            f.seek(1500)
            f.write("0")

        self.small_file = self.episode_dir / "small.mp4"
        with open(self.small_file, "w") as f:
            f.seek(50)
            f.write("0")

        self.sub_dir = self.episode_dir / "Subs"
        self.sub_dir.mkdir()

        self.sub_file = self.sub_dir / "2_Eng.srt"
        self.sub_file.touch()

        self.expected_media_file = (
            self.tv_dir / "Test.Dir.Path.S04E01.WEBRip.x264-MV.mp4"
        )
        self.expected_sub_file = (
            self.tv_dir / "Test.Dir.Path.S04E01.WEBRip.x264-MV-0.srt"
        )
        self.non_existent_small_file = self.tv_dir / "small.mp4"

        self.tv_runner = TvRunner()

    def test_path_does_not_exist(self):
        shutil.rmtree(self.tv_dir)

        self.tv_runner.handleDirs(self.tv_dir)
        assert not self.expected_media_file.exists()
        assert not self.expected_sub_file.exists()
        assert not self.non_existent_small_file.exists()

    def test_handleDirs(self):
        self.tv_runner.handleDirs(self.tv_dir)
        assert self.expected_media_file.exists()
        assert self.expected_sub_file.exists()
        assert not self.non_existent_small_file.exists()
