import pytest
import shutil
import tempfile

from pathlib import Path


DATA_DIR_PATH = Path(__file__).parent / "data"
STREAMABLE_FILE_NAME = "mov_bbb.mp4"
STREAMABLE_FILE_PATH = DATA_DIR_PATH / STREAMABLE_FILE_NAME
UNSTREAMABLE_FILE_NAME = "mov_bbb_x265.mp4"
UNSTREAMABLE_FILE_PATH = DATA_DIR_PATH / UNSTREAMABLE_FILE_NAME
SRT_FILE_NAME = "2_Eng.srt"
SRT_FILE_PATH = DATA_DIR_PATH / SRT_FILE_NAME


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


@pytest.fixture()
def temp_directory():
    temp_dir = tempfile.mkdtemp()
    temp_dir_path = Path(temp_dir)
    yield temp_dir_path
    shutil.rmtree(temp_dir_path)
