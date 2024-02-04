import pytest
from tv_runner import TvRunner


class TestTvRunner:
    @pytest.fixture(autouse=True)
    def setUp(self, mocker, temp_directory):
        mocker.patch('tv_runner.LOCAL_TV_SHOWS_PATHS',
                     [str(temp_directory)])
        mocker.patch('tv_runner.DOMAIN',
                     'http://mediaviewer:8000')
        mocker.patch("tv_runner.MINIMUM_FILE_SIZE", 100)

        self.temp_dir = temp_directory

        self.tv_dir = self.temp_dir / "Test.Dir.Path"
        self.tv_dir.mkdir()

    def test_run(self, create_video_file):
        create_video_file(self.tv_dir,
                          'Test.Dir.Path.S01E03.mp4')

        tv_runner = TvRunner()
        tv_runner.run()
