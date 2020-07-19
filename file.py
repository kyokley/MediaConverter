import requests

from log import LogFile
from settings import (
    MEDIAVIEWER_MOVIE_FILE_URL,
    MEDIAVIEWER_MOVIE_PATHFILES_URL,
    MEDIAVIEWER_TV_FILE_URL,
    MEDIAVIEWER_TV_PATHFILES_URL,
    VERIFY_REQUESTS,
    WAITER_PASSWORD,
    WAITER_USERNAME,
)
from utils import postData

log = LogFile().getLogger()


class File(object):
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
            log.error("Filename: %s Pathid: %s" % (self.filename, self.pathid))
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
