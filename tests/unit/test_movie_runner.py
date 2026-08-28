import mock
import pytest

from pathlib import Path
from movie_runner import MovieRunner, Movie


def gen_data(num):
    return [dict(results=[dict(pk=i)]) for i in range(1, num + 1)]


class TestPostMovies:
    @pytest.fixture(autouse=True)
    def setUp(self, mocker, temp_directory):
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

    def test_postMovies_s3_enabled(self, mocker):
        mocker.patch("movie_runner.S3_ENABLED", True)
        mocker.patch("movie_runner.S3_BUCKET_NAME", "bucket")
        mocker.patch("movie_runner.S3_KEY_PREFIX", "prefix/")
        mocker.patch("utils.S3_BUCKET_NAME", "bucket")
        mocker.patch("utils.S3_KEY_PREFIX", "prefix/")
        mock_upload = mocker.patch("movie_runner.s3.get_s3_client")
        mock_post_media_path = mocker.patch("movie_runner.Movie.post_media_path")
        mocker.patch(
            "movie_runner.MovieRunner._get_largest_video_file",
            return_value=Path(f"{self.tmp_dir}/movies/movie1/Movie1.mp4"),
        )

        assert self.movieRunner.postMovies() is None
        assert not self.movieRunner.errors

        mock_upload.return_value.upload_file.assert_has_calls(
            [
                mock.call(
                    Path(f"{self.tmp_dir}/movies/movie1/Movie1.mp4"),
                    "bucket",
                    "prefix/movie1/Movie1.mp4",
                ),
                mock.call(
                    Path(f"{self.tmp_dir}/movies/movie1/Movie1.mp4"),
                    "bucket",
                    "prefix/movie2/Movie1.mp4",
                ),
                mock.call(
                    Path(f"{self.tmp_dir}/movies/movie1/Movie1.mp4"),
                    "bucket",
                    "prefix/movie3/Movie1.mp4",
                ),
            ]
        )
        mock_post_media_path.assert_has_calls(
            [
                mock.call("s3://bucket/prefix/movie1/", filename="Movie1.mp4"),
                mock.call("s3://bucket/prefix/movie2/", filename="Movie1.mp4"),
                mock.call("s3://bucket/prefix/movie3/", filename="Movie1.mp4"),
            ]
        )

    def test_postMovies_s3_enabled_no_video_file(self, mocker):
        mocker.patch("movie_runner.S3_ENABLED", True)
        mocker.patch("movie_runner.s3.get_s3_client")
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

    def test_get_all_movies_s3_reverse_mapping(self, mocker, temp_directory):
        mocker.patch("utils.BASE_PATH", temp_directory)
        mocker.patch("movie_runner.LOCAL_MOVIE_PATHS", ["movies"])
        local_dir = temp_directory / "movies" / "Movie.Name"
        local_dir.mkdir(parents=True)

        mock_response = mock.MagicMock()
        mock_response.json.return_value = {
            "results": [
                {
                    "media_path": {
                        "pk": 1,
                        "path": "s3://bucket/prefix/Movie.Name/",
                    },
                    "finished": False,
                }
            ],
            "next": "",
        }
        mocker.patch("movie_runner.get_data", return_value=mock_response)

        paths = Movie.get_all_movies()

        assert paths == {local_dir: {"pks": {1}, "finished": False}}


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
