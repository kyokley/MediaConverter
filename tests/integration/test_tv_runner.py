import pytest
from tv_runner import TvRunner, Tv


@pytest.fixture(autouse=True)
def settings_setup(mocker, temp_directory):
    mocker.patch('tv_runner.LOCAL_TV_SHOWS_PATHS',
                    [str(temp_directory)])
    mocker.patch('tv_runner.DOMAIN',
                    'http://mediaviewer:8000')
    mocker.patch("tv_runner.MINIMUM_FILE_SIZE", 100)


class TestRun:
    @pytest.fixture(autouse=True)
    def setUp(self, temp_directory):
        self.temp_dir = temp_directory

        self.tv_dir = self.temp_dir / "Test.Dir.Path"
        self.tv_dir.mkdir()

    def test_run(self, create_video_file):
        create_video_file(self.tv_dir,
                          'Test.Dir.Path.S01E03.mp4')

        tv_runner = TvRunner()
        tv_runner.run()


class TestPostMediaPath:
    @pytest.fixture(autouse=True)
    def setUp(self, create_tv_directory):
        self.tv_dir = create_tv_directory()

    def test_post_media_path_new(self):
        resp = Tv.post_media_path(self.tv_dir)
        assert str(self.tv_dir) == resp['path']

        tv_resp = Tv.get_tv(resp['tv'])
        media_paths = {x['pk'] for x in tv_resp['media_paths']}
        assert tv_resp['pk'] == resp['tv']
        assert resp['pk'] in media_paths

    def test_post_media_path_existing(self):
        first_resp = Tv.post_media_path(self.tv_dir)
        assert str(self.tv_dir) == first_resp['path']

        second_resp = Tv.post_media_path(self.tv_dir)
        assert str(self.tv_dir) == second_resp['path']
        assert first_resp['pk'] == second_resp['pk']
        assert first_resp['tv'] == second_resp['tv']


class TestGetMediaPath:
    @pytest.fixture(autouse=True)
    def setUp(self, create_tv_directory):
        self.tv_dir = create_tv_directory()

    def test_get_media_path(self):
        post_resp = Tv.post_media_path(self.tv_dir)
        assert str(self.tv_dir) == post_resp['path']

        get_resp = Tv.get_media_path(post_resp['pk'])
        assert get_resp == post_resp


class TestGetAllTv:
    @pytest.fixture(autouse=True)
    def setUp(self, create_tv_directory):
        self.tv_dir = create_tv_directory()
        self.post_resp = Tv.post_media_path(self.tv_dir)

    def test_get_all_tv(self):
        resp = Tv.get_all_tv()
        assert self.tv_dir in resp
        assert self.post_resp['pk'] in resp[self.tv_dir]['pks']
