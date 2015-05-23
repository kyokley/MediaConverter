import os
import commands, requests
from settings import (MOVIE_PATH_ID,
                      MEDIAVIEWER_MOVIE_URL,
                      LOCAL_MOVIE_PATH,
                      )
from convert import makeFileStreamable, reencodeFilesInDirectory
from file import File
from path import Path
from utils import postData

from log import LogFile
log = LogFile().getLogger()

FIND_FAIL_STRING = 'No such file or directory'

class TvRunner(object):
    def __init__(self):
        self.paths = dict()

    def loadPaths(self):
        self.paths = Path.getAllPaths()

    @staticmethod
    def getOrCreatePathForKey(key):
        print 'Get or create path for %s' % key
        newPath = Path(key, key)
        newPath.post()
        data = Path.getPathByLocalPathAndRemotePath(key, key)
        pathid = data['results'][0]['pk']
        print 'Got path'

        return pathid

    @staticmethod
    def buildRemoteFileSetForPathIDs(pathIDs):
        fileSet = set()
        for pathid in pathIDs:
            # Skip local paths
            if pathid == -1:
                continue
            remoteFilenames = File.getFileSet(pathid)
            fileSet.update(remoteFilenames)
        print 'Built fileSet'

        return fileSet

    def run(self):
        print 'Attempting to get paths'
        self.loadPaths()
        print 'Got paths'
        for key, vals in self.paths.items():
            res = commands.getoutput("find '%s' -maxdepth 1 -not -type d" % key)
            if MOVIE_PATH_ID in vals or FIND_FAIL_STRING in res:
                continue

            tokens = res.split('\n')
            tokens = [os.path.basename(x) for x in tokens]
            print tokens

            print 'Attempting to get files for %s' % key
            fileSet = self.buildRemoteFileSetForPathIDs(vals)

            pathid = None
            for token in tokens:
                if token and token not in fileSet:
                    try:
                        if not pathid:
                            pathid = self.getOrCreatePathForKey(key)

                        print "Attempting to add %s" % (token,)
                        fullPath = os.path.join(key, token)
                        try:
                            fullPath = makeFileStreamable(fullPath,
                                                          appendSuffix=True,
                                                          removeOriginal=True,
                                                          dryRun=False)
                        except Exception, e:
                            print e
                            log.error(e)
                            log.error("Something bad happened. Attempting to continue")

                        if os.path.exists(fullPath):
                            newFile = File(os.path.basename(fullPath),
                                           pathid,
                                           os.path.getsize(fullPath),
                                           True,
                                           )
                            newFile.post()
                    except Exception, e:
                        log.error(e)
                        continue
        print 'Done'

class MovieRunner(object):
    def __init__(self):
        self.movies = set()

    def loadMovies(self):
        self.movies = set()

        log.info("Loading movie paths")
        data = {'next': MEDIAVIEWER_MOVIE_URL}
        while data['next']:
            try:
                log.debug("Making API call with data: %s" % (data,))
                request = requests.get(data['next'])
                data = request.json()

                if data['results']:
                    for result in data['results']:
                        self.movies.add(result['filename'])
            except Exception, e:
                log.error("An error has occurred")
                log.error(e)

    def postMovies(self):
        res = commands.getoutput("ls '%s'" % (LOCAL_MOVIE_PATH,))
        tokens = res.split('\n')

        for token in tokens:
            if token not in self.movies:
                print "Found %s" % token
                print "Attempting to re-encode media files"
                log.info("Found %s. Starting re-encoding..." % token)
                try:
                    reencodeFilesInDirectory(token)
                except Exception, e:
                    print "Error processing %s" % token
                    log.error("Error processing %s" % token)
                    log.error(e)
                print "Posting %s" % (token,)
                log.info("Posting %s" % (token,))
                self._postMovie(token)

    def run(self):
        self.loadMovies()
        self.postMovies()

    def _postMovie(self, name):
        values = {'pathid': MOVIE_PATH_ID,
                  'filename': name,
                  'skip': 1,
                  'size': 0,
                  'finished': 1,
                  'streamable': True,
                  }
        postData(values, MEDIAVIEWER_MOVIE_URL)

if __name__ == '__main__':
    tvRunner = TvRunner()
    tvRunner.run()

    movieRunner = MovieRunner()
    movieRunner.run()
