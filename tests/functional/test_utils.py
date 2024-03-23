import pytest
import tempfile
import shutil
import os

from pathlib import Path
from utils import (
    stripUnicode,
    is_valid_media_file,
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

    @pytest.mark.parametrize(
        "test_filename,expected",
        (
            ("test_filename", "test_filename"),
            ("test_filenameÐÆ", "test_filenameDAE"),
            ("it's got an apostrophe", "its got an apostrophe"),
        ),
    )
    def test_filenames(self, use_bytes, test_filename, expected):
        self._create_file(test_filename)

        if use_bytes:
            test_filename = test_filename.encode("utf-8")

        expected = Path(expected)
        actual = stripUnicode(test_filename)

        assert expected == actual

    def test_with_path(self, use_bytes):
        test_filename = "test_fi'lenameÐÆ"
        self._create_file(test_filename, path="new_path")

        if use_bytes:
            test_filename = test_filename.encode("utf-8")

        expected = Path("new_path") / "test_filenameDAE"
        actual = stripUnicode(test_filename, path="new_path")

        assert expected == actual


@pytest.mark.parametrize("use_bytes", (True, False))
class TestIsValidMediaFile(CreateFileMixin):
    @pytest.fixture(autouse=True)
    def setUp(self):
        self.current_dir = os.getcwd()
        self.temp_dir = tempfile.mkdtemp()
        os.chdir(self.temp_dir)

        yield
        shutil.rmtree(self.temp_dir)
        os.chdir(self.current_dir)

    def test_bad_extension(self, use_bytes):
        self._create_file("test_path.txt")

        if use_bytes:
            assert not is_valid_media_file(b"test_path.txt")
        else:
            assert not is_valid_media_file("test_path.txt")

    @pytest.mark.parametrize("ext", ("mp4", "MP4"))
    def test_valid(self, ext, use_bytes):
        self._create_file(f"test_path.{ext}")

        if use_bytes:
            test_str = f"test_path.{ext}"
            test_bytes = test_str.encode("utf-8")
            assert is_valid_media_file(test_bytes)
        else:
            assert is_valid_media_file(f"test_path.{ext}")
