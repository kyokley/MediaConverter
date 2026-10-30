import logging
import pytest

from movie_runner import MovieRunner
from tv_runner import TvRunner


@pytest.fixture(autouse=True)
def published_filenames(mocker):
    mocker.patch("tv_runner.MediaFile.get_all_filenames", side_effect=set)


def test_tv_run_logs_discovery_counts_and_elapsed_summary(mocker, caplog):
    runner = TvRunner()
    runner.paths = {"show-a": {-1}, "show-b": {-1}}
    mocker.patch.object(runner, "_sort_unsorted_files")
    mocker.patch.object(runner, "load_paths")
    mocker.patch.object(runner, "handleDirs")
    mocker.patch.object(runner, "buildLocalFileSet", side_effect=[{"a.mkv"}, set()])
    mocker.patch.object(
        runner,
        "fetch_remote_media_path_details",
        return_value=[{"pk": 1, "media_files": ["remote.mp4"]}],
    )
    mocker.patch.object(runner, "updateFileRecords")

    with caplog.at_level(logging.INFO, logger="tv_runner"):
        assert runner.run() == []

    messages = caplog.messages
    assert any("TV run started" in message for message in messages)
    assert any("show-a" in message and "[1/2]" in message for message in messages)
    assert any("local=1 remote=1" in message for message in messages)
    assert any(
        "TV run completed" in message and "directories=2" in message
        for message in messages
    )


def test_tv_publication_logged_only_after_api_success(mocker, caplog, temp_directory):
    source = temp_directory / "episode.mkv"
    encoded = temp_directory / "episode.mp4"
    source.write_bytes(b"source")
    encoded.write_bytes(b"encoded")
    mocker.patch("tv_runner.stripUnicode", return_value=source)
    mocker.patch("tv_runner.makeFileStreamable", return_value=encoded)
    mocker.patch(
        "tv_runner.TvRunner.get_or_create_media_path",
        return_value={
            "pk": 1,
            "skip": False,
            "bucket": "bucket",
            "b2_upload_prefix": "001/",
        },
    )
    mocker.patch("tv_runner.b2.get_b2_client")
    mocker.patch("tv_runner.upload_subtitle_files", return_value=[])
    post = mocker.patch("tv_runner.MediaFile.post_media_file")

    with caplog.at_level(logging.INFO, logger="tv_runner"):
        TvRunner().updateFileRecords(temp_directory, {source.name}, set())

    publication = next(
        i for i, message in enumerate(caplog.messages) if "Published" in message
    )
    assert "episode.mp4" in caplog.messages[publication]
    assert post.called

    caplog.clear()
    encoded.write_bytes(b"encoded")
    post.side_effect = RuntimeError("API failed")
    with caplog.at_level(logging.ERROR, logger="tv_runner"):
        with pytest.raises(RuntimeError, match="API failed"):
            TvRunner().updateFileRecords(temp_directory, {source.name}, set())
    assert not any("Published" in message for message in caplog.messages)
    assert any("episode.mp4" in message for message in caplog.messages)
    assert any(record.exc_info for record in caplog.records)


def test_movie_run_logs_directory_progress_and_completion(
    mocker, caplog, temp_directory
):
    root = temp_directory / "movies"
    root.mkdir()
    mocker.patch("movie_runner.BASE_PATH", temp_directory)
    mocker.patch("movie_runner.LOCAL_MOVIE_PATHS", ["movies"])
    mocker.patch("movie_runner.Movie.get_all_movies", return_value={})
    for name in ("One", "Two"):
        folder = root / name
        folder.mkdir()
        (folder / f"{name}.mp4").write_bytes(b"encoded")
    mocker.patch.object(MovieRunner, "_getLocalMoviePaths", return_value=["One", "Two"])
    mocker.patch.object(MovieRunner, "promoteSubtitles")
    mocker.patch("movie_runner.reencodeFilesInDirectory", return_value=None)
    post = mocker.patch(
        "movie_runner.Movie.post_media_path",
        return_value={"pk": 1, "bucket": "bucket", "b2_upload_prefix": "001/"},
    )
    mocker.patch("movie_runner.b2.get_b2_client")
    mocker.patch("movie_runner.upload_subtitle_files", return_value=[])
    mocker.patch("movie_runner.MediaFile.post_media_file")
    runner = MovieRunner()

    with caplog.at_level(logging.INFO, logger="movie_runner"):
        assert runner.run() == []

    assert any("[1/2]" in message and "One" in message for message in caplog.messages)
    assert any("[2/2]" in message and "Two" in message for message in caplog.messages)
    assert any(
        "directories=2 discovered, remote=0 pending=2 completed=2" in message
        for message in caplog.messages
    )
    assert post.call_count == 2


def test_tv_dry_run_logs_plan_without_upload_or_publication(
    mocker, caplog, temp_directory
):
    source = temp_directory / "episode.mkv"
    source.write_bytes(b"source")
    encode = mocker.patch("tv_runner.makeFileStreamable")
    create = mocker.patch("tv_runner.TvRunner.get_or_create_media_path")
    upload = mocker.patch("tv_runner.b2.get_b2_client")
    post = mocker.patch("tv_runner.MediaFile.post_media_file")

    with caplog.at_level(logging.INFO, logger="tv_runner"):
        TvRunner().updateFileRecords(
            temp_directory,
            {source.name},
            set(),
            dry_run=True,
        )

    assert any("dry-run would process file" in message for message in caplog.messages)
    encode.assert_not_called()
    create.assert_not_called()
    upload.assert_not_called()
    post.assert_not_called()


def test_tv_strip_unicode_failure_logs_initialized_filename_and_traceback(
    mocker, caplog, temp_directory
):
    mocker.patch(
        "tv_runner.TvRunner.get_or_create_media_path",
        return_value={
            "pk": 1,
            "skip": False,
            "bucket": "bucket",
            "b2_upload_prefix": "001/",
        },
    )
    failure = RuntimeError("strip failed")
    mocker.patch("tv_runner.stripUnicode", side_effect=failure)

    with caplog.at_level(logging.ERROR, logger="tv_runner"):
        with pytest.raises(RuntimeError) as raised:
            TvRunner().updateFileRecords(
                temp_directory,
                {"episode.mkv"},
                set(),
            )

    assert raised.value is failure
    assert any(
        str(temp_directory / "episode.mkv") in message for message in caplog.messages
    )
    assert any(record.exc_info for record in caplog.records)


def test_movie_failure_logs_traceback_and_does_not_report_success(mocker, caplog):
    runner = MovieRunner()
    mocker.patch.object(runner, "postMovies", side_effect=RuntimeError("boom"))

    with caplog.at_level(logging.ERROR, logger="movie_runner"):
        with pytest.raises(RuntimeError, match="boom"):
            runner.run()

    assert any(record.exc_info for record in caplog.records)
    assert not any("Movie run completed" in message for message in caplog.messages)
