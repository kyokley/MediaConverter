import os

import requests

from log import LogFile
from settings import (
    BASE_PATH,
    LOCAL_MOVIE_PATHS,
    LOCAL_TV_SHOWS_PATHS,
    MEDIAVIEWER_MOVIE_PATH_URL,
    MEDIAVIEWER_TV_PATH_URL,
    SERVER_NAME,
    VERIFY_REQUESTS,
    WAITER_PASSWORD,
    WAITER_USERNAME,
)
from utils import postData

log = LogFile().getLogger()


class Path(object):
    def __init__(self, localpath, remotepath):
        self.localpath = localpath
        self.remotepath = remotepath

    def _post(self, useMovieURL=False):
        if useMovieURL:
            url = MEDIAVIEWER_MOVIE_PATH_URL
        else:
            url = MEDIAVIEWER_TV_PATH_URL

        values = {
            "localpath": self.localpath,
            "remotepath": self.remotepath,
            "skip": False,
            "server": SERVER_NAME,
        }
        postData(values, url)

    def postMovie(self):
        self._post(useMovieURL=True)

    def postTVShow(self):
        self._post(useMovieURL=False)

    @classmethod
    def _getPaths(cls, getMovies=False):
        pathDict = dict()
        if getMovies:
            url = MEDIAVIEWER_MOVIE_PATH_URL
        else:
            url = MEDIAVIEWER_TV_PATH_URL

        data = {"next": url}
        while data["next"]:
            request = requests.get(
                data["next"],
                verify=VERIFY_REQUESTS,
                auth=(WAITER_USERNAME, WAITER_PASSWORD),
            )
            request.raise_for_status()
            data = request.json()

            if data["results"]:
                for result in data["results"]:
                    localpath = result["localpath"]
                    if BASE_PATH not in localpath:
                        localpath = os.path.join(BASE_PATH, localpath)

                    val = pathDict.setdefault(
                        localpath, {"pks": set(), "finished": result["finished"]}
                    )
                    val["pks"].add(result["pk"])
                    pathDict[localpath] = val
        return pathDict

    @classmethod
    def getTVPaths(cls):
        return cls._getPaths(getMovies=False)

    @classmethod
    def getMoviePaths(cls):
        return cls._getPaths(getMovies=True)

    @classmethod
    def _getLocalPaths(cls, getMovies=False):
        if getMovies:
            filepaths = LOCAL_MOVIE_PATHS
        else:
            filepaths = LOCAL_TV_SHOWS_PATHS

        return cls._buildLocalPaths(filepaths)

    @staticmethod
    def _buildLocalPaths(filepaths):
        localpaths = set()
        for localpath in filepaths:
            if not os.path.exists(localpath):
                log.error("{} does not exist. Continuing...".format(localpath))
                continue

            res = set(
                [
                    os.path.join(localpath, path)
                    for path in os.listdir(localpath)
                    if path
                ]
            )
            localpaths.update(res)
        return localpaths

    @classmethod
    def getLocalTVPaths(cls):
        return cls._getLocalPaths(getMovies=False)

    @classmethod
    def getLocalMoviePaths(cls):
        return cls._getLocalPaths(getMovies=True)

    @classmethod
    def _getAllPaths(cls, getMovies=False):
        """ Returns a dict of localpaths related to pathids
            Local paths not in the server are represented with pathid -1.
        """
        allPaths = cls._getPaths(getMovies=getMovies)
        localPaths = cls._getLocalPaths(getMovies=getMovies)

        for path in localPaths:
            val = allPaths.setdefault(path, {"pks": set(), "finished": False})
            val["pks"].add(-1)
            allPaths[path] = val
        return allPaths

    @classmethod
    def getAllTVPaths(cls):
        return cls._getAllPaths(getMovies=False)

    @classmethod
    def getAllMoviePaths(cls):
        return cls._getAllPaths(getMovies=True)

    @classmethod
    def _getPathByLocalPathAndRemotePath(
        cls, localpath, remotepath, useMovieURL=False,
    ):
        payload = {"localpath": localpath, "remotepath": remotepath}
        if useMovieURL:
            url = MEDIAVIEWER_MOVIE_PATH_URL
        else:
            url = MEDIAVIEWER_TV_PATH_URL
        request = requests.get(
            url,
            params=payload,
            verify=VERIFY_REQUESTS,
            auth=(WAITER_USERNAME, WAITER_PASSWORD),
        )
        request.raise_for_status()
        data = request.json()
        return data

    @classmethod
    def getTVPathByLocalPathAndRemotePath(cls, localpath, remotepath):
        return cls._getPathByLocalPathAndRemotePath(
            localpath, remotepath, useMovieURL=False
        )

    @classmethod
    def getMoviePathByLocalPathAndRemotePath(cls, localpath, remotepath):
        return cls._getPathByLocalPathAndRemotePath(
            localpath, remotepath, useMovieURL=True
        )
