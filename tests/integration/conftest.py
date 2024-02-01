import pytest
import shutil
from pathlib import Path


DATA_DIR = Path(__file__).parent.parent / 'data'
if not DATA_DIR.exists():
    raise Exception('FAIL')


@pytest.fixture(autouse=True)
def _enable_sockets_for_integration(socket_enabled):
    pass


@pytest.fixture
def create_video_file():
    def _create_video_file(dir, filename):
        src = DATA_DIR / filename
        dst = dir / filename

        shutil.copy(src, dst)
        return dst
    return _create_video_file
