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
    def __init__(self, dryRun=False):
        self.movies = set()
        self.errors = []
        self.dryRun = dryRun

    def _getLocalMoviePathsSetting(self):
        return LOCAL_MOVIE_PATHS

    def postMovies(self, dryRun=False):
        self.results = []
        for moviepath in self._getLocalMoviePathsSetting():
            if not os.path.exists(moviepath):
                self.errors.append('{} does not exist. Continuing...'.format(moviepath))
                continue

            path = Path(moviepath, moviepath)
            path.postMovie()
            data = Path.getMoviePathByLocalPathAndRemotePath(moviepath, moviepath)
            pathid = data['results'][0]['pk']

            movie_file_set = File.getMovieFileSet(pathid)
            fileset = [os.path.join(moviepath, res)
                           for res in movie_file_set]

            tokens = self._getLocalMoviePaths(moviepath)

            for token in tokens:
                localpath = os.path.join(moviepath, token)
                if localpath not in fileset:
                    log.info("Found {}".format(localpath))
                    log.info("Adding job for {}".format(localpath))

                    self.results.append({'token': token,
                                         'pathid': pathid,
                                         'localpath': localpath,
                                         'asyncResults': reencodeFilesInDirectory(localpath, pathid, dryRun=dryRun or self.dryRun)})

            for result in self.results:
                for task in result.get('asyncResults'):
                    try:
                        dest, pathid = task.wait()

                        log.info("Finished recompressing {} for pathid = {}".format(dest, pathid))
                    except Exception, e:
                        log.error("Error processing {}".format(result.get('localpath')))
                        log.error(e)
                        self.errors.append(e)
                self._postMovie(result.get('token'), result.get('pathid'))

    @staticmethod
    def _getLocalMoviePaths(moviepath):
        if not os.path.exists(moviepath):
            return set()

        command = "ls '{}'".format(moviepath)
        p = subprocess.Popen(shlex.split(command),
                             stdout=subprocess.PIPE,
                             stderr=subprocess.STDOUT)
        res = p.communicate()[0]
        tokens = res.split('\n')
        return set([x for x in tokens if x])

    def run(self, dryRun=False):
        self.postMovies(dryRun=dryRun)
        log.debug('Done running movies')
        return self.errors

    def _postMovie(self, name, pathid):
        if (not name or
                not pathid):
            log.error('Invalid request')
            log.error('Filename: {} Pathid: {}'.format(name, pathid))
            return

        values = {'path': pathid,
                  'filename': name,
                  'skip': 1,
                  'size': 0,
                  'finished': 1,
                  'streamable': True,
                  }
        postData(values, MEDIAVIEWER_MOVIE_FILE_URL)
