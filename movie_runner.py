import commands, os
from settings import (MEDIAVIEWER_MOVIE_FILE_URL,
                      LOCAL_MOVIE_PATHS,
                      )
from convert import reencodeFilesInDirectory
from utils import postData
from path import Path
from file import File

from log import LogFile
log = LogFile().getLogger()

class MovieRunner(object):
    def __init__(self):
        self.movies = set()
        #self.remoteMoviePaths = set()
        self.movies = set()
        self.errors = []

    #def loadMovies(self):
        #self.remoteMoviePaths = Path.getMoviePaths()

    def _getLocalMoviePathsSetting(self):
        return LOCAL_MOVIE_PATHS

    def postMovies(self):
        for moviepath in self._getLocalMoviePathsSetting():
            path = Path(moviepath, moviepath)
            path.postMovie()
            data = Path.getMoviePathByLocalPathAndRemotePath(moviepath, moviepath)
            pathid = data['results'][0]['pk']

            results = File.getMovieFileSet(pathid)
            fileset = [os.path.join(moviepath, res)
                           for res in results]

            res = commands.getoutput("ls '%s'" % (moviepath,))
            tokens = res.split('\n')

            for token in tokens:
                localpath = os.path.join(moviepath, token)
                if localpath not in fileset:
                    log.info("Found %s" % localpath)
                    log.info("Starting re-encoding of %s..." % localpath)
                    try:
                        errors = reencodeFilesInDirectory(localpath)

                        if errors:
                            self.errors.extend(errors)
                            continue
                    except Exception, e:
                        log.error("Error processing %s" % localpath)
                        log.error(e)
                        raise
                    log.info("Posting %s" % (localpath,))
                    self._postMovie(token, pathid)

    def run(self):
        self.loadMovies()
        self.postMovies()
        log.debug('Done running movies')
        return self.errors

    def _postMovie(self, name, pathid):
        values = {'path': pathid,
                  'filename': name,
                  'skip': 1,
                  'size': 0,
                  'finished': 1,
                  'streamable': True,
                  }
        postData(values, MEDIAVIEWER_MOVIE_FILE_URL)
