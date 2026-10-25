import os
import uuid
from pathlib import Path
import b2
from settings import (
    LOCAL_MOVIE_PATHS,
    SUBTITLE_FILES,
    DOMAIN,
    BASE_PATH,
    B2_ENABLED,
)
from convert import reencodeFilesInDirectory
from utils import (
    get_data,
    put_data,
    get_b2_uri_for_local_path,
    get_local_path_from_media_path,
    is_valid_media_file,
    upload_subtitle_files,
)
from tv_runner import MediaPathMixin, MediaFile

import logging

log = logging.getLogger(__name__)


class Movie(MediaPathMixin):
    @classmethod
    @property
    def MEDIAVIEWER_MOVIE_URL(cls):
        return f"{DOMAIN}/mediaviewer/api/movie/"

    @classmethod
    @property
    def MEDIAVIEWER_MOVIE_DETAIL_URL(cls):
        return cls.MEDIAVIEWER_MOVIE_URL + "{movie_id}/"

    @classmethod
    def get_movie(cls, movie_id):
        resp = get_data(cls.MEDIAVIEWER_MOVIE_DETAIL_URL.format(movie_id=movie_id))
        resp.raise_for_status()
        return resp.json()

    @classmethod
    def put_movie(cls, movie_id, finished=False):
        payload = {"finished": finished}
        resp = put_data(
            payload, cls.MEDIAVIEWER_MOVIE_DETAIL_URL.format(movie_id=movie_id)
        )
        return resp.json()

    @classmethod
    @property
    def MEDIAVIEWER_MEDIAPATH_URL(cls):
        return DOMAIN + "/mediaviewer/api/moviemediapath/"

    @classmethod
    def get_all_movies(cls, incomplete_paths=None):
        paths = dict()

        data = {"next": cls.MEDIAVIEWER_MOVIE_URL}
        while data["next"]:
            request = get_data(data["next"])
            request.raise_for_status()
            data = request.json()

            if data["results"]:
                for result in data["results"]:
                    media_path = result["media_path"]

                    if media_path.get("path", "").startswith(
                        "b2://"
                    ) and not media_path.get("filename"):
                        local_path = get_local_path_from_media_path(
                            media_path["path"], LOCAL_MOVIE_PATHS
                        )
                        if incomplete_paths is not None:
                            existing = incomplete_paths.get(local_path)
                            if existing and existing["path"] != media_path["path"]:
                                raise ValueError(
                                    "Multiple incomplete B2 MediaPaths map to "
                                    f"{local_path}: {existing['path']}, "
                                    f"{media_path['path']}"
                                )
                            val = incomplete_paths.setdefault(
                                local_path,
                                {"path": media_path["path"], "pks": set()},
                            )
                            val["pks"].add(media_path["pk"])
                        continue

                    local_path = get_local_path_from_media_path(
                        media_path["path"], LOCAL_MOVIE_PATHS
                    )

                    val = paths.setdefault(
                        local_path, {"pks": set(), "finished": result["finished"]}
                    )
                    val["pks"].add(media_path["pk"])
                    paths[local_path] = val
        return paths


class MovieRunner:
    def __init__(self):
        self.movies = set()
        self.errors = []

    def postMovies(self, dry_run=False):
        base_path = Path(BASE_PATH)

        incomplete_paths = {}
        remote_paths = set(Movie.get_all_movies(incomplete_paths).keys())
        published_filenames = (
            MediaFile.get_all_filenames() if B2_ENABLED and not dry_run else set()
        )

        for moviepath_str in LOCAL_MOVIE_PATHS:
            moviepath = base_path / moviepath_str

            if not moviepath.exists():
                self.errors.append(f"{moviepath} does not exist. Continuing...")
                continue

            tokens = self._getLocalMoviePaths(moviepath)
            for token in tokens:
                localpath = moviepath / token
                if localpath not in remote_paths:
                    if B2_ENABLED and not dry_run:
                        candidate = self._get_largest_video_file(localpath)
                        if (
                            candidate is not None
                            and candidate.name in published_filenames
                        ):
                            log.info(
                                f"Skipping {localpath}: {candidate.name} already published"
                            )
                            continue
                    log.info(f"Found {localpath}")
                    log.info(f"Starting re-encoding of {localpath}...")
                    try:
                        self.promoteSubtitles(localpath, dry_run=dry_run)
                        if dry_run:
                            log.debug(f"Would re-encode files in {localpath}")
                        else:
                            errors = reencodeFilesInDirectory(localpath)

                        if not dry_run and errors:
                            self.errors.extend(errors)
                            continue
                    except Exception as e:
                        log.error(f"Error processing {localpath}")
                        log.error(str(e))
                        raise
                    log.info(f"Posting {localpath}")
                    if dry_run:
                        log.debug(f"Would post path for {localpath}")
                        continue
                    if B2_ENABLED:
                        video_file = self._get_largest_video_file(localpath)
                        if video_file is None:
                            self.errors.append(
                                f"No video file found in {localpath}. Continuing..."
                            )
                            continue
                        if video_file.name in published_filenames:
                            log.info(
                                f"Skipping {localpath}: {video_file.name} already published"
                            )
                            continue
                        incomplete_path = incomplete_paths.get(localpath)
                        logical_path = (
                            incomplete_path["path"]
                            if incomplete_path
                            else get_b2_uri_for_local_path(localpath)
                        )
                        media_path_data = Movie.post_media_path(logical_path)
                        key_prefix = media_path_data.get("b2_upload_prefix")
                        bucket = media_path_data.get("bucket")
                        if not key_prefix or not bucket:
                            raise ValueError(
                                "MediaPath response missing bucket or b2_upload_prefix"
                            )
                        b2_uuid = str(uuid.uuid4())
                        key = f"{key_prefix}{b2_uuid}{video_file.suffix}"
                        b2.get_b2_client().upload_file(video_file, bucket, key)
                        subtitle_files = upload_subtitle_files(
                            video_file,
                            localpath,
                            bucket=bucket,
                            key_prefix=key_prefix,
                        )
                        MediaFile.post_media_file(
                            video_file.name,
                            media_path_data["pk"],
                            video_file.stat().st_size,
                            subtitle_files=subtitle_files,
                            b2_uuid=b2_uuid,
                        )
                        published_filenames.add(video_file.name)
                    else:
                        Movie.post_media_path(localpath)

    @staticmethod
    def promoteSubtitles(localpath, dry_run=False):
        path = None
        if os.path.exists(localpath):
            for root, dirs, files in os.walk(localpath):
                for file in files:
                    if file in SUBTITLE_FILES:
                        path = os.path.join(root, file)
                        break

            if path and path != os.path.join(localpath, file):
                dest = os.path.join(localpath, file)

                if dry_run:
                    log.debug(f"Would rename {path} to {dest}")
                else:
                    os.rename(path, dest)

    @staticmethod
    def _getLocalMoviePaths(moviepath):
        if not os.path.exists(moviepath):
            return set()

        return {
            entry
            for entry in os.listdir(moviepath)
            if os.path.isdir(os.path.join(moviepath, entry))
        }

    @staticmethod
    def _get_largest_video_file(localpath):
        video_files = [
            f
            for f in Path(localpath).iterdir()
            if f.is_file() and is_valid_media_file(f)
        ]
        if not video_files:
            return None
        return max(video_files, key=lambda f: f.stat().st_size)

    def run(self, dry_run=False):
        self.postMovies(dry_run=dry_run)
        log.info("Done running movies")
        return self.errors


if __name__ == "__main__":
    runner = MovieRunner()
    errors = runner.run()
    if errors:
        print(errors)
