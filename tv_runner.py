import os, commands
from file import File
from path import Path
from convert import makeFileStreamable
from settings import MOVIE_PATH_ID

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

    def updateFileRecords(self, key, tokens, fileSet):
        pathid = None
        for token in tokens:
            if token not in fileSet:
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

            self.updateFileRecords(key, tokens, fileSet)

        print 'Done'
