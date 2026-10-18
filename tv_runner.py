import os
import json
import traceback
import subprocess  # nosec
import shlex
import shutil
import uuid
from urllib.parse import urlsplit

from pathlib import Path
import b2
from settings import (
    SEND_EMAIL,
    MEDIA_FILE_EXTENSIONS,
    UNSORTED_PATHS,
    MINIMUM_FILE_SIZE,
    DOMAIN,
    LOCAL_TV_SHOWS_PATHS,
    B2_ENABLED,
)
from convert import makeFileStreamable, SkipProcessing, AlreadyEncoded
from utils import (
    stripUnicode,
    EncoderException,
    MissingPathException,
    send_email,
    get_localpath_by_filename,
    get_media_path_by_filename,
    post_data,
    get_data,
    put_data,
    get_b2_uri_for_local_path,
    get_local_path_from_media_path,
    upload_subtitle_files,
    matching_subtitle_files,
)

import logging

log = logging.getLogger(__name__)

FIND_FAIL_STRING = b"No such file or directory"
IGNORED_FILE_EXTENSIONS = (".vtt", ".srt")


class MediaPathMixin:
    @classmethod
    @property
    def MEDIAVIEWER_MEDIAPATH_DETAIL_URL(cls):
        return cls.MEDIAVIEWER_MEDIAPATH_URL + "{media_path_id}/"

    @classmethod
    def post_media_path(
        cls, path, tv=None, movie=None, filename=None, subtitle_files=None
    ):
        payload = {
            "path": path,
            "tv": tv,
            "movie": movie,
            "filename": filename,
            "subtitle_files": json.dumps(subtitle_files or []),
        }
        resp = post_data(payload, cls.MEDIAVIEWER_MEDIAPATH_URL)
        return resp.json()

    @classmethod
    def get_media_path(cls, media_path_id):
        resp = get_data(
            cls.MEDIAVIEWER_MEDIAPATH_DETAIL_URL.format(media_path_id=media_path_id)
        )
        return resp.json()

    @classmethod
    def put_media_path(cls, media_path_id, skip=False):
        payload = {"skip": skip}
        resp = put_data(
            payload,
            cls.MEDIAVIEWER_MEDIAPATH_DETAIL_URL.format(media_path_id=media_path_id),
        )
        return resp.json()


class Tv(MediaPathMixin):
    @classmethod
    @property
    def MEDIAVIEWER_TV_URL(cls):
        return f"{DOMAIN}/mediaviewer/api/tv/"

    @classmethod
    @property
    def MEDIAVIEWER_TV_DETAIL_URL(cls):
        return cls.MEDIAVIEWER_TV_URL + "{tv_id}/"

    @classmethod
    def get_tv(cls, tv_id):
        resp = get_data(cls.MEDIAVIEWER_TV_DETAIL_URL.format(tv_id=tv_id))
        return resp.json()

    @classmethod
    def put_tv(cls, tv_id, finished=False):
        payload = {"finished": finished}
        resp = put_data(payload, cls.MEDIAVIEWER_TV_DETAIL_URL.format(tv_id=tv_id))
        return resp.json()

    @classmethod
    @property
    def MEDIAVIEWER_MEDIAPATH_URL(cls):
        return DOMAIN + "/mediaviewer/api/tvmediapath/"

    @classmethod
    def get_all_tv(cls):
        paths = dict()

        data = {"next": cls.MEDIAVIEWER_TV_URL}
        while data["next"]:
            request = get_data(data["next"])
            data = request.json()

            if data["results"]:
                for result in data["results"]:
                    media_paths = result["media_paths"]

                    for media_path in media_paths:
                        local_path = get_local_path_from_media_path(
                            media_path["path"], LOCAL_TV_SHOWS_PATHS
                        )

                        val = paths.setdefault(
                            local_path, {"pks": set(), "finished": result["finished"]}
                        )
                        val["pks"].add(media_path["pk"])
                        paths[local_path] = val
        return paths

    @classmethod
    def get_all_media_paths(cls):
        media_paths = []
        data = {"next": cls.MEDIAVIEWER_MEDIAPATH_URL}
        while data["next"]:
            response = get_data(data["next"])
            data = response.json()
            media_paths.extend(data["results"])
        return media_paths


