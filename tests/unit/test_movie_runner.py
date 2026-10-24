import mock
import pytest
import uuid

from pathlib import Path
from movie_runner import MovieRunner, Movie
from tv_runner import MediaFile


def gen_data(num):
    return [dict(results=[dict(pk=i)]) for i in range(1, num + 1)]


class TestPostMovies:
    @pytest.fixture(autouse=True)
    def setUp(self, mocker, temp_directory):
        mocker.patch("movie_runner.B2_ENABLED", False)
        self.tmp_dir = temp_directory
        movie_dir = self.tmp_dir / "movies"
        movie_dir.mkdir(parents=True)
        mocker.patch("movie_runner.BASE_PATH", self.tmp_dir)
        mocker.patch("utils.requests")
        self.mock_get_data = mocker.patch("movie_runner.get_data")
        self.mock_response = mock.MagicMock()
        self.mock_response.json.return_value = {
            "results": [],
            "next": "",
        }
        self.mock_get_data.return_value = self.mock_response
        mocker.patch.object(MediaFile, "get_all_filenames", return_value=set())

        mocker.patch("movie_runner.LOCAL_MOVIE_PATHS", [f"{self.tmp_dir}/movies"])

        self.mock_promoteSubtitles = mocker.patch(
            "movie_runner.MovieRunner.promoteSubtitles"
        )

        self.mock_exists = mocker.patch("movie_runner.os.path.exists")

        self.mock_reencodeFilesInDirectory = mocker.patch(
            "movie_runner.reencodeFilesInDirectory"
        )

        self.mock_getLocalMoviePaths = mocker.patch(
            "movie_runner.MovieRunner._getLocalMoviePaths"
        )

        self.mock_log = mocker.patch("movie_runner.log")

        self.mock_exists.return_value = True
        self.mock_getLocalMoviePaths.return_value = ["movie1", "movie2", "movie3"]
        self.mock_reencodeFilesInDirectory.return_value = None

        self.movieRunner = MovieRunner()

    def test_postMovies(self):
        assert self.movieRunner.postMovies() is None
        assert not self.movieRunner.errors, []

        self.mock_log.info.assert_has_calls(
            [
                mock.call(f"Found {self.tmp_dir}/movies/movie2"),
                mock.call(f"Starting re-encoding of {self.tmp_dir}/movies/movie2..."),
                mock.call(f"Posting {self.tmp_dir}/movies/movie2"),
            ]
        )
        assert not self.mock_log.error.called

        self.mock_promoteSubtitles.assert_has_calls(
            [
                mock.call(Path(f"{self.tmp_dir}/movies/movie1"), dry_run=False),
                mock.call(Path(f"{self.tmp_dir}/movies/movie2"), dry_run=False),
                mock.call(Path(f"{self.tmp_dir}/movies/movie3"), dry_run=False),
            ]
        )
        self.mock_reencodeFilesInDirectory.assert_has_calls(
            [
                mock.call(Path(f"{self.tmp_dir}/movies/movie1")),
                mock.call(Path(f"{self.tmp_dir}/movies/movie2")),
                mock.call(Path(f"{self.tmp_dir}/movies/movie3")),
            ]
        )

    def test_global_exact_filename_match_skips_before_conversion(self, mocker):
        mocker.patch("movie_runner.B2_ENABLED", True)
        self.mock_getLocalMoviePaths.return_value = ["movie1"]
        video = Path(f"{self.tmp_dir}/movies/movie1/Already.mp4")
        mocker.patch.object(
            MediaFile, "get_all_filenames", return_value={"Already.mp4"}
        )
        largest = mocker.patch.object(
            MovieRunner, "_get_largest_video_file", return_value=video
        )

        self.movieRunner.postMovies()

        largest.assert_called_once_with(Path(f"{self.tmp_dir}/movies/movie1"))
        self.mock_promoteSubtitles.assert_not_called()
        self.mock_reencodeFilesInDirectory.assert_not_called()

    @pytest.mark.parametrize("filename", ["already.mp4", "Already.mv-encoded.mp4"])
    def test_filename_near_match_is_not_skipped(self, mocker, filename):
        mocker.patch("movie_runner.B2_ENABLED", True)
        video = Path(f"{self.tmp_dir}/movies/movie1/{filename}")
        video.parent.mkdir(parents=True, exist_ok=True)
        video.write_bytes(b"video")
        mocker.patch.object(
            MediaFile, "get_all_filenames", return_value={"Already.mp4"}
        )
        mocker.patch.object(MovieRunner, "_get_largest_video_file", return_value=video)
        mocker.patch(
            "movie_runner.Movie.post_media_path",
            return_value={"pk": 1, "bucket": "bucket", "b2_upload_prefix": "p/"},
        )
        mocker.patch("movie_runner.b2.get_b2_client")
        mocker.patch("movie_runner.upload_subtitle_files", return_value=[])
        record = mocker.patch.object(MediaFile, "post_media_file")

        self.movieRunner.postMovies()

        self.mock_reencodeFilesInDirectory.assert_called()
        assert self.movieRunner.errors == []
        record.assert_called_once_with(
            filename, 1, len(b"video"), subtitle_files=[], b2_uuid=mock.ANY
        )

    def test_encoded_global_match_skips_before_media_path_post(self, mocker):
        mocker.patch("movie_runner.B2_ENABLED", True)
        self.mock_getLocalMoviePaths.return_value = ["movie1"]
        video = Path(f"{self.tmp_dir}/movies/movie1/Encoded.mp4")
        mocker.patch.object(
            MediaFile, "get_all_filenames", return_value={"Encoded.mp4"}
        )
        mocker.patch.object(
            MovieRunner,
            "_get_largest_video_file",
            side_effect=[None, video],
        )
        post_path = mocker.patch("movie_runner.Movie.post_media_path")

        self.movieRunner.postMovies()

        self.mock_reencodeFilesInDirectory.assert_called_once()
        post_path.assert_not_called()

    def test_filename_inventory_failure_aborts_before_conversion(self, mocker):
        mocker.patch("movie_runner.B2_ENABLED", True)
        mocker.patch.object(
            MediaFile,
            "get_all_filenames",
            side_effect=RuntimeError("inventory unavailable"),
        )

        with pytest.raises(RuntimeError, match="inventory unavailable"):
            self.movieRunner.postMovies()

        self.mock_promoteSubtitles.assert_not_called()
        self.mock_reencodeFilesInDirectory.assert_not_called()

    def test_same_filename_batch_publishes_once(self, mocker):
        mocker.patch("movie_runner.B2_ENABLED", True)
        video = Path(f"{self.tmp_dir}/movies/movie1/Shared.mp4")
        video.parent.mkdir(parents=True, exist_ok=True)
        video.write_bytes(b"video")
        mocker.patch.object(MovieRunner, "_get_largest_video_file", return_value=video)
        mocker.patch(
            "movie_runner.Movie.post_media_path",
            return_value={"pk": 1, "bucket": "bucket", "b2_upload_prefix": "p/"},
        )
        client = mocker.patch("movie_runner.b2.get_b2_client").return_value
        mocker.patch("movie_runner.upload_subtitle_files", return_value=[])
        record = mocker.patch.object(MediaFile, "post_media_file")

        self.movieRunner.postMovies()

        client.upload_file.assert_called_once()
        record.assert_called_once_with(
            "Shared.mp4", 1, len(b"video"), subtitle_files=[], b2_uuid=mock.ANY
        )

    def test_reencodeErrors(self):
        self.mock_reencodeFilesInDirectory.side_effect = [
            ["test_error1"],
            [],
            ["test_error2"],
        ]

        assert self.movieRunner.postMovies() is None
        assert self.movieRunner.errors == ["test_error1", "test_error2"]

        self.mock_log.info.assert_has_calls(
            [
                mock.call(f"Found {self.tmp_dir}/movies/movie2"),
                mock.call(f"Starting re-encoding of {self.tmp_dir}/movies/movie2..."),
            ]
        )
        assert not self.mock_log.error.called

        self.mock_reencodeFilesInDirectory.assert_has_calls(
            [
                mock.call(Path(f"{self.tmp_dir}/movies/movie1")),
                mock.call(Path(f"{self.tmp_dir}/movies/movie2")),
                mock.call(Path(f"{self.tmp_dir}/movies/movie3")),
            ]
        )
        self.mock_promoteSubtitles.assert_has_calls(
            [
                mock.call(Path(f"{self.tmp_dir}/movies/movie1"), dry_run=False),
                mock.call(Path(f"{self.tmp_dir}/movies/movie2"), dry_run=False),
                mock.call(Path(f"{self.tmp_dir}/movies/movie3"), dry_run=False),
            ]
        )

    def test_unhandledException(self):
        self.mock_reencodeFilesInDirectory.side_effect = Exception(
            "Oh no! Something bad happened"
        )

        with pytest.raises(Exception):
            self.movieRunner.postMovies()

        self.mock_log.info.assert_has_calls(
            [
                mock.call(f"Found {self.tmp_dir}/movies/movie1"),
                mock.call(f"Starting re-encoding of {self.tmp_dir}/movies/movie1..."),
            ]
        )
        self.mock_log.error.assert_has_calls(
            [
                mock.call(f"Error processing {self.tmp_dir}/movies/movie1"),
                mock.call("Oh no! Something bad happened"),
            ]
        )

        self.mock_reencodeFilesInDirectory.assert_has_calls(
            [
                mock.call(Path(f"{self.tmp_dir}/movies/movie1")),
            ]
        )
        self.mock_promoteSubtitles.assert_has_calls(
            [
                mock.call(Path(f"{self.tmp_dir}/movies/movie1"), dry_run=False),
            ]
        )

    def test_postMovies_b2_enabled(self, mocker):
        mocker.patch("movie_runner.B2_ENABLED", True)
        mocker.patch("utils.B2_BUCKET_NAME", "bucket")
        mocker.patch("utils.B2_NAME_PREFIX", "prefix/")
        mock_upload = mocker.patch("movie_runner.b2.get_b2_client")
        events = []
        mock_upload.return_value.upload_file.side_effect = lambda *args: events.append(
            ("video", args)
        )
        mock_post_media_path = mocker.patch("movie_runner.Movie.post_media_path")
        mock_post_media_path.side_effect = lambda path: (
            events.append(("path", path))
            or {
                "pk": sum(event[0] == "path" for event in events),
                "skip": False,
                "bucket": "bucket",
                "b2_upload_prefix": f"movies/{sum(event[0] == 'path' for event in events)}/",
            }
        )
        mock_upload_subtitle_files = mocker.patch(
            "movie_runner.upload_subtitle_files",
        )
        mock_upload_subtitle_files.side_effect = lambda *args, **kwargs: (
            events.append(("subtitles", args, kwargs))
            or ["abcdefab-cdef-abcd-efab-cdefabcdefab.vtt"]
        )

        def candidate_for(localpath):
            video_path = Path(localpath) / f"{Path(localpath).name.title()}.mp4"
            video_path.parent.mkdir(parents=True, exist_ok=True)
            video_path.write_bytes(video_path.name.encode())
            return video_path

        mocker.patch(
            "movie_runner.MovieRunner._get_largest_video_file",
            side_effect=candidate_for,
        )
        mock_media_file_post = mocker.patch.object(MediaFile, "post_media_file")
        mock_media_file_post.side_effect = lambda *args, **kwargs: events.append(
            ("record", args, kwargs)
        )

        assert self.movieRunner.postMovies() is None
        assert not self.movieRunner.errors

        upload_calls = mock_upload.return_value.upload_file.call_args_list
        assert len(upload_calls) == 3
        assert mock_upload_subtitle_files.call_count == 3
        assert mock_post_media_path.call_args_list == [
            mock.call(f"b2://bucket/prefix/movie{index}/") for index in range(1, 4)
        ]
        assert mock_media_file_post.call_count == 3
        for index, (upload_call, subtitle_call, record_call) in enumerate(
            zip(
                upload_calls,
                mock_upload_subtitle_files.call_args_list,
                mock_media_file_post.call_args_list,
            ),
            start=1,
        ):
            video_path = Path(f"{self.tmp_dir}/movies/movie{index}/Movie{index}.mp4")
            assert upload_call.args[:2] == (video_path, "bucket")
            key = upload_call.args[2]
            assert key.startswith(f"movies/{index}/") and key.endswith(".mp4")
            assert "Movie" not in key
            object_uuid = key.removeprefix(f"movies/{index}/").removesuffix(".mp4")
            assert str(uuid.UUID(object_uuid)) == object_uuid
            assert subtitle_call == mock.call(
                video_path,
                video_path.parent,
                bucket="bucket",
                key_prefix=f"movies/{index}/",
            )
            assert record_call.args == (
                f"Movie{index}.mp4",
                index,
                len(f"Movie{index}.mp4".encode()),
            )
            assert record_call.kwargs == {
                "subtitle_files": ["abcdefab-cdef-abcd-efab-cdefabcdefab.vtt"],
                "b2_uuid": object_uuid,
            }
        assert [event[0] for event in events] == [
            "path",
            "video",
            "subtitles",
            "record",
        ] * 3

    def test_postMovies_b2_enabled_no_video_file(self, mocker):
        mocker.patch("movie_runner.B2_ENABLED", True)
        mocker.patch("movie_runner.b2.get_b2_client")
        mock_post_media_path = mocker.patch("movie_runner.Movie.post_media_path")
        mocker.patch(
            "movie_runner.MovieRunner._get_largest_video_file", return_value=None
        )

        assert self.movieRunner.postMovies() is None
        assert self.movieRunner.errors == [
            f"No video file found in {self.tmp_dir}/movies/movie1. Continuing...",
            f"No video file found in {self.tmp_dir}/movies/movie2. Continuing...",
            f"No video file found in {self.tmp_dir}/movies/movie3. Continuing...",
        ]
        assert not mock_post_media_path.called

    def test_get_all_movies_b2_reverse_mapping(self, mocker, temp_directory):
        mocker.patch("utils.BASE_PATH", str(temp_directory))
        mocker.patch("movie_runner.LOCAL_MOVIE_PATHS", ["movies"])
        local_dir = temp_directory / "movies" / "Movie.Name"
        local_dir.mkdir(parents=True)

        mock_response = mock.MagicMock()
        mock_response.json.return_value = {
            "results": [
                {
                    "media_path": {
                        "pk": 1,
                        "path": "b2://bucket/prefix/Movie.Name/",
                        "filename": "Movie.Name.mp4",
                    },
                    "finished": False,
                }
            ],
            "next": "",
        }
        mocker.patch("movie_runner.get_data", return_value=mock_response)

        paths = Movie.get_all_movies()

        assert paths == {local_dir: {"pks": {1}, "finished": False}}

    def test_incomplete_b2_movie_path_is_retryable(self, mocker, temp_directory):
        mocker.patch("utils.BASE_PATH", str(temp_directory))
        mocker.patch("movie_runner.LOCAL_MOVIE_PATHS", ["movies"])
        response = mock.Mock()
        response.json.return_value = {
            "results": [
                {
                    "media_path": {
                        "pk": 8,
                        "path": "b2://bucket/archive/Movie.Name/",
                    },
                    "finished": False,
                }
            ],
            "next": "",
        }
        mocker.patch("movie_runner.get_data", return_value=response)

        incomplete = {}
        assert Movie.get_all_movies(incomplete) == {}
        assert incomplete == {
            temp_directory / "movies" / "Movie.Name": {
                "path": "b2://bucket/archive/Movie.Name/",
                "pks": {8},
            }
        }

    def test_incomplete_b2_movie_reuses_stored_uri_and_destination(
        self, mocker, temp_directory
    ):
        mocker.patch("movie_runner.B2_ENABLED", True)
        mocker.patch("movie_runner.BASE_PATH", temp_directory)
        mocker.patch("movie_runner.LOCAL_MOVIE_PATHS", ["movies"])
        mocker.patch("utils.BASE_PATH", str(temp_directory))
        mocker.patch("utils.B2_BUCKET_NAME", "configured")
        mocker.patch("utils.B2_NAME_PREFIX", "configured-prefix/")
        local_path = temp_directory / "movies" / "Film"
        local_path.mkdir(parents=True)
        response = mock.Mock()
        response.json.return_value = {
            "results": [
                {
                    "media_path": {
                        "pk": 42,
                        "path": "b2://custom/archive/Film/",
                    },
                    "finished": False,
                }
            ],
            "next": "",
        }
        mocker.patch("movie_runner.get_data", return_value=response)
        mocker.patch(
            "movie_runner.MovieRunner._getLocalMoviePaths", return_value=["Film"]
        )
        mocker.patch("movie_runner.reencodeFilesInDirectory", return_value=None)
        video = local_path / "Film.converted.mp4"
        video.write_bytes(b"encoded")
        mocker.patch(
            "movie_runner.MovieRunner._get_largest_video_file", return_value=video
        )
        post_path = mocker.patch(
            "movie_runner.Movie.post_media_path",
            return_value={
                "pk": 42,
                "bucket": "custom",
                "b2_upload_prefix": "archive/42/",
            },
        )
        upload = mocker.patch("movie_runner.b2.get_b2_client")
        subtitles = mocker.patch(
            "movie_runner.upload_subtitle_files",
            return_value=["abcdefab-cdef-abcd-efab-cdefabcdefab.vtt"],
        )
        post_file = mocker.patch.object(MediaFile, "post_media_file")

        MovieRunner().postMovies()

        post_path.assert_called_once_with("b2://custom/archive/Film/")
        upload.return_value.upload_file.assert_called_once()
        assert upload.return_value.upload_file.call_args.args[:2] == (video, "custom")
        object_key = upload.return_value.upload_file.call_args.args[2]
        assert object_key.startswith("archive/42/")
        assert "Film" not in object_key
        subtitles.assert_called_once_with(
            video,
            local_path,
            bucket="custom",
            key_prefix="archive/42/",
        )
        post_file.assert_called_once_with(
            video.name,
            42,
            len(b"encoded"),
            subtitle_files=["abcdefab-cdef-abcd-efab-cdefabcdefab.vtt"],
            b2_uuid=object_key.removeprefix("archive/42/").removesuffix(".mp4"),
        )

    @pytest.mark.parametrize(
        "configured_suffix", ["mv-encoded.mp4", "custom-encode.mp4"]
    )
    def test_lanterns_already_encoded_upload_and_publish_real_subtitle_tracks(
        self, mocker, temp_directory, configured_suffix
    ):
        mocker.patch("movie_runner.B2_ENABLED", True)
        mocker.patch("movie_runner.BASE_PATH", temp_directory)
        mocker.patch("movie_runner.LOCAL_MOVIE_PATHS", ["movies"])
        mocker.patch("utils.MEDIAVIEWER_SUFFIX", configured_suffix)
        mocker.patch("movie_runner.Movie.get_all_movies", return_value={})
        mocker.patch(
            "movie_runner.MovieRunner._getLocalMoviePaths", return_value=["Lanterns"]
        )
        mocker.patch("movie_runner.reencodeFilesInDirectory", return_value=None)
        folder = temp_directory / "movies" / "Lanterns"
        folder.mkdir(parents=True)
        stem = "Lanterns.S01E01.1080p.WEBRip.10Bit.DDP5.1.x265-NeoNoir.mp4.ALFRED-ENCODED.mp4"
        video = folder / f"{stem}.{configured_suffix}"
        video.write_bytes(b"video")
        subtitles = [folder / f"{stem}-{track}.vtt" for track in (0, 1)]
        for subtitle in subtitles:
            subtitle.write_bytes(b"subtitle")
        (folder / f"{stem.replace('S01E01', 'S01E02')}-0.vtt").write_bytes(b"decoy")
        mocker.patch(
            "movie_runner.Movie.post_media_path",
            return_value={
                "pk": 42,
                "bucket": "bucket",
                "b2_upload_prefix": "movies/42/",
            },
        )
        transfers = []
        client = mocker.patch("movie_runner.b2.get_b2_client").return_value
        client.upload_file.side_effect = lambda *args: transfers.append(args)
        record = mocker.patch.object(MediaFile, "post_media_file")

        MovieRunner().postMovies()

        video_uuid = record.call_args.kwargs["b2_uuid"]
        posted_subtitles = record.call_args.kwargs["subtitle_files"]
        assert record.call_args.args == (video.name, 42, len(b"video"))
        assert str(uuid.UUID(video_uuid)) == video_uuid
        assert len(posted_subtitles) == 2
        assert {Path(upload[0]).name for upload in transfers[1:]} == {
            p.name for p in subtitles
        }
        assert {upload[2] for upload in transfers[1:]} == {
            f"movies/42/{name}" for name in posted_subtitles
        }
        assert transfers[0][2] == f"movies/42/{video_uuid}{video.suffix}"
        assert all(
            upload[1] == "bucket" and upload[2].startswith("movies/42/")
            for upload in transfers
        )
        assert all("Lanterns" not in upload[2] for upload in transfers)

    def test_lanterns_subtitle_upload_failure_does_not_publish_movie(
        self, mocker, temp_directory
    ):
        mocker.patch("movie_runner.B2_ENABLED", True)
        mocker.patch("movie_runner.BASE_PATH", temp_directory)
        mocker.patch("movie_runner.LOCAL_MOVIE_PATHS", ["movies"])
        mocker.patch("movie_runner.Movie.get_all_movies", return_value={})
        mocker.patch(
            "movie_runner.MovieRunner._getLocalMoviePaths", return_value=["Lanterns"]
        )
        mocker.patch("movie_runner.reencodeFilesInDirectory", return_value=None)
        folder = temp_directory / "movies" / "Lanterns"
        folder.mkdir(parents=True)
        stem = "Lanterns.S01E01.1080p.WEBRip.10Bit.DDP5.1.x265-NeoNoir.mp4.ALFRED-ENCODED.mp4"
        video = folder / f"{stem}.mv-encoded.mp4"
        subtitle = folder / f"{stem}-0.vtt"
        video.write_bytes(b"video")
        subtitle.write_bytes(b"subtitle")
        mocker.patch(
            "movie_runner.Movie.post_media_path",
            return_value={
                "pk": 42,
                "bucket": "bucket",
                "b2_upload_prefix": "movies/42/",
            },
        )
        client = mocker.patch("movie_runner.b2.get_b2_client").return_value
        client.upload_file.side_effect = lambda _file, _bucket, key: (
            (_ for _ in ()).throw(RuntimeError("subtitle upload failed"))
            if key.endswith(".vtt")
            else None
        )
        record = mocker.patch.object(MediaFile, "post_media_file")

        with pytest.raises(RuntimeError, match="subtitle upload failed"):
            MovieRunner().postMovies()

        record.assert_not_called()
        assert video.exists() and subtitle.exists()

    def test_multiple_incomplete_b2_paths_for_local_movie_fail(
        self, mocker, temp_directory
    ):
        mocker.patch("utils.BASE_PATH", str(temp_directory))
        mocker.patch("movie_runner.LOCAL_MOVIE_PATHS", ["movies"])
        local_path = temp_directory / "movies" / "Film"
        local_path.mkdir(parents=True)
        response = mock.Mock()
        response.json.return_value = {
            "results": [
                {
                    "media_path": {"pk": 42, "path": "b2://custom/archive/Film/"},
                    "finished": False,
                },
                {
                    "media_path": {"pk": 43, "path": "b2://other/archive/Film/"},
                    "finished": False,
                },
            ],
            "next": "",
        }
        mocker.patch("movie_runner.get_data", return_value=response)

        with pytest.raises(ValueError, match="Multiple incomplete B2 MediaPaths"):
            Movie.get_all_movies({})

    def test_completed_b2_movie_is_not_reprocessed(self, mocker):
        mocker.patch("utils.BASE_PATH", str(self.tmp_dir))
        mocker.patch("movie_runner.LOCAL_MOVIE_PATHS", ["movies"])
        movie_path = self.tmp_dir / "movies" / "Movie.Name"
        movie_path.mkdir(parents=True)
        response = mock.Mock()
        response.json.return_value = {
            "results": [
                {
                    "media_path": {
                        "pk": 1,
                        "path": "b2://bucket/prefix/Movie.Name/",
                        "filename": "Movie.Name.mp4",
                    },
                    "finished": False,
                }
            ],
            "next": "",
        }
        mocker.patch("movie_runner.get_data", return_value=response)
        mock_get_local_paths = mocker.patch(
            "movie_runner.MovieRunner._getLocalMoviePaths",
            return_value=["Movie.Name"],
        )
        post_path = mocker.patch("movie_runner.Movie.post_media_path")

        self.movieRunner.postMovies()

        assert Movie.get_all_movies() == {movie_path: {"pks": {1}, "finished": False}}
        mock_get_local_paths.assert_called_once()
        self.mock_reencodeFilesInDirectory.assert_not_called()
        post_path.assert_not_called()

    def test_local_legacy_movie_without_filename_remains_mapped(
        self, mocker, temp_directory
    ):
        mocker.patch("utils.BASE_PATH", str(temp_directory))
        mocker.patch("movie_runner.LOCAL_MOVIE_PATHS", ["movies"])
        local_dir = temp_directory / "movies" / "Legacy.Movie"
        local_dir.mkdir(parents=True)
        response = mock.Mock()
        response.json.return_value = {
            "results": [
                {
                    "media_path": {"pk": 3, "path": str(local_dir)},
                    "finished": False,
                }
            ],
            "next": "",
        }
        mocker.patch("movie_runner.get_data", return_value=response)

        assert Movie.get_all_movies() == {local_dir: {"pks": {3}, "finished": False}}

    @pytest.mark.parametrize("failure", ["video", "subtitle", "api"])
    def test_b2_failures_leave_movie_unpublished_for_retry(
        self, mocker, temp_directory, failure
    ):
        mocker.patch("movie_runner.B2_ENABLED", True)
        mocker.patch("movie_runner.LOCAL_MOVIE_PATHS", ["movies"])
        mocker.patch("movie_runner.BASE_PATH", temp_directory)
        mocker.patch("utils.B2_BUCKET_NAME", "bucket")
        mocker.patch("utils.B2_NAME_PREFIX", "prefix/")
        mocker.patch("movie_runner.Movie.get_all_movies", return_value={})
        filename_inventory = set()
        mocker.patch.object(
            MediaFile, "get_all_filenames", return_value=filename_inventory
        )
        mocker.patch(
            "movie_runner.MovieRunner._getLocalMoviePaths", return_value=["Film"]
        )
        mocker.patch("movie_runner.reencodeFilesInDirectory", return_value=None)
        video = temp_directory / "movies" / "Film" / "Film.converted.mp4"
        video.parent.mkdir(parents=True)
        video.write_bytes(b"encoded")
        mocker.patch(
            "movie_runner.MovieRunner._get_largest_video_file", return_value=video
        )
        path_post = mocker.patch(
            "movie_runner.Movie.post_media_path",
            return_value={
                "pk": 42,
                "bucket": "custom-bucket",
                "b2_upload_prefix": "archive/42/",
            },
        )
        upload = mocker.patch("movie_runner.b2.get_b2_client")
        subtitles = mocker.patch("movie_runner.upload_subtitle_files", return_value=[])
        record = mocker.patch.object(MediaFile, "post_media_file")
        if failure == "video":
            upload.return_value.upload_file.side_effect = RuntimeError("upload failed")
        elif failure == "subtitle":
            subtitles.side_effect = RuntimeError("subtitle failed")
        else:
            record.side_effect = RuntimeError("api failed")

        with pytest.raises(RuntimeError):
            MovieRunner().postMovies()

        path_post.assert_called_once_with("b2://bucket/prefix/Film/")
        assert upload.return_value.upload_file.called
        if failure == "video":
            subtitles.assert_not_called()
            record.assert_not_called()
        elif failure == "subtitle":
            record.assert_not_called()
        else:
            record.assert_called_once()
        assert video.name not in filename_inventory


