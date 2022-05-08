import pytest
import tempfile
import shutil

from pathlib import Path as PathlibPath

from path import Path


class TestGetLocalPathsFunctional:
    @pytest.fixture(autouse=True)
    def setUp(self):
        self.temp_dir = PathlibPath(tempfile.mkdtemp())
        self.path = Path("localpath", "remotepath")

        yield
        shutil.rmtree(self.temp_dir)

    def test_path_does_not_exist(self):
        filepath = self.temp_dir / "test_file"
        expected = set()
        actual = self.path._buildLocalPaths([filepath])
        assert expected == actual

    def test_paths_exist(self):
        files = set([tempfile.mkstemp(dir=self.temp_dir)[1] for i in range(3)])
        expected = files
        actual = self.path._buildLocalPaths([self.temp_dir])
        assert expected == actual
