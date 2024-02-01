import pytest
from pathlib import Path
from tv_runner import TvRunner


class TestTvRunner:
    @pytest.fixture(autouse=True)
    def setUp(self, mocker, tmpdir):
        mocker.patch('tv_runner.LOCAL_TV_SHOWS_PATHS',
                     [str(tmpdir)])
        mocker.patch('tv_runner.DOMAIN',
                     'http://mediaviewer:8000')
        mocker.patch("tv_runner.MINIMUM_FILE_SIZE", 100)

        self.temp_dir = Path(tmpdir)

        self.tv_dir = self.temp_dir / "Test.Dir.Path"
        self.tv_dir.mkdir()

    def test_run(self, create_video_file):
        dst = create_video_file(self.tv_dir,
                                'mov_bbb.mp4')

        tv_runner = TvRunner()
        tv_runner.load_paths()
        pass
