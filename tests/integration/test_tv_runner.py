import pytest

from pathlib import Path
from tv_runner import TvRunner, Tv, MediaFile


class BaseSettings:
    @pytest.fixture(autouse=True)
    def setUp(self,
              mocker,
              temp_directory,
              create_tv_directory,
              ):
        self._temp_directory = temp_directory
        mocker.patch('tv_runner.DOMAIN',
                        'http://mediaviewer:8000')
        mocker.patch("tv_runner.MINIMUM_FILE_SIZE", 100)
        self.local_paths = self._local_tv_paths()
        mocker.patch('tv_runner.LOCAL_TV_SHOWS_PATHS',
                     self.local_paths)
        self.tv_dir, self.video_file = create_tv_directory(self.local_paths[-1])

    def _local_tv_paths(self):
        return [str(self._temp_directory)]


class TestRun(BaseSettings):
    def test_run(self):
        tv_runner = TvRunner()
        tv_runner.run()


class TestPostMediaPath(BaseSettings):
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


class TestGetMediaPath(BaseSettings):
    def test_get_media_path(self):
        post_resp = Tv.post_media_path(self.tv_dir)
        assert str(self.tv_dir) == post_resp['path']

        get_resp = Tv.get_media_path(post_resp['pk'])
        assert get_resp == post_resp


class TestGetAllTv(BaseSettings):
    def test_get_all_tv(self):
        self.post_resp = Tv.post_media_path(self.tv_dir)

        resp = Tv.get_all_tv()
        assert self.tv_dir in resp
        assert self.post_resp['pk'] in resp[self.tv_dir]['pks']


class TestPostMediaFile(BaseSettings):
    def _local_tv_paths(self):
        return [
            str(self._temp_directory / f'{x}')
            for x in range(3)
        ]

    def test_post_media_file(self):
        post_resp = Tv.post_media_path(self.tv_dir)
        media_path_id = post_resp['pk']
        mf_resp = MediaFile.post_media_file(
            self.video_file.name,
            media_path_id,
            123123)

        assert mf_resp['filename'] == self.video_file.name
        assert mf_resp['media_path'] == post_resp['pk']
        assert mf_resp['ismovie'] is False
        assert mf_resp['size'] == 123123

        get_resp = Tv.get_media_path(post_resp['pk'])
        assert self.video_file.name in get_resp['media_files']

    def test_multiple_media_paths(self, create_tv_directory):
        self.video_files = []
        self.dirs = []
        tv = None

        for idx, dir_str in enumerate(self.local_paths):
            new_dir = Path(dir_str) / f'TestDir{idx}'
            tv_dir, video_file = create_tv_directory(
                directory=new_dir)
            self.video_files.append(video_file)
            self.dirs.append(tv_dir)

            resp = Tv.post_media_path(tv_dir, tv=tv)
            MediaFile.post_media_file(
                video_file.name,
                resp['pk'],
                123124)
            if tv is None:
                tv = resp['tv']

        resp = Tv.get_tv(tv)
        media_paths = {x['path']
                       for x in resp['media_paths']}
        assert resp['number_of_unwatched_shows'] == 3

        for dir in self.dirs:
            assert str(dir) in media_paths
