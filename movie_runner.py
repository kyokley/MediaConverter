import os
from pathlib import Path
from settings import (
    LOCAL_MOVIE_PATHS,
    SUBTITLE_FILES,
    DOMAIN,
    BASE_PATH,
)
from convert import reencodeFilesInDirectory
from utils import get_data
from tv_runner import MediaPathMixin

import logging

log = logging.getLogger(__name__)


class Movie(MediaPathMixin):
    MEDIAVIEWER_MOVIE_URL = f"{DOMAIN}/mediaviewer/api/movie/"
    MEDIAVIEWER_MEDIAPATH_URL = DOMAIN + "/mediaviewer/api/moviemediapath/"

    @classmethod
    def get_all_movies(cls):
        paths = dict()

        data = {"next": cls.MEDIAVIEWER_MOVIE_URL}
        while data["next"]:
            request = get_data(data['next'])
            request.raise_for_status()
            data = request.json()

            if data["results"]:
                for result in data["results"]:
                    media_paths = result['media_paths']

                    for media_path in media_paths:
                        if BASE_PATH not in media_path:
                            local_path = BASE_PATH / media_path

                        val = paths.setdefault(
                            local_path, {"pks": set(), "finished": result["finished"]}
                        )
                        val["pks"].add(result["pk"])
                        paths[local_path] = val
        return paths


class MovieRunner:
    def __init__(self):
        self.movies = set()
        self.errors = []

    def postMovies(self):
        base_path = Path(BASE_PATH)

        remote_paths = set(Movie.get_all_movies().keys())

        for moviepath_str in LOCAL_MOVIE_PATHS:
            moviepath = base_path / moviepath_str

            if not moviepath.exists():
                self.errors.append(f"{moviepath} does not exist. Continuing...")
                continue

            tokens = self._getLocalMoviePaths(moviepath)
            for token in tokens:
                localpath = os.path.join(moviepath, token)
                if localpath not in remote_paths:
                    log.info(f"Found {localpath}")
                    log.info(f"Starting re-encoding of {localpath}...")
                    try:
                        self.promoteSubtitles(localpath)
                        errors = reencodeFilesInDirectory(localpath)

                        if errors:
                            self.errors.extend(errors)
                            continue
                    except Exception as e:
                        log.error(f"Error processing {localpath}")
                        log.error(str(e))
                        raise
                    log.info(f"Posting {localpath}")
                    Movie.post_media_path(localpath)

    @staticmethod
    def promoteSubtitles(localpath):
        path = None
        if os.path.exists(localpath):
            for root, dirs, files in os.walk(localpath):
                for file in files:
                    if file in SUBTITLE_FILES:
                        path = os.path.join(root, file)
                        break

            if path and path != os.path.join(localpath, file):
                dest = os.path.join(localpath, file)
                os.rename(path, dest)

    @staticmethod
    def _getLocalMoviePaths(moviepath):
        if not os.path.exists(moviepath):
            return set()

        return set(os.listdir(moviepath))

    def run(self):
        self.postMovies()
        log.info("Done running movies")
        return self.errors
