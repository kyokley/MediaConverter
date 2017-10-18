import os
import traceback
import subprocess
import shlex
import shutil
from file import File
from path import Path
from settings import SEND_EMAIL, MEDIA_FILE_EXTENSIONS
from convert import makeFileStreamable
from utils import (stripUnicode,
                   EncoderException,
                   MissingPathException,
                   send_email,
                   )

from log import LogFile
log = LogFile().getLogger()

FIND_FAIL_STRING = 'No such file or directory'
IGNORED_FILE_EXTENSIONS = ('.vtt', '.srt')
SUBTITLE_FILE = '2_Eng.srt'

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

    @staticmethod
    def buildLocalFileSet(path):
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

    def handleDirs(self, path):
        if os.path.exists(path):
            paths = []
            dir_set = set()
            for root, dirs, files in os.walk(path):
                for file in files:
                    paths.append(os.path.join(root, file))

            for fullpath in paths:
                dirs = fullpath.split(os.path.sep)
                top, episode, file = dirs[0], dirs[1], dirs[-1]
                file_ext = os.path.splitext(file)[-1].lower()

                if os.path.isdir(episode):
                    dir_set.add(os.path.join(top, episode))

                    if file == SUBTITLE_FILE:
                        # Move subtitle to show directory and rename
                        log.info('Found subtitle file in {}'.format(episode))
                        new = os.path.join(top, episode + '.srt')
                        os.rename(fullpath, new)

                    elif file_ext in MEDIA_FILE_EXTENSIONS:
                        # Move media file to show directory
                        log.info('Found media file in {}'.format(episode))
                        new = os.path.join(top, file)
                        os.rename(fullpath, new)

            for directory in dir_set:
                log.info('Deleting {}'.format(directory))
                shutil.rmtree(directory)


    def run(self):
        log.debug('Attempting to get paths')
        self.loadPaths()
        log.debug('Got paths')
        for path, pathIDs in self.paths.items():
            try:
                log.debug('Handling directories in {}'.format(path))
                self.handleDirs(path)
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
