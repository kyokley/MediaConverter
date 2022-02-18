import requests
from settings import (
    DOMAIN,
    WAITER_USERNAME,
    WAITER_PASSWORD,
    VERIFY_REQUESTS,
)
from utils import postData

import logging

log = logging.getLogger(__name__)


MEDIAVIEWER_MOVIE_FILE_URL = f"{DOMAIN}/mediaviewer/api/movie/"
MEDIAVIEWER_TV_FILE_URL = f"{DOMAIN}/mediaviewer/api/tv/"

MEDIAVIEWER_TV_PATHFILES_URL = f"{DOMAIN}/mediaviewer/api/tv/?pathid=%s"
MEDIAVIEWER_MOVIE_PATHFILES_URL = f"{DOMAIN}/mediaviewer/api/movie/?pathid=%s"


class File:
    def __init__(self, filename, pathid, size, streamable):
        self.filename = filename
        self.pathid = pathid
        self.size = size
        self.streamable = streamable

    def _post(self, useMovieURL=False):
        if useMovieURL:
            url = MEDIAVIEWER_MOVIE_FILE_URL
        else:
            url = MEDIAVIEWER_TV_FILE_URL

        if not self.filename or not self.pathid:
            log.error("Invalid request")
            log.error(f"Filename: {self.filename} Pathid: {self.pathid}")
            return

        values = {
            "path": self.pathid,
            "filename": self.filename,
            "skip": False,
            "size": self.size,
            "finished": True,
            "streamable": self.streamable,
        }
        postData(values, url)

    def postTVFile(self):
        self._post(useMovieURL=False)

    def postMovieFile(self):
        self._post(useMovieURL=True)

    @classmethod
    def _getFileSet(cls, pathid, useMovieURL=False):
        fileSet = set()
        if useMovieURL:
            url = MEDIAVIEWER_MOVIE_PATHFILES_URL
        else:
            url = MEDIAVIEWER_TV_PATHFILES_URL
        data = {"next": url % pathid}
        while data["next"]:
            r = requests.get(
                data["next"],
                verify=VERIFY_REQUESTS,
                auth=(WAITER_USERNAME, WAITER_PASSWORD),
            )
            r.raise_for_status()
            data = r.json()

            if data["results"]:
                for result in data["results"]:
                    fileSet.add(result["filename"])
        return fileSet

    @classmethod
    def getTVFileSet(cls, pathid):
        return cls._getFileSet(pathid, useMovieURL=False)

    @classmethod
    def getMovieFileSet(cls, pathid):
        return cls._getFileSet(pathid, useMovieURL=True)