class MediaFile:
    @classmethod
    @property
    def MEDIAVIEWER_MEDIAFILE_URL(cls):
        return f"{DOMAIN}/mediaviewer/api/mediafile/"

    @classmethod
    def get_all_filenames(cls):
        filenames = set()
        visited = set()
        for endpoint in (
            f"{DOMAIN}/mediaviewer/api/tvmediapath/",
            f"{DOMAIN}/mediaviewer/api/moviemediapath/",
        ):
            url = endpoint
            while url:
                if url in visited:
                    raise ValueError(f"Cyclic MediaPath pagination: {url}")
                visited.add(url)
                response = get_data(url)
                if hasattr(response, "raise_for_status"):
                    response.raise_for_status()
                data = response.json()
                if (
                    not isinstance(data, dict)
                    or "next" not in data
                    or not isinstance(data.get("results"), list)
                ):
                    raise ValueError(f"Malformed MediaPath response from {url}")
                next_url = data.get("next")
                if next_url is not None and not isinstance(next_url, str):
                    raise ValueError(f"Malformed pagination link from {url}")
                for path in data["results"]:
                    if not isinstance(path, dict):
                        raise ValueError(f"Malformed MediaPath record from {url}")
                    media_files = path.get("media_files")
                    if not isinstance(media_files, list) or any(
                        not isinstance(name, str) for name in media_files
                    ):
                        raise ValueError(f"Malformed media_files in {url}")
                    filenames.update(media_files)
                    filename = path.get("filename")
                    if filename is not None and not isinstance(filename, str):
                        raise ValueError(f"Malformed filename in {url}")
                    if filename:
                        filenames.add(filename)
                url = next_url
        return filenames

    @classmethod
    def post_media_file(
        cls,
        filename,
        media_path_id,
        size,
        subtitle_files=None,
        b2_uuid=None,
    ):
        payload = {
            "filename": filename,
            "media_path": media_path_id,
            "size": size,
            "subtitle_files": json.dumps(subtitle_files or []),
        }
        if b2_uuid is not None:
            payload["b2_uuid"] = b2_uuid
        resp = post_data(payload, cls.MEDIAVIEWER_MEDIAFILE_URL)
        resp.raise_for_status()
        return resp.json()


