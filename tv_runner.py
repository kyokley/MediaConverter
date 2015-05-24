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
    def getOrCreateRemotePath(localPath):
        print 'Get or create path for %s' % localPath
        newPath = Path(localPath, localPath)
        newPath.post()
        data = Path.getPathByLocalPathAndRemotePath(localPath, localPath)
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

    def updateFileRecords(self, path, localFileSet, remoteFileSet):
        pathid = None
        for localFile in localFileSet:
            if localFile not in remoteFileSet:
                try:
                    if not pathid:
                        pathid = self.getOrCreateRemotePath(path)

                    print "Attempting to add %s" % (localFile,)
                    fullPath = os.path.join(path, localFile)
                    try:
                        fullPath = makeFileStreamable(fullPath,
                                                      appendSuffix=True,
                                                      removeOriginal=True,
                                                      dryRun=False)
                    except Exception, e:
                        print e
                        log.error(e)
                        log.error("Something bad happened. Attempting to continue")

                    import pdb; pdb.set_trace()
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
        for path, pathIDs in self.paths.items():
            local_files = commands.getoutput("find '%s' -maxdepth 1 -not -type d" % path)
            if MOVIE_PATH_ID in pathIDs or FIND_FAIL_STRING in local_files:
                continue

            localFileSet = set(local_files.split('\n'))
            localFileSet = [os.path.basename(x) for x in localFileSet]
            print localFileSet

            print 'Attempting to get files for %s' % path
            remoteFileSet = self.buildRemoteFileSetForPathIDs(pathIDs)

            self.updateFileRecords(path, localFileSet, remoteFileSet)

        print 'Done'
