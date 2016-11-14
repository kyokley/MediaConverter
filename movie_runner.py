import os
import subprocess
import shlex
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
        self.errors = []

    def _getLocalMoviePathsSetting(self):
        return LOCAL_MOVIE_PATHS

    def postMovies(self):
        for moviepath in self._getLocalMoviePathsSetting():
            if not os.path.exists(moviepath):
                self.errors.append('%s does not exist. Continuing...' % moviepath)
                continue

            path = Path(moviepath, moviepath)
            path.postMovie()
            data = Path.getMoviePathByLocalPathAndRemotePath(moviepath, moviepath)
            pathid = data['results'][0]['pk']

            results = File.getMovieFileSet(pathid)
            fileset = [os.path.join(moviepath, res)
                           for res in results]

            tokens = self._getLocalMoviePaths(moviepath)

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

    @staticmethod
    def _getLocalMoviePaths(moviepath):
        if not os.path.exists(moviepath):
            return set()

        command = "ls '%s'" % moviepath
        p = subprocess.Popen(shlex.split(command),
                             stdout=subprocess.PIPE,
                             stderr=subprocess.STDOUT)
        res = p.communicate()[0]
        tokens = res.split('\n')
        return set([x for x in tokens if x])

    def run(self):
        self.postMovies()
        log.debug('Done running movies')
        return self.errors

    def _postMovie(self, name, pathid):
        if (not name or
                not pathid):
            log.error('Invalid request')
            log.error('Filename: %s Pathid: %s' % (name, pathid))
            return

        values = {'path': pathid,
                  'filename': name,
                  'skip': 1,
                  'size': 0,
                  'finished': 1,
                  'streamable': True,
                  }
        postData(values, MEDIAVIEWER_MOVIE_FILE_URL)