class TvRunner:
    def __init__(self):
        self.paths = dict()
        self.errors = []
        self._published_filenames = None

    def _get_published_filenames(self):
        if self._published_filenames is None:
            self._published_filenames = MediaFile.get_all_filenames()
        return self._published_filenames

    def load_paths(self):
        tv_entries = Tv.get_all_tv()
        self.paths = {
            key: val["pks"] for key, val in tv_entries.items() if not val["finished"]
        }

        for path_str in LOCAL_TV_SHOWS_PATHS:
            path = Path(path_str)
            if not path.exists():
                log.warning(f"Local TV path {path} does not exist")
                continue
            for dir in path.iterdir():
                if "unsorted" in str(dir).lower() or (
                    dir in tv_entries and tv_entries[dir]["finished"]
                ):
                    continue
                self.paths.setdefault(dir, set()).add(-1)

    @staticmethod
    def get_or_create_media_path(local_path):
        log.info(f"Get or create MediaPath for {local_path}")
        if B2_ENABLED:
            media_path = get_b2_uri_for_local_path(local_path)
        else:
            media_path = local_path
        media_path_data = Tv.post_media_path(media_path)
        return {
            "pk": media_path_data["pk"],
            "skip": media_path_data["skip"],
            "bucket": media_path_data.get("bucket"),
            "b2_upload_prefix": media_path_data.get("b2_upload_prefix"),
        }

    @staticmethod
    def build_remote_media_file_set(pathIDs):
        return {
            filename
            for detail in TvRunner.fetch_remote_media_path_details(pathIDs)
            for filename in detail["media_files"]
        }

    @staticmethod
    def fetch_remote_media_path_details(pathIDs):
        details = []
        for pathid in pathIDs:
            # Skip local paths
            if pathid == -1:
                continue
            detail = Tv.get_media_path(pathid)
            detail.setdefault("pk", pathid)
            details.append(detail)
        return details

    @staticmethod
    def _select_b2_destination(path, media_path_details):
        destinations = {}
        for detail in media_path_details or []:
            uri = detail.get("path", "")
            if uri.startswith("b2://"):
                destinations.setdefault(uri, []).append(detail)
        if not destinations:
            return None
        if len(destinations) > 1:
            configured_uri = get_b2_uri_for_local_path(Path(path))
            if configured_uri not in destinations:
                raise ValueError(
                    f"Ambiguous B2 media paths for {path}: {sorted(destinations)}"
                )
            uri = configured_uri
        else:
            uri = next(iter(destinations))
        detail = min(destinations[uri], key=lambda item: item["pk"])
        parsed = urlsplit(uri)
        if (
            parsed.scheme != "b2"
            or not parsed.netloc
            or parsed.query
            or parsed.fragment
        ):
            raise ValueError(f"Invalid B2 media path: {uri}")
        return {
            "pk": detail["pk"],
            "skip": detail.get("skip", False),
            "bucket": detail.get("bucket"),
            "b2_upload_prefix": detail.get("b2_upload_prefix"),
        }

    def updateFileRecords(
        self, path, localFileSet, remoteFileSet, dry_run=False, media_path_details=None
    ):
        destination = (
            self._select_b2_destination(path, media_path_details)
            if B2_ENABLED
            else None
        )
        media_path_id = None
        for localFile in localFileSet.difference(remoteFileSet):
            if not localFile:
                continue

            published_filenames = None
            if B2_ENABLED and not dry_run:
                published_filenames = self._get_published_filenames()
                if localFile in published_filenames:
                    log.info(f"Skipping {localFile}; filename already published")
                    continue

            if dry_run:
                log.debug(f"Would process {localFile}")
                continue

            if not media_path_id:
                media_path_data = destination or self.get_or_create_media_path(
                    Path(path) if B2_ENABLED else path
                )
                if B2_ENABLED:
                    destination = media_path_data
                if media_path_data["skip"]:
                    break

                media_path_id = media_path_data["pk"]

            try:
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
                except AlreadyEncoded as e:
                    log.warning(e)
                    if not fullPath.exists() or fullPath.suffix.lower() != ".mp4":
                        continue
                except SkipProcessing as e:
                    log.warning(e)
                    continue

                if fullPath.exists():
                    if fullPath.name in remoteFileSet or (
                        published_filenames is not None
                        and fullPath.name in published_filenames
                    ):
                        log.info(
                            f"Skipping {fullPath.name}; filename already published"
                        )
                        continue
                    subtitle_files = []
                    if B2_ENABLED:
                        bucket = destination["bucket"]
                        key_prefix = destination["b2_upload_prefix"]
                        if not key_prefix:
                            raise ValueError(
                                "MediaPath response missing b2_upload_prefix"
                            )
                        if not bucket:
                            raise ValueError("MediaPath response missing bucket")
                        b2_uuid = str(uuid.uuid4())
                        key = f"{key_prefix}{b2_uuid}{fullPath.suffix}"
                        b2.get_b2_client().upload_file(fullPath, bucket, key)
                        subtitle_files = upload_subtitle_files(
                            fullPath, path, bucket=bucket, key_prefix=key_prefix
                        )
                    media_file_kwargs = {"subtitle_files": subtitle_files}
                    if B2_ENABLED:
                        media_file_kwargs["b2_uuid"] = b2_uuid
                    MediaFile.post_media_file(
                        fullPath.name,
                        media_path_id,
                        fullPath.stat().st_size,
                        **media_file_kwargs,
                    )
                    if published_filenames is not None:
                        published_filenames.add(fullPath.name)
                    remoteFileSet.add(fullPath.name)
                    if media_path_details:
                        selected_detail = next(
                            (
                                detail
                                for detail in media_path_details
                                if detail.get("pk") == media_path_id
                            ),
                            None,
                        )
                        if selected_detail is not None:
                            media_files = selected_detail.setdefault("media_files", [])
                            if fullPath.name not in media_files:
                                media_files.append(fullPath.name)
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

    def handleDirs(self, path, dry_run=False):
        if path.exists():
            for directory in sorted((p for p in path.iterdir() if p.is_dir())):
                videos = sorted(
                    p
                    for p in directory.rglob("*")
                    if p.is_file()
                    and p.suffix.lower() in MEDIA_FILE_EXTENSIONS
                    and p.stat().st_size > MINIMUM_FILE_SIZE
                )
                generic_names = {
                    "2_eng",
                    "2_english",
                    "english",
                    "eng",
                    "subtitle",
                }
                # Resolve every owner against the unchanged directory inventory.
                plans = []
                for video in videos:
                    sidecars = matching_subtitle_files(video, video_inventory=videos)
                    if len(videos) == 1:
                        sidecars.extend(
                            subtitle
                            for subtitle in directory.rglob("*")
                            if subtitle.is_file()
                            and subtitle.suffix.lower() in (".srt", ".vtt")
                            and subtitle.stem.casefold() in generic_names
                            and subtitle not in sidecars
                        )
                    moves = [(video, path / video.name)]
                    for sidecar in sidecars:
                        name = sidecar.name
                        if sidecar.stem.casefold() in generic_names:
                            name = f"{video.stem}.{sidecar.name}"
                        moves.append((sidecar, path / name))
                    plans.append(moves)

                for moves in plans:
                    sources = {source for source, _ in moves}
                    targets = [target for _, target in moves]
                    collision = len(set(targets)) != len(targets) or any(
                        target.exists() and target not in sources for target in targets
                    )
                    if collision:
                        log.warning(
                            "Skipping directory move batch due to destination collision"
                        )
                        continue
                    for source, target in moves:
                        if dry_run:
                            log.debug(f"Would rename {source} to {target}")
                        else:
                            shutil.move(str(source), str(target))
                if not dry_run:
                    for nested in sorted(directory.rglob("*"), reverse=True):
                        if nested.is_dir():
                            try:
                                nested.rmdir()
                            except OSError:
                                pass
                    try:
                        directory.rmdir()
                    except OSError:
                        pass

    def run(self, dry_run=False):
        self._published_filenames = None
        if B2_ENABLED and not dry_run:
            self._get_published_filenames()
        log.info("Attempting to sort unsorted files")
        self._sort_unsorted_files(dry_run=dry_run)

        log.info("Attempting to get paths")
        self.load_paths()
        log.info("Got paths")
        for path, pathIDs in self.paths.items():
            try:
                log.info(f"Handling directories in {path}")
                self.handleDirs(path, dry_run=dry_run)
                log.info(f"Building local file set for {path}")
                localFileSet = self.buildLocalFileSet(path)
                log.info(f"Done building local file set for {path}")
            except MissingPathException as e:
                log.warning(e)
                log.warning("Continuing...")
                continue

            log.info(f"Attempting to get remote files for {path}")
            media_path_details = self.fetch_remote_media_path_details(pathIDs)
            remoteFileSet = {
                filename
                for detail in media_path_details
                for filename in detail["media_files"]
            }
            log.info(f"Done building remote file set for {path}")

            self.updateFileRecords(
                path,
                localFileSet,
                remoteFileSet,
                dry_run=dry_run,
                media_path_details=media_path_details,
            )

        if self.errors:
            log.error("Errors occured in the following files:")
            for error in self.errors:
                log.error(error)
        log.info("Done running tv shows")
        return self.errors

    @staticmethod
    def _normalized_media_path(uri):
        return uri[:-1] if uri.endswith("/") else uri

    def _sort_unsorted_files(self, dry_run=False):
        media_paths = None
        details_by_uri = {}
        for unsorted_path_str in UNSORTED_PATHS:
            unsorted_path = Path(unsorted_path_str)

            if not unsorted_path.exists():
                log.info(f"Unsorted file path {unsorted_path} does not exist")
                continue

            for src in list(unsorted_path.iterdir()):
                if B2_ENABLED:
                    if (
                        not src.is_file()
                        or src.suffix.lower() not in MEDIA_FILE_EXTENSIONS
                        or src.stat().st_size <= MINIMUM_FILE_SIZE
                    ):
                        continue
                    inferred_uri = get_media_path_by_filename(src.name)
                    if not inferred_uri:
                        log.warning(f"No media path inferred for {src.name}")
                        continue
                    if not inferred_uri.startswith("b2://"):
                        inferred_uri = get_b2_uri_for_local_path(Path(inferred_uri))
                    try:
                        self._select_b2_destination(
                            src.parent,
                            [{"pk": 0, "path": inferred_uri, "skip": False}],
                        )
                    except ValueError as error:
                        log.warning(f"Invalid inferred B2 path for {src.name}: {error}")
                        continue

                    normalized_uri = self._normalized_media_path(inferred_uri)
                    if normalized_uri not in details_by_uri:
                        if media_paths is None:
                            media_paths = Tv.get_all_media_paths()
                        matching_paths = [
                            item
                            for item in media_paths
                            if item.get("path", "").startswith("b2://")
                            and self._normalized_media_path(item["path"])
                            == normalized_uri
                        ]
                        if matching_paths:
                            listed_path = min(
                                matching_paths, key=lambda item: item["pk"]
                            )
                            detail = Tv.get_media_path(listed_path["pk"])
                            detail.setdefault("pk", listed_path["pk"])
                            detail.setdefault("path", listed_path["path"])
                        elif dry_run:
                            log.info(
                                f"Would create media path {inferred_uri} for {src.name}"
                            )
                            continue
                        else:
                            detail = Tv.post_media_path(inferred_uri)
                            detail.setdefault("path", inferred_uri)
                            detail.setdefault("media_files", [])
                        details_by_uri[normalized_uri] = detail

                    detail = details_by_uri[normalized_uri]
                    remote_files = set(detail.get("media_files", []))
                    self.updateFileRecords(
                        src.parent,
                        {src.name},
                        remote_files,
                        dry_run=dry_run,
                        media_path_details=[detail],
                    )
                    continue

                filename = src.name

                localpath = get_localpath_by_filename(filename)
                if not localpath or not localpath.exists():
                    continue

                dst = localpath / filename

                if dry_run:
                    log.info(f"Would move {src} to {dst}")
                else:
                    log.info(f"Moving {src} to {dst}")
                    shutil.move(src, dst)


if __name__ == "__main__":
    runner = TvRunner()
    errors = runner.run()
    if errors:
        print(errors)
