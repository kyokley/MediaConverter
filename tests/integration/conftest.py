import pytest


@pytest.fixture(autouse=True)
def _enable_sockets_for_integration(socket_enabled):
    pass


@pytest.fixture(autouse=True)
def _set_external_request_cooldown_for_test(mocker):
    mocker.patch("utils._external_request_cooldown", lambda: 0)
