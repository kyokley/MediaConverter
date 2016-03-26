import requests, commands, os
from settings import (LOCAL_TV_SHOWS_PATH,
                      SERVER_NAME,
                      MEDIAVIEWER_TV_PATH_URL,
                      MEDIAVIEWER_MOVIE_PATH_URL,
                      WAITER_USERNAME,
                      WAITER_PASSWORD,
                      LOCAL_TV_SHOWS_PATHS,
                      LOCAL_MOVIE_PATHS,
                      )
from utils import postData

class Path(object):
    def __init__(self,
                 localpath,
                 remotepath):
        self.localpath = localpath
        self.remotepath = remotepath

    def _post(self, useMovieURL=False):
        if useMovieURL:
            url = MEDIAVIEWER_MOVIE_PATH_URL
        else:
            url = MEDIAVIEWER_TV_PATH_URL

        values = {'localpath': self.localpath,
                  'remotepath': self.remotepath,
                  'skip': False,
                  'server': SERVER_NAME,
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

        data = {'next': url}
        while data['next']:
            request = requests.get(data['next'], verify=False, auth=(WAITER_USERNAME, WAITER_PASSWORD))
            data = request.json()

            if data['results']:
                for result in data['results']:
                    if result['is_movie'] == getMovies:
                        pathDict.setdefault(result['localpath'], set()).add(result['pk'])
        return pathDict

    @classmethod
    def getTVPaths(cls):
        return cls._getPaths(getMovies=False)

    @classmethod
    def getMoviePaths(cls):
        return cls._getPath(getMovies=True)

    @classmethod
    def _getLocalPaths(cls, getMovies=False):
        localpaths = set()
        if getMovies:
            filepaths = LOCAL_MOVIE_PATHS
        else:
            filepaths = LOCAL_TV_SHOWS_PATHS

        for localpath in filepaths:
            res = commands.getoutput("ls '%s'" % localpath)
            res = res.split('\n')
            res = set([os.path.join(localpath, path) for path in res])
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
        ''' Returns a dict of localpaths related to pathids
            Local paths not in the server are represented with pathid -1.
        '''
        allPaths = cls._getPaths(getMovies=getMovies)
        localPaths = cls._getLocalPaths(getMovies=getMovies)

        for path in localPaths:
            allPaths.setdefault(path, set()).add(-1)
        return allPaths

    @classmethod
    def getAllTVPaths(cls):
        return cls._getAllPaths(getMovies=False)

    @classmethod
    def getAllMoviePaths(cls):
        return cls._getAllPaths(getMovies=True)

    @classmethod
    def _getPathByLocalPathAndRemotePath(cls,
                                         localpath,
                                         remotepath,
                                         useMovieURL=False,
                                        ):
        payload = {'localpath': localpath, 'remotepath': remotepath}
        if useMovieURL:
            url = MEDIAVIEWER_MOVIE_PATH_URL
        else:
            url = MEDIAVIEWER_TV_PATH_URL
        request = requests.get(url,
                               params=payload,
                               verify=False,
                               auth=(WAITER_USERNAME, WAITER_PASSWORD),
                               )
        data = request.json()
        return data

    @classmethod
    def getTVPathByLocalPathAndRemotePath(cls, localpath, remotepath):
        return cls._getPathByLocalPathAndRemotePath(localpath,
                                                    remotepath,
                                                    useMovieURL=False)

    @classmethod
    def getMoviePathByLocalPathAndRemotePath(cls, localpath, remotepath):
        return cls._getPathByLocalPathAndRemotePath(localpath,
                                                    remotepath,
                                                    useMovieURL=True)
