import time
import os
import subprocess
import shlex
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
IGNORED_FILE_EXTENSIONS = ('.vtt', '.srt')

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
        tasks = []
        for localFile in localFileSet:
            if localFile and localFile not in remoteFileSet:
                if not pathid:
                    pathid = self.getOrCreateRemotePath(path)

                log.debug("Attempting to add %s" % (localFile,))
                fullPath = stripUnicode(localFile, path=path)

                task = makeFileStreamable.delay(fullPath,
                                                pathid,
                                                appendSuffix=True,
                                                removeOriginal=True,
                                                dryRun=False)
                tasks.append(task)
        return tasks


    def buildLocalFileSet(self, path):
        command = "find '%s' -maxdepth 1 -not -type d" % path
        p = subprocess.Popen(shlex.split(command),
                             stdout=subprocess.PIPE,
                             stderr=subprocess.STDOUT)
        local_files = p.communicate()[0]

        if FIND_FAIL_STRING in local_files:
            raise MissingPathException('Path not found: %s' % path)

        localFileSet = local_files.split('\n')
        localFileSet = set([os.path.basename(x) for x in localFileSet
                                if x and os.path.splitext(x)[1] not in IGNORED_FILE_EXTENSIONS])
        log.debug(localFileSet)
        return localFileSet

    def run(self):
        log.debug('Attempting to get paths')
        self.loadPaths()
        log.debug('Got paths')
        tasks = []
        errors = []

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

            tasks.extend(self.updateFileRecords(path, localFileSet, remoteFileSet))

        done = False
        while not done:
            time.sleep(1)
            for task in tasks:
                if not task.successful() and not task.failed():
                    break
            else:
                done = True

        for task in tasks:
            if task.successful():
                fullPath, pathid = task.result
                if os.path.exists(fullPath):
                    newFile = File(os.path.basename(fullPath),
                                   pathid,
                                   os.path.getsize(fullPath),
                                   True,
                                   )

                    newFile.postTVFile()
            elif task.failed():
                error = task.get(propagate=False)
                log.error(error)
                errors.append(error)

        if SEND_EMAIL and errors:
            subject = 'MC: Got some errors'
            send_email(subject, '\n'.join(errors))

        log.debug('Done running tv shows')
        return errors
