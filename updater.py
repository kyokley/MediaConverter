import os
import commands, requests
from settings import (LOCAL_PATH,
                      MOVIE_PATH_ID,
                      WAITER_USERNAME,
                      WAITER_PASSWORD,
                      MEDIAVIEWER_PATH_URL,
                      MEDIAVIEWER_FILE_URL,
                      MEDIAVIEWER_PATHFILES_URL,
                      MEDIAVIEWER_CERT,
                      SERVER_NAME,
                      MEDIAVIEWER_MOVIE_URL,
                      LOCAL_MOVIE_PATH,
                      )
from convert import makeFileStreamable, reencodeFilesInDirectory

from log import LogFile
log = LogFile().getLogger()

FIND_FAIL_STRING = 'No such file or directory'

class TvRunner(object):
    def __init__(self):
        self.paths = dict()

    def loadPaths(self):
        self.paths = Path.getAllPaths()

    def run(self):
        print 'Attempting to get paths'
        self.loadPaths()
        print 'Got paths'
        for key, vals in self.paths.items():
            res = commands.getoutput("find '%s' -maxdepth 1 -not -type d" % key)
            if MOVIE_PATH_ID in vals or FIND_FAIL_STRING in res:
                continue

            tokens = res.split('\n')
            tokens = map(os.path.basename, tokens)
            print tokens

            print 'Attempting to get files for %s' % key
            fileSet = set()
            for pathid in vals:
                # Skip local paths
                if pathid == -1:
                    continue
                remoteFilenames = File.getFileSet(pathid)
                fileSet.update(remoteFilenames)
            print 'Built fileSet'

            pathid = None
            for token in tokens:
                if token and token not in fileSet:
                    try:
                        if not pathid:
                            print 'Get or create path for %s' % key
                            newPath = Path(key, key)
                            newPath.post()
                            data = Path.getPathByLocalPathAndRemotePath(key, key)
                            pathid = data['results'][0]['pk']
                            print 'Got path'

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

def postData(values, url):
    try:
        log.debug(values)
        request = requests.post(url, data=values, auth=(WAITER_USERNAME, WAITER_PASSWORD), verify=False)
        request.raise_for_status()
    except Exception, e:
        log.error(e)

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

class Path(object):
    def __init__(self,
                 localpath,
                 remotepath):
        self.localpath = localpath
        self.remotepath = remotepath

    def post(self):
        values = {'localpath': self.localpath,
                  'remotepath': self.remotepath,
                  'skip': 1,
                  'server': SERVER_NAME,
                  }
        postData(values, MEDIAVIEWER_PATH_URL)

    @classmethod
    def getPaths(cls):
        pathDict = dict()
        data = {'next': MEDIAVIEWER_PATH_URL}
        while data['next']:
            request = requests.get(data['next'], verify=False)
            data = request.json()

            if data['results']:
                for result in data['results']:
                    pathDict.setdefault(result['localpath'], set()).add(result['pk'])
        return pathDict

    @classmethod
    def getLocalPaths(cls):
        res = commands.getoutput("ls '%s'" % LOCAL_PATH)
        res = res.split('\n')
        res = set([os.path.join(LOCAL_PATH, path) for path in res])
        return res

    @classmethod
    def getAllPaths(cls):
        allPaths = cls.getPaths()
        localPaths = cls.getLocalPaths()

        for path in localPaths:
            allPaths.setdefault(path, set()).add(-1)
        return allPaths

    @classmethod
    def getPathByLocalPathAndRemotePath(cls,
                                        localpath,
                                        remotepath,
                                        ):
        payload = {'localpath': localpath, 'remotepath': remotepath}
        request = requests.get(MEDIAVIEWER_PATH_URL, params=payload, verify=False)
        data = request.json()
        return data

class File(object):
    def __init__(self,
                 filename,
                 pathid,
                 size,
                 streamable):
        self.filename = filename
        self.pathid = pathid
        self.size = size
        self.streamable = streamable

    def post(self):
        values = {'pathid': self.pathid,
                  'filename': self.filename,
                  'skip': 1,
                  'size': self.size,
                  'finished': 1,
                  'streamable': self.streamable,
                  }
        postData(values, MEDIAVIEWER_FILE_URL)

    @classmethod
    def getFileSet(cls, pathid):
        fileSet = set()
        data = {'next': MEDIAVIEWER_PATHFILES_URL % pathid}
        while data['next']:
            r = requests.get(data['next'], verify=MEDIAVIEWER_CERT)
            data = r.json()

            if data['results']:
                for result in data['results']:
                    fileSet.add(result['filename'])
        return fileSet

if __name__ == '__main__':
    tvRunner = TvRunner()
    tvRunner.run()

    movieRunner = MovieRunner()
    movieRunner.run()
