import os
import traceback
import subprocess  # nosec
import shlex
import shutil

from file import File
from path import Path
from settings import (
    SEND_EMAIL,
    MEDIA_FILE_EXTENSIONS,
    SUBTITLE_FILES,
    UNSORTED_PATHS,
    BASE_PATH,
)
from convert import makeFileStreamable
from utils import (
    stripUnicode,
    EncoderException,
    MissingPathException,
    send_email,
    get_localpath_by_filename,
)

import logging

log = logging.getLogger(__name__)

FIND_FAIL_STRING = b"No such file or directory"
IGNORED_FILE_EXTENSIONS = (".vtt", ".srt")

SMALL_FILE_SIZE = 1024 * 1024 * 10  # 10 MB


class TvRunner:
    def __init__(self):
        self.paths = dict()
        self.errors = []

    def loadPaths(self):
        self.paths = {
            key: val["pks"]
            for key, val in Path.getAllTVPaths().items()
            if not val["finished"]
        }

    @staticmethod
    def getOrCreateRemotePath(localPath):
        log.info(f"Get or create path for {localPath}")
        newPath = Path(localPath, localPath)
        newPath.postTVShow()
        data = Path.getTVPathByLocalPathAndRemotePath(localPath, localPath)
        pathid = data["results"][0]["pk"]
        log.info("Got path")

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
        log.info("Built remote fileSet")

        return fileSet

    def updateFileRecords(self, path, localFileSet, remoteFileSet):
        pathid = None
        for localFile in localFileSet.difference(remoteFileSet):
            if not localFile:
                continue

            try:
                if not pathid:
                    pathid = self.getOrCreateRemotePath(path)

                log.info(f"Attempting to add {localFile}")
                fullPath = stripUnicode(localFile, path=path)
                try:
                    fullPath = makeFileStreamable(
                        fullPath, appendSuffix=True, removeOriginal=True, dryRun=False
                    )
                except EncoderException:
                    errorMsg = f"Got a non-fatal encoding error attempting to make {fullPath} streamable"
                    log.error(errorMsg)
                    log.error("Attempting to recover and continue")
                    self.errors.append(errorMsg)
                    continue

                if os.path.exists(fullPath):
                    newFile = File(
                        os.path.basename(fullPath),
                        pathid,
                        os.path.getsize(fullPath),
                        True,
                    )

                    newFile.postTVFile()
            except Exception as e:
                errorMsg = (
                    f"Something bad happened attempting to make {fullPath} streamable"
                )
                log.error(errorMsg)
                log.error(e)

                if SEND_EMAIL:
                    subject = "MC: Got some errors"
                    message = f"""
                    {errorMsg}
                    Got the following:
                    {traceback.format_exc()}
                    """
                    send_email(subject, message)
                raise

    @staticmethod
    def buildLocalFileSet(path):
        command = f"find '{path}' -maxdepth 1 -size +{SMALL_FILE_SIZE}c -not -type d"
        p = subprocess.Popen(
            shlex.split(command),  # nosec
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
        )
        local_files = p.communicate()[0]

        if FIND_FAIL_STRING in local_files:
            raise MissingPathException(f"Path not found: {path}")

        localFileSet = local_files.split(b"\n")
        localFileSet = set(
            [
                os.path.basename(x).decode("utf-8")
                for x in localFileSet
                if x and os.path.splitext(x)[1] not in IGNORED_FILE_EXTENSIONS
            ]
        )
        log.info(localFileSet)
        return localFileSet

    def handleDirs(self, path):
        if os.path.exists(path):
            paths = []
            dir_set = set()
            for root, dirs, files in os.walk(path):
                for file in files:
                    paths.append(os.path.join(root, file))

            for fullpath in paths:
                dirs = fullpath.split(path)[1].split(os.path.sep)
                top, episode, file = path, dirs[1], dirs[-1]
                file_ext = os.path.splitext(file)[-1].lower()

                dir_path = os.path.join(top, episode)
                if os.path.isdir(dir_path):
                    dir_set.add(dir_path)

                    if file in SUBTITLE_FILES:
                        # Move subtitle to show directory and rename
                        log.info(f"Found subtitle file in {episode}")
                        new = os.path.join(top, episode + ".srt")
                        os.rename(fullpath, new)

                    elif (
                        file_ext in MEDIA_FILE_EXTENSIONS
                        and os.path.getsize(fullpath) > SMALL_FILE_SIZE
                    ):
                        # Move media file to show directory
                        log.info(f"Found media file in {episode}")
                        new = os.path.join(top, file)
                        os.rename(fullpath, new)

            for directory in dir_set:
                log.info(f"Deleting {directory}")
                shutil.rmtree(directory)

    def run(self):
        log.info("Attempting to sort unsorted files")
        self._sort_unsorted_files()

        log.info("Attempting to get paths")
        self.loadPaths()
        log.info("Got paths")
        for path, pathIDs in self.paths.items():
            try:
                log.info(f"Handling directories in {path}")
                self.handleDirs(path)
                log.info(f"Building local file set for {path}")
                localFileSet = self.buildLocalFileSet(path)
                log.info(f"Done building local file set for {path}")
            except MissingPathException as e:
                log.error(e)
                log.error("Continuing...")
                continue

            log.info(f"Attempting to get remote files for {path}")
            remoteFileSet = self.buildRemoteFileSetForPathIDs(pathIDs)
            log.info(f"Done building remote file set for {path}")

            self.updateFileRecords(path, localFileSet, remoteFileSet)

        if self.errors:
            log.error("Errors occured in the following files:")
            for error in self.errors:
                log.error(error)
        log.info("Done running tv shows")
        return self.errors

    @staticmethod
    def _sort_unsorted_files():
        for unsorted_path in UNSORTED_PATHS:
            if BASE_PATH not in unsorted_path:
                unsorted_path = os.path.join(BASE_PATH, unsorted_path)

            if not os.path.exists(unsorted_path):
                log.info(f"Unsorted file path {unsorted_path} does not exist")
                return

            for filename in os.listdir(unsorted_path):
                src = os.path.join(unsorted_path, filename)

                localpath = get_localpath_by_filename(filename)
                if not localpath or not os.path.exists(localpath):
                    continue

                dst = os.path.join(localpath, filename)
                shutil.move(src, dst)
