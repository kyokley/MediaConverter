import logging
import runpy
from types import SimpleNamespace

import pytest

import main
import settings


@pytest.fixture
def task_module(mocker):
    # Exercise the synchronous task body without a broker or Celery task loading.
    mocker.patch("celery.Celery.task", side_effect=lambda **kwargs: lambda fn: fn)
    return SimpleNamespace(**runpy.run_path(main.__file__, run_name="main"))


def test_task_reports_phases_and_error_summary(mocker, caplog, task_module):
    caplog.set_level(logging.INFO, logger="main")
    globals_ = task_module.main.__globals__
    tv = mocker.Mock()
    movie = mocker.Mock()
    mocker.patch.dict(
        globals_,
        TvRunner=mocker.Mock(return_value=tv),
        MovieRunner=mocker.Mock(return_value=movie),
        SEND_EMAIL=False,
    )
    tv.run.return_value = ["episode encoding failed"]
    movie.run.return_value = []

    task_module.main()

    assert "[1/2] TV pipeline started" in caplog.text
    assert "[2/2] Movie pipeline started" in caplog.text
    assert "Media processing completed: tv_errors=1 movie_errors=0" in caplog.text
    assert "elapsed=" in caplog.text


def test_task_reports_failed_phase_and_preserves_exception(mocker, caplog, task_module):
    caplog.set_level(logging.INFO, logger="main")
    tv = mocker.Mock()
    tv.run.side_effect = RuntimeError("failed")
    movie = mocker.Mock()
    mocker.patch.dict(
        task_module.main.__globals__,
        TvRunner=mocker.Mock(return_value=tv),
        MovieRunner=movie,
    )

    with pytest.raises(RuntimeError, match="failed"):
        task_module.main()

    movie.assert_not_called()
    assert "Media processing failed during TV pipeline" in caplog.text
    assert any(record.exc_info for record in caplog.records)
    assert "Media processing completed" not in caplog.text


def test_worker_log_formats_include_logger_and_task_context():
    assert "%(name)s" in main.app.conf.worker_log_format
    assert "%(task_id)s" in main.app.conf.worker_task_log_format


@pytest.mark.parametrize(
    "level,expected", [(None, "INFO"), ("debug", "DEBUG"), ("invalid", "INFO")]
)
def test_logging_level_and_format(monkeypatch, mocker, level, expected):
    if level is None:
        monkeypatch.delenv("MC_LOG_LEVEL", raising=False)
    else:
        monkeypatch.setenv("MC_LOG_LEVEL", level)
    configure = mocker.patch("logging.basicConfig")

    runpy.run_path(settings.__file__)

    assert configure.call_args.kwargs["level"] == expected
    assert "%(asctime)s" in configure.call_args.kwargs["format"]
    assert "%(name)s" in configure.call_args.kwargs["format"]
