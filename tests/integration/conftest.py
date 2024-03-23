import pytest


@pytest.fixture(autouse=True)
def _enable_sockets_for_integration(socket_enabled):
    pass


@pytest.fixture(autouse=True)
def _set_external_request_cooldown_for_test(mocker):
    mocker.patch("utils.EXTERNAL_REQUEST_COOLDOWN", 0.01)
