import os, commands
from file import File
from path import Path
from convert import makeFileStreamable
from settings import MOVIE_PATH_ID
from utils import stripUnicode

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
        log.debug('Get or create path for %s' % localPath)
        newPath = Path(localPath, localPath)
        newPath.post()
        data = Path.getPathByLocalPathAndRemotePath(localPath, localPath)
        pathid = data['results'][0]['pk']
        log.debug('Got path')

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
        log.debug('Built fileSet')

        return fileSet

    def updateFileRecords(self, path, localFileSet, remoteFileSet):
        pathid = None
        for localFile in localFileSet:
            if localFile not in remoteFileSet:
                try:
                    if not pathid:
                        pathid = self.getOrCreateRemotePath(path)

                    log.debug("Attempting to add %s" % (localFile,))
                    fullPath = stripUnicode(path, localFile)
                    try:
                        fullPath = makeFileStreamable(fullPath,
                                                      appendSuffix=True,
                                                      removeOriginal=True,
                                                      dryRun=False)
                    except Exception, e:
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



    def buildLocalFileSet(self, path):
        local_files = commands.getoutput("find '%s' -maxdepth 1 -not -type d" % path)
        if FIND_FAIL_STRING in local_files:
            raise Exception('Path not found: %s' % path)

        localFileSet = local_files.split('\n')
        localFileSet = set([os.path.basename(x) for x in localFileSet])
        log.debug(localFileSet)
        return localFileSet

    def run(self):
        log.debug('Attempting to get paths')
        self.loadPaths()
        log.debug('Got paths')
        for path, pathIDs in self.paths.items():
            if MOVIE_PATH_ID in pathIDs:
                continue

            try:
                localFileSet = self.buildLocalFileSet(path)
            except:
                continue

            log.debug('Attempting to get files for %s' % path)
            remoteFileSet = self.buildRemoteFileSetForPathIDs(pathIDs)

            self.updateFileRecords(path, localFileSet, remoteFileSet)

        log.debug('Done')
