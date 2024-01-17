import os
import traceback
import subprocess  # nosec
import shlex
import shutil

from pathlib import Path
from settings import (
    BASE_PATH,
    SEND_EMAIL,
    MEDIA_FILE_EXTENSIONS,
    UNSORTED_PATHS,
    MINIMUM_FILE_SIZE,
    DOMAIN,
)
from convert import makeFileStreamable, SkipProcessing, AlreadyEncoded
from utils import (
    stripUnicode,
    EncoderException,
    MissingPathException,
    send_email,
    get_localpath_by_filename,
    post_data,
    get_data,
)

import logging

log = logging.getLogger(__name__)

FIND_FAIL_STRING = b"No such file or directory"
IGNORED_FILE_EXTENSIONS = (".vtt", ".srt")


MEDIAVIEWER_TV_URL = f"{DOMAIN}/mediaviewer/api/tv/"
MEDIAVIEWER_MEDIAPATH_URL = f"{DOMAIN}/mediaviewer/api/mediapath/"
MEDIAVIEWER_MEDIAFILE_URL = f"{DOMAIN}/mediaviewer/api/mediafile/"


class Tv:
    @classmethod
    def get_all_tv(cls):
        paths = dict()

        data = {"next": MEDIAVIEWER_TV_URL}
        while data["next"]:
            request = get_data(data['next'])
            request.raise_for_status()
            data = request.json()

            if data["results"]:
                for result in data["results"]:
                    media_paths = result['media_paths']

                    for media_path in media_paths:
                        if BASE_PATH not in media_path:
                            local_path = BASE_PATH / media_path

                        val = paths.setdefault(
                            local_path, {"pks": set(), "finished": result["finished"]}
                        )
                        val["pks"].add(result["pk"])
                        paths[local_path] = val

    @classmethod
    def post_media_path(cls, path):
        payload = {'path': path}
        resp = post_data(payload, MEDIAVIEWER_MEDIAPATH_URL)
        resp.raise_for_status()
        return resp.json()


class MediaFile:
    @classmethod
    def post_media_file(
        cls,
        filename,
        media_path_id,
        size,
    ):
        payload = {'filename': filename,
                   'media_path': media_path_id,
                   'size': size}
        resp = post_data(payload, MEDIAVIEWER_MEDIAFILE_URL)
        resp.raise_for_status()
        return resp.json()


class TvRunner:
    def __init__(self):
        self.paths = dict()
        self.errors = []

    def load_paths(self):
        self.paths = {
            key: val["pks"]
            for key, val in Tv.get_all_tv().items()
            if not val["finished"]
        }

    @staticmethod
    def get_or_create_media_path(local_path):
        log.info(f"Get or create MediaPath for {local_path}")
        media_path_data = Tv.post_media_path(local_path)
        return media_path_data['pk']

    @staticmethod
    def buildRemoteFileSetForPathIDs(pathIDs):
        fileSet = set()
        for pathid in pathIDs:
            # Skip local paths
            if pathid == -1:
                continue
            # TODO: Get MediaFiles for this MediaPath!
            # remoteFilenames = File.getTVFileSet(pathid)
            # fileSet.update(remoteFilenames)
        log.info("Built remote fileSet")

        return fileSet

    def updateFileRecords(self, path, localFileSet, remoteFileSet):
        media_path_id = None
        for localFile in localFileSet.difference(remoteFileSet):
            if not localFile:
                continue

            try:
                if not media_path_id:
                    media_path_id = self.get_or_create_media_path(path)

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
                except (AlreadyEncoded, SkipProcessing) as e:
                    log.warning(e)
                    continue

                if fullPath.exists():
                    MediaFile.post_media_file(
                        fullPath.name,
                        media_path_id,
                        fullPath.stat().st_size)
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
        command = f"find '{path}' -maxdepth 1 -size +{MINIMUM_FILE_SIZE}c -not -type d"
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

                dir_path = Path(top) / episode
                if dir_path.is_dir():
                    dir_set.add(dir_path)

                    english_subtitle_paths = dir_path.rglob("*Eng*.srt")
                    count = 0
                    for srt_path in english_subtitle_paths:
                        # Move subtitle to show directory and rename
                        log.info(f"Found subtitle file in {episode}")
                        new = Path(top) / f"{episode}-{count}.srt"
                        os.rename(srt_path, new)
                        count += 1

                    if (
                        file_ext in MEDIA_FILE_EXTENSIONS
                        and os.path.getsize(fullpath) > MINIMUM_FILE_SIZE
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
        self.load_paths()
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