class TestRun:
    @pytest.fixture(autouse=True)
    def setUp(self, mocker):
        self.mock_postMovies = mocker.patch("movie_runner.MovieRunner.postMovies")

        self.mock_info = mocker.patch("movie_runner.log.info")

        self.movieRunner = MovieRunner()
        self.errors = mock.MagicMock()
        self.movieRunner.errors = self.errors

    def test_run(self):
        expected = self.errors
        actual = self.movieRunner.run()

        assert expected == actual
        self.mock_postMovies.assert_called_once_with(dry_run=False)
        self.mock_info.assert_called_once_with("Done running movies")


class TestPromoteSubtitles:
    @pytest.fixture(autouse=True)
    def setUp(self, mocker):
        mocker.patch("movie_runner.SUBTITLE_FILES", ("English.srt", "2_Eng.srt"))

        self.mock_exists = mocker.patch("movie_runner.os.path.exists")

        self.mock_walk = mocker.patch("movie_runner.os.walk")

        self.mock_rename = mocker.patch("movie_runner.os.rename")

        self.mock_walk.return_value = [
            ("/path/to/movies/test_movie", ["Subs"], ["file1.mp4"]),
            ("/path/to/movies/test_movie/Subs", [], ["2_Eng.srt"]),
        ]

        self.mock_exists.return_value = True

    def test_path_does_not_exist(self):
        self.mock_exists.return_value = False

        expected = None
        actual = MovieRunner.promoteSubtitles("/path/to/movies/test_movie")

        assert expected == actual
        assert not self.mock_walk.called
        assert not self.mock_rename.called

    def test_2_Eng_exists_at_top_level(self):
        self.mock_walk.return_value = [
            ("/path/to/movies/test_movie", [], ["file1.mp4", "2_Eng.srt"]),
        ]

        expected = None
        actual = MovieRunner.promoteSubtitles("/path/to/movies/test_movie")

        assert expected == actual
        self.mock_walk.assert_called_once_with("/path/to/movies/test_movie")
        assert not self.mock_rename.called

    def test_English_exists_at_top_level(self):
        self.mock_walk.return_value = [
            ("/path/to/movies/test_movie", [], ["file1.mp4", "English.srt"]),
        ]

        expected = None
        actual = MovieRunner.promoteSubtitles("/path/to/movies/test_movie")

        assert expected == actual
        self.mock_walk.assert_called_once_with("/path/to/movies/test_movie")
        assert not self.mock_rename.called

    def test_rename_2_Eng(self):
        expected = None
        actual = MovieRunner.promoteSubtitles("/path/to/movies/test_movie")

        assert expected == actual
        self.mock_walk.assert_called_once_with("/path/to/movies/test_movie")
        self.mock_rename.assert_called_once_with(
            "/path/to/movies/test_movie/Subs/2_Eng.srt",
            "/path/to/movies/test_movie/2_Eng.srt",
        )

    def test_rename_English(self):
        self.mock_walk.return_value = [
            ("/path/to/movies/test_movie", ["Subs"], ["file1.mp4"]),
            ("/path/to/movies/test_movie/Subs", [], ["English.srt"]),
        ]

        expected = None
        actual = MovieRunner.promoteSubtitles("/path/to/movies/test_movie")

        assert expected == actual
        self.mock_walk.assert_called_once_with("/path/to/movies/test_movie")
        self.mock_rename.assert_called_once_with(
            "/path/to/movies/test_movie/Subs/English.srt",
            "/path/to/movies/test_movie/English.srt",
        )


