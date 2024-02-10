import pytest
import shutil
import tempfile
from faker import Faker

from pathlib import Path

DATA_DIR_PATH = Path(__file__).parent / "data"
STREAMABLE_FILE_NAME = "mov_bbb.mp4"
STREAMABLE_FILE_PATH = DATA_DIR_PATH / STREAMABLE_FILE_NAME
UNSTREAMABLE_FILE_NAME = "mov_bbb_x265.mp4"
UNSTREAMABLE_FILE_PATH = DATA_DIR_PATH / UNSTREAMABLE_FILE_NAME
SRT_FILE_NAME = "2_Eng.srt"
SRT_FILE_PATH = DATA_DIR_PATH / SRT_FILE_NAME


@pytest.fixture(scope='session')
def fake():
    return Faker()


@pytest.fixture(scope='session')
def counter():
    def _counter():
        count = 1
        while True:
            yield count
            count += 1
    return _counter()


@pytest.fixture
def create_tv_directory(temp_directory, create_media_name, create_video_file):
    def _create_tv_directory(tv_name=None,
                             directory=None):
        if tv_name is None:
            tv_name = create_media_name()

        directory = Path(directory) or temp_directory
        tv_dir = directory / tv_name
        if not tv_dir.exists():
            tv_dir.mkdir(exist_ok=True, parents=True)

        video_file = create_video_file(tv_dir, f'{tv_name}.S01E01.mp4')
        return tv_dir, video_file
    return _create_tv_directory


@pytest.fixture
def create_movie_directory(temp_directory, create_media_name, create_video_file):
    def _create_movie_directory(movie_name=None,
                                directory=None):
        if movie_name is None:
            movie_name = create_media_name()

        directory = Path(directory) or temp_directory
        movie_dir = directory / movie_name
        if not movie_dir.exists():
            movie_dir.mkdir(exist_ok=True, parents=True)

        video_file = create_video_file(movie_dir, f'{movie_name}.mp4')
        return movie_dir, video_file
    return _create_movie_directory


@pytest.fixture
def temp_directory(tmp_path, counter):
    dir = tmp_path / f'test_dir{next(counter)}'
    dir.mkdir(exist_ok=True, parents=True)
    yield dir

    if dir.exists():
        shutil.rmtree(dir)


@pytest.fixture
def create_media_name(fake):
    def _create_media_name(num_words=3):
        return '.'.join(fake.words(num_words)).title()
    return _create_media_name


@pytest.fixture()
def streamable_file_path():
    temp_dir = tempfile.mkdtemp()
    temp_dir_path = Path(temp_dir)

    new_path = temp_dir_path / STREAMABLE_FILE_NAME
    shutil.copy(STREAMABLE_FILE_PATH, new_path)

    yield new_path
    shutil.rmtree(temp_dir)


@pytest.fixture()
def unstreamable_file_path():
    temp_dir = tempfile.mkdtemp()
    temp_dir_path = Path(temp_dir)

    new_path = temp_dir_path / UNSTREAMABLE_FILE_NAME
    shutil.copy(UNSTREAMABLE_FILE_PATH, new_path)

    yield new_path
    shutil.rmtree(temp_dir)


@pytest.fixture()
def srt_file_path():
    temp_dir = tempfile.mkdtemp()
    temp_dir_path = Path(temp_dir)

    new_path = temp_dir_path / SRT_FILE_NAME
    shutil.copy(SRT_FILE_PATH, new_path)

    yield new_path
    shutil.rmtree(temp_dir)


@pytest.fixture()
def multiple_srt_path():
    temp_dir = tempfile.mkdtemp()
    temp_dir_path = Path(temp_dir)

    for sub_file in DATA_DIR_PATH.glob("*.srt"):
        new_path = temp_dir_path / sub_file.name
        shutil.copy(sub_file, new_path)

    yield new_path
    shutil.rmtree(temp_dir)


@pytest.fixture
def create_video_file():
    def _create_video_file(dir, dst_name, src_name=STREAMABLE_FILE_NAME):
        src = DATA_DIR_PATH / src_name
        dst = dir / dst_name

        shutil.copy(src, dst)
        return dst
    return _create_video_file
