import os
import commands
import traceback
from file import File
from path import Path
from settings import SEND_EMAIL
from convert import makeFileStreamable
from utils import (stripUnicode,
                   EncoderException,
                   MissingPathException,
                   send_email)

from log import LogFile
log = LogFile().getLogger()

FIND_FAIL_STRING = 'No such file or directory'

class TvRunner(object):
    def __init__(self):
        self.paths = dict()
        self.errors = []

    def loadPaths(self):
        self.paths = Path.getAllTVPaths()

    @staticmethod
    def getOrCreateRemotePath(localPath):
        log.debug('Get or create path for %s' % localPath)
        newPath = Path(localPath, localPath)
        newPath.postTVShow()
        data = Path.getTVPathByLocalPathAndRemotePath(localPath, localPath)
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
            remoteFilenames = File.getTVFileSet(pathid)
            fileSet.update(remoteFilenames)
        log.debug('Built remote fileSet')

        return fileSet

    def updateFileRecords(self, path, localFileSet, remoteFileSet):
        pathid = None
        for localFile in localFileSet:
            if localFile and localFile not in remoteFileSet:
                try:
                    if not pathid:
                        pathid = self.getOrCreateRemotePath(path)

                    log.debug("Attempting to add %s" % (localFile,))
                    fullPath = stripUnicode(localFile, path=path)
                    try:
                        fullPath = makeFileStreamable(fullPath,
                                                      appendSuffix=True,
                                                      removeOriginal=True,
                                                      dryRun=False)
                    except EncoderException, e:
                        errorMsg = "Got a non-fatal encoding error attempting to make %s streamable" % fullPath
                        log.error(errorMsg)
                        log.error('Attempting to recover and continue')
                        self.errors.append(errorMsg)
                        continue

                    if os.path.exists(fullPath):
                        newFile = File(os.path.basename(fullPath),
                                       pathid,
                                       os.path.getsize(fullPath),
                                       True,
                                       )

                        newFile.postTVFile()
                except Exception, e:
                    errorMsg = "Something bad happened attempting to make %s streamable" % fullPath
                    log.error(errorMsg)
                    log.error(e)

                    if SEND_EMAIL:
                        subject = 'MC: Got some errors'
                        message = '''
                        %s
                        Got the following:
                        %s
                        ''' % (errorMsg, traceback.format_exc())
                        send_email(subject, message)
                    raise



    def buildLocalFileSet(self, path):
        local_files = commands.getoutput("find '%s' -maxdepth 1 -not -type d" % path)
        if FIND_FAIL_STRING in local_files:
            raise MissingPathException('Path not found: %s' % path)

        localFileSet = local_files.split('\n')
        localFileSet = set([os.path.basename(x) for x in localFileSet])
        log.debug(localFileSet)
        return localFileSet

    def run(self):
        log.debug('Attempting to get paths')
        self.loadPaths()
        log.debug('Got paths')
        for path, pathIDs in self.paths.items():
            try:
                log.debug('Building local file set for %s' % path)
                localFileSet = self.buildLocalFileSet(path)
                log.debug('Done building local file set for %s' % path)
            except MissingPathException, e:
                log.error(e)
                log.error('Continuing...')
                continue

            log.debug('Attempting to get remote files for %s' % path)
            remoteFileSet = self.buildRemoteFileSetForPathIDs(pathIDs)
            log.debug('Done building remote file set for %s' % path)

            self.updateFileRecords(path, localFileSet, remoteFileSet)

        if self.errors:
            log.error('Errors occured in the following files:')
            for error in self.errors:
                log.error(error)
        log.debug('Done running tv shows')
        return self.errors
