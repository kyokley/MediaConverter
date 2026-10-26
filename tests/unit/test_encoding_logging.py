import logging
from io import BytesIO
from subprocess import TimeoutExpired

import pytest

from convert import _reencodeVideo, makeFileStreamable
from utils import EncoderException


class FakeProcess:
    def __init__(self, output, returncode=0):
        self.stdout = BytesIO(output.encode())
        self.returncode = returncode
        self.waited = False
        self.terminated = False
        self.killed = False

    def wait(self, timeout=None):
        if timeout is not None and self.terminated and not self.killed:
            raise TimeoutExpired("ffmpeg", timeout)
        self.waited = True
        return self.returncode

    def terminate(self):
        self.terminated = True

    def kill(self):
        self.killed = True


def test_encoding_logs_lifecycle_and_throttled_progress(mocker, caplog, tmp_path):
    progress = (
        "".join(
            f"frame={frame}\nout_time=00:00:{frame:02}.000\nspeed=1.2x\nprogress=continue\n"
            for frame in (1, 2, 3)
        )
        + "frame=4\nout_time=00:00:04.000\nspeed=1.3x\nprogress=end\n"
    )
    process = FakeProcess(progress)
    mocker.patch("convert.Popen", return_value=process)
    mocker.patch("convert.time.monotonic", side_effect=[0, 0, 10, 31, 32, 33])
    destination = tmp_path / "out.mp4"

    with caplog.at_level(logging.INFO, logger="convert"):
        _reencodeVideo("in.mkv", destination, False, False, False)

    assert process.waited
    messages = [record.getMessage() for record in caplog.records]
    assert any(
        "in.mkv" in message and str(destination) in message for message in messages
    )
    progress_messages = [
        message for message in messages if "FFmpeg progress" in message
    ]
    assert len(progress_messages) == 2
    assert any(
        "frame=4" in message and "00:00:04.000" in message
        for message in progress_messages
    )
    assert any("completed" in message and "elapsed" in message for message in messages)


def test_failure_logs_bounded_stderr_and_removes_partial_destination(
    mocker, caplog, tmp_path
):
    destination = tmp_path / "out.mp4"
    destination.touch()
    process = FakeProcess("", returncode=1)

    def start_process(command, stdin, stdout, stderr):
        stderr.write(b"x" * 9000 + b"bounded diagnostic")
        return process

    mocker.patch("convert.Popen", side_effect=start_process)
    mocker.patch("convert.time.monotonic", return_value=4)

    with (
        caplog.at_level(logging.INFO, logger="convert"),
        pytest.raises(EncoderException),
    ):
        _reencodeVideo("in.mkv", destination, False, False, False)

    assert process.waited
    assert not destination.exists()
    messages = [record.getMessage() for record in caplog.records]
    assert any("bounded diagnostic" in message for message in messages)
    assert not any("completed" in message for message in messages)


def test_copy_decision_and_dry_run_are_logged_without_spawn(mocker, caplog, tmp_path):
    spawn = mocker.patch("convert.Popen")
    with caplog.at_level(logging.INFO, logger="convert"):
        _reencodeVideo("in.mkv", tmp_path / "out.mp4", True, True, False, True)
        _reencodeVideo("in.mkv", tmp_path / "dry.mp4", False, False, True, True)

    spawn.assert_not_called()
    messages = [record.getMessage() for record in caplog.records]
    assert any("copy" in message.lower() for message in messages)
    assert any("dry-run" in message.lower() for message in messages)


def test_progress_read_failure_stops_and_reaps_child(mocker, caplog, tmp_path):
    class BrokenProgress(BytesIO):
        def __iter__(self):
            yield b"frame=1\n"
            raise RuntimeError("progress reader failed")

    process = FakeProcess("")
    process.stdout = BrokenProgress()
    mocker.patch("convert.Popen", return_value=process)

    with (
        caplog.at_level(logging.INFO, logger="convert"),
        pytest.raises(RuntimeError, match="progress reader failed"),
    ):
        _reencodeVideo("in.mkv", tmp_path / "out.mp4", False, False, False)

    assert process.terminated
    assert process.killed
    assert process.waited
    assert process.stdout.closed
    assert not any("completed" in record.getMessage() for record in caplog.records)


def test_make_file_streamable_logs_dry_run_plan(mocker, caplog, tmp_path):
    source = tmp_path / "movie.mkv"
    source.touch()
    destination = tmp_path / "movie.mp4"
    mocker.patch("convert.is_valid_media_file", return_value=True)
    mocker.patch("convert.encode")
    mocker.patch("convert.overwriteExistingFile", return_value=destination)

    with caplog.at_level(logging.INFO, logger="convert"):
        result = makeFileStreamable(source, dryRun=True, appendSuffix=False)

    assert result == destination
    messages = [record.getMessage() for record in caplog.records]
    assert any(
        "Dry-run planned output" in message
        and str(source) in message
        and str(destination) in message
        and "elapsed=" in message
        for message in messages
    )
    assert not any("Processing completed" in message for message in messages)
