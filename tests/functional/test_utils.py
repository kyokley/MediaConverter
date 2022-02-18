import pytest
import tempfile
import shutil
import os

from pathlib import Path
from utils import (
    stripUnicode,
    is_valid_media_file,
    is_valid_subtitle_file,
)


class CreateFileMixin:
    def _create_file(self, filename, path=None):
        if path:
            temp_path = Path(self.temp_dir) / path
            os.mkdir(temp_path)

            temp_path = temp_path / filename
        else:
            temp_path = Path(self.temp_dir) / filename
        with open(temp_path, "w") as f:
            f.write("")


@pytest.mark.parametrize("use_bytes", (True, False))
class TestStripUnicode(CreateFileMixin):
    @pytest.fixture(autouse=True)
    def setUp(self):
        self.current_dir = os.getcwd()
        self.temp_dir = tempfile.mkdtemp()
        os.chdir(self.temp_dir)

        yield
        shutil.rmtree(self.temp_dir)
        os.chdir(self.current_dir)

    def test_no_changes(self, use_bytes):
        test_filename = "test_filename"
        self._create_file(test_filename)

        if use_bytes:
            test_filename = test_filename.encode("utf-8")

        expected = "test_filename"
        actual = stripUnicode(test_filename)

        assert expected == actual

    def test_with_changes(self, use_bytes):
        test_filename = "test_filenameÐÆ"
        self._create_file(test_filename)

        if use_bytes:
            test_filename = test_filename.encode("utf-8")

        expected = "test_filenameDAE"
        actual = stripUnicode(test_filename)

        assert expected == actual

    def test_strip_apostrophe(self, use_bytes):
        test_filename = "it's got an apostrophe"
        self._create_file(test_filename)

        if use_bytes:
            test_filename = test_filename.encode("utf-8")

        expected = "its got an apostrophe"
        actual = stripUnicode(test_filename)

        assert expected == actual

    def test_with_path(self, use_bytes):
        test_filename = "test_fi'lenameÐÆ"
        self._create_file(test_filename, path="new_path")

        if use_bytes:
            test_filename = test_filename.encode("utf-8")

        expected = f"{Path('new_path') / 'test_filenameDAE'}"
        actual = stripUnicode(test_filename, path="new_path")

        assert expected == actual


class TestIsValidMediaFile(CreateFileMixin):
    @pytest.fixture(autouse=True)
    def setUp(self):
        self.current_dir = os.getcwd()
        self.temp_dir = tempfile.mkdtemp()
        os.chdir(self.temp_dir)

        yield
        shutil.rmtree(self.temp_dir)
        os.chdir(self.current_dir)

    def test_file_does_not_exist(self):
        assert not is_valid_media_file("test_path.mp4")

    def test_bad_extension(self):
        self._create_file("test_path.txt")

        assert not is_valid_media_file("test_path.txt")

    @pytest.mark.parametrize("ext", ("mp4", "MP4"))
    def test_valid(self, ext):
        self._create_file(f"test_path.{ext}")
        assert is_valid_media_file(f"test_path.{ext}")


class TestIsValidSubtitleFile(CreateFileMixin):
    @pytest.fixture(autouse=True)
    def setUp(self):
        self.current_dir = os.getcwd()
        self.temp_dir = tempfile.mkdtemp()
        os.chdir(self.temp_dir)

        yield
        shutil.rmtree(self.temp_dir)
        os.chdir(self.current_dir)

    def test_file_does_not_exist(self):
        assert not is_valid_subtitle_file("test_path.srt")

    def test_bad_extension(self):
        self._create_file("test_path.txt")
        assert not is_valid_subtitle_file("test_path.txt")

    @pytest.mark.parametrize("ext", ("srt", "SRT"))
    def test_valid(self, ext):
        self._create_file(f"test_path.{ext}")
        assert is_valid_subtitle_file(f"test_path.{ext}")