class TestGetLocalMoviePaths:
    @pytest.fixture(autouse=True)
    def setUp(self, mocker):
        self.mock_exists = mocker.patch("movie_runner.os.path.exists")

        self.mock_listdir = mocker.patch("movie_runner.os.listdir")

        self.mock_exists.return_value = True

    def test_path_does_not_exist(self):
        self.mock_exists.return_value = False

        expected = set()
        actual = MovieRunner._getLocalMoviePaths("test_path")

        assert expected == actual
        self.mock_exists.assert_called_once_with("test_path")
        assert not self.mock_listdir.called

    def test_path_exists(self):
        expected = set(self.mock_listdir.return_value)
        actual = MovieRunner._getLocalMoviePaths("test_path")

        assert expected == actual
        self.mock_exists.assert_called_once_with("test_path")
        self.mock_listdir.assert_called_once_with("test_path")


class TestGetLargestVideoFile:
    def test_returns_largest_video_file(self, temp_directory):
        (temp_directory / "movie1.mp4").write_bytes(b"a" * 100)
        (temp_directory / "movie2.mkv").write_bytes(b"b" * 200)
        (temp_directory / "notes.txt").write_bytes(b"c" * 300)

        result = MovieRunner._get_largest_video_file(temp_directory)

        assert result == temp_directory / "movie2.mkv"

    def test_no_video_files_returns_none(self, temp_directory):
        (temp_directory / "notes.txt").write_bytes(b"c")

        result = MovieRunner._get_largest_video_file(temp_directory)

        assert result is None
