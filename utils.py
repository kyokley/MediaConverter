import logging
import os
import uuid
import smtplib
import time
from pathlib import Path
from urllib.parse import urlsplit, urlunsplit

import requests
from unidecode import unidecode

import b2
from settings import (
    B2_BUCKET_NAME,
    B2_NAME_PREFIX,
    BASE_PATH,
    DOMAIN,
    EMAIL_RECIPIENTS,
    GMAIL_PASSWORD,
    GMAIL_USER,
    MEDIA_FILE_EXTENSIONS,
    MEDIAVIEWER_SUFFIX,
    TIMEOUT,
    VERIFY_REQUESTS,
    WAITER_PASSWORD,
    WAITER_USERNAME,
)

log = logging.getLogger(__name__)

EXTERNAL_REQUEST_COOLDOWN = 0.25


class EncoderException(Exception):
    pass


class MissingPathException(Exception):
    pass


def mediaviewer_infer_scrapers_url():
    return f"{DOMAIN}/mediaviewer/api/inferscrapers/"


def _external_request_cooldown():
    return EXTERNAL_REQUEST_COOLDOWN


def _sanitized_endpoint(url):
    """Return scheme, host, and path without URL credentials or parameters."""
    try:
        parsed = urlsplit(url)
        host = parsed.hostname
        if host is None:
            return parsed.path or "<invalid-endpoint>"
        if ":" in host:
            host = f"[{host}]"
        if parsed.port is not None:
            host = f"{host}:{parsed.port}"
        return urlunsplit((parsed.scheme, host, parsed.path, "", ""))
    except (TypeError, ValueError):
        return "<invalid-endpoint>"


def _response_status(exception):
    response = getattr(exception, "response", None)
    return getattr(response, "status_code", None)


def post_data(values, url):
    request = _make_request("POST", url, values=values)

    infer_url = mediaviewer_infer_scrapers_url()
    endpoint = _sanitized_endpoint(infer_url)
    started = time.perf_counter()
    log.debug("API request started: POST %s", endpoint)
    try:
        infer_response = requests.post(
            infer_url,
            data={},
            auth=(WAITER_USERNAME, WAITER_PASSWORD),
            verify=VERIFY_REQUESTS,
            timeout=TIMEOUT,
        )
        log.debug(
            "API request completed: POST %s status=%s elapsed=%.3fs",
            endpoint,
            getattr(infer_response, "status_code", "unknown"),
            time.perf_counter() - started,
        )
        time.sleep(_external_request_cooldown())
    except Exception as exc:
        log.warning(
            "API request failed: POST %s status=%s elapsed=%.3fs",
            endpoint,
            _response_status(exc) or "unavailable",
            time.perf_counter() - started,
        )
        log.warning("Ignoring error generated during scraping")

    return request


def get_data(url):
    return _make_request("GET", url)


def put_data(values, url):
    return _make_request("PUT", url, values=values)


def _make_request(verb, url, values=None):
    verb = verb.upper()
    endpoint = _sanitized_endpoint(url)
    started = time.perf_counter()
    log.debug("API request started: %s %s", verb, endpoint)
    try:
        request_method = None
        if verb == "GET":
            request_method = requests.get
        elif verb == "POST":
            request_method = requests.post
        elif verb == "PUT":
            request_method = requests.put
        else:
            raise ValueError(f"Got invalid verb {verb}")

        request = request_method(
            url,
            data=values,
            auth=(WAITER_USERNAME, WAITER_PASSWORD),
            verify=VERIFY_REQUESTS,
            timeout=TIMEOUT,
        )
        status = request.status_code
        request.raise_for_status()
        time.sleep(_external_request_cooldown())
        log.debug(
            "API request completed: %s %s status=%s elapsed=%.3fs",
            verb,
            endpoint,
            status,
            time.perf_counter() - started,
        )
        return request
    except Exception as exc:
        status = _response_status(exc)
        log.warning(
            "API request failed: %s %s status=%s elapsed=%.3fs",
            verb,
            endpoint,
            status if status is not None else "unavailable",
            time.perf_counter() - started,
        )
        raise


def stripUnicode(filename, path=None):
    if isinstance(filename, bytes):
        filename = filename.decode("utf-8")

    file_path = Path(filename)

    stripped_filename = unidecode(file_path.name).replace("'", "")
    stripped_path = file_path.parent / stripped_filename

    if stripped_path != file_path:
        if path:
            current_dir = Path(os.getcwd())
            os.chdir(path)

        os.rename(filename, stripped_filename)

        if path:
            os.chdir(current_dir)

    if path:
        return Path(path) / stripped_filename
    else:
        return stripped_path


def send_email(subject, body):
    log.info("sending error email")
    message = (
        f"From: {GMAIL_USER}\n"
        f"To: {', '.join(EMAIL_RECIPIENTS)}\n"
        f"Subject: {subject}\n\n{body}\n"
    )
    try:
        server = smtplib.SMTP("smtp.gmail.com", 587)
        server.ehlo()
        server.starttls()
        server.login(GMAIL_USER, GMAIL_PASSWORD)
        server.sendmail(GMAIL_USER, EMAIL_RECIPIENTS, message)
        server.close()
        log.info("successfully sent the mail")
    except Exception:
        log.error("failed to send mail")


def is_valid_media_file(path):
    if isinstance(path, bytes):
        path = path.decode("utf-8")
    path = Path(path)
    return path.suffix.lower() in MEDIA_FILE_EXTENSIONS


def get_localpath_by_filename(filename):
    media_path = get_media_path_by_filename(filename)
    return Path(media_path) if media_path else None


def get_media_path_by_filename(filename):
    """Return the inferred MediaViewer media path without converting its type."""
    endpoint = _sanitized_endpoint(mediaviewer_infer_scrapers_url())
    started = time.perf_counter()
    log.debug("API request started: GET %s", endpoint)
    try:
        resp = requests.get(
            mediaviewer_infer_scrapers_url(),
            params={"title": filename},
            auth=(WAITER_USERNAME, WAITER_PASSWORD),
            timeout=TIMEOUT,
        )
    except Exception as exc:
        log.warning(
            "API request failed: GET %s type=%s elapsed=%.3fs",
            endpoint,
            type(exc).__name__,
            time.perf_counter() - started,
        )
        raise

    try:
        resp.raise_for_status()
    except Exception as exc:
        status = getattr(resp, "status_code", None)
        log.warning(
            "Unable to find path for %s: GET %s status=%s elapsed=%.3fs",
            filename,
            endpoint,
            status if status is not None else (_response_status(exc) or "unavailable"),
            time.perf_counter() - started,
        )
        return

    log.debug(
        "API request completed: GET %s status=%s elapsed=%.3fs",
        endpoint,
        getattr(resp, "status_code", "unknown"),
        time.perf_counter() - started,
    )

    data = resp.json()
    return data["path"]


def get_b2_uri_for_local_path(local_path):
    """Build the b2:// URI MediaViewer should store for a local directory."""
    return f"b2://{B2_BUCKET_NAME}/{B2_NAME_PREFIX}{local_path.name}/"


def upload_subtitle_files(video_path, media_path, bucket=None, key_prefix=None):
    """Upload .vtt subtitle files matching the video to B2.

    Returns the list of uploaded subtitle file names.
    """
    subtitle_files = []
    bucket = bucket or B2_BUCKET_NAME
    if key_prefix is None:
        key_prefix = f"{B2_NAME_PREFIX}{Path(media_path).name}/"
    subtitle_files_to_upload = matching_subtitle_files(video_path)
    total = len(subtitle_files_to_upload)
    video_path = Path(video_path)
    destination = f"b2://{bucket}/{key_prefix}"
    log.info(
        "Found %d subtitle file(s) for %s to upload to %s",
        total,
        video_path,
        destination,
    )
    for index, subtitle_file in enumerate(subtitle_files_to_upload, start=1):
        if subtitle_file.suffix.lower() == ".srt":
            from convert import _convertSrtToVtt

            subtitle_file = _convertSrtToVtt(subtitle_file)
        remote_name = f"{uuid.uuid4()}.vtt"
        key = f"{key_prefix}{remote_name}"
        log.info(
            "Uploading subtitle [%d/%d] %s for %s to %s",
            index,
            total,
            subtitle_file,
            video_path,
            destination,
        )
        b2.get_b2_client().upload_file(subtitle_file, bucket, key)
        subtitle_files.append(remote_name)
    log.info(
        "Uploaded %d subtitle file(s) for %s to %s",
        len(subtitle_files),
        video_path,
        destination,
    )
    return subtitle_files


def matching_subtitle_files(video_path, video_inventory=None):
    """Return deterministically matched adjacent SRT/VTT sidecars."""
    video = Path(video_path)
    base = video.name
    suffix = f".{MEDIAVIEWER_SUFFIX}"
    if base.lower().endswith(suffix.lower()):
        base = base[: -len(suffix)]
    if Path(base).suffix.lower() in MEDIA_FILE_EXTENSIONS:
        base = base[: -len(Path(base).suffix)]
    bases = {base.casefold(), video.stem.casefold()}
    inventory = (
        [Path(item) for item in video_inventory]
        if video_inventory is not None
        else [
            path
            for path in video.parent.iterdir()
            if path.is_file() and path.suffix.lower() in MEDIA_FILE_EXTENSIONS
        ]
    )
    if video not in inventory:
        inventory.append(video)
    candidates = sorted(
        (
            p
            for p in video.parent.iterdir()
            if p.is_file() and p.suffix.lower() in (".srt", ".vtt")
        ),
        key=lambda p: p.name.casefold(),
    )
    matches = {}
    for path in candidates:
        stem = path.stem.casefold()
        matched_bases = [
            owner
            for owner in bases
            if (
                stem.startswith(owner)
                and (
                    not stem[len(owner) :]
                    or stem[len(owner) : len(owner) + 1] in (".", "-")
                )
            )
        ]
        if matched_bases:
            longest_match = max(map(len, matched_bases))
            claimed_by_more_specific_video = False
            for other in inventory:
                if other.resolve() == video.resolve():
                    continue
                other_name = other.name
                if other_name.lower().endswith(suffix.lower()):
                    other_name = other_name[: -len(suffix)]
                if Path(other_name).suffix.lower() in MEDIA_FILE_EXTENSIONS:
                    other_name = other_name[: -len(Path(other_name).suffix)]
                other_base = other_name.casefold()
                if (
                    len(other_base) > longest_match
                    and stem.startswith(other_base)
                    and (
                        not stem[len(other_base) :]
                        or stem[len(other_base) : len(other_base) + 1] in (".", "-")
                    )
                ):
                    claimed_by_more_specific_video = True
                    break
            if claimed_by_more_specific_video:
                continue
            if stem not in matches or path.suffix.lower() == ".vtt":
                matches[stem] = path

    generic = {"2_eng", "2_english", "english", "eng", "subtitle"}
    media_count = (
        len(inventory)
        if video_inventory is not None
        else sum(
            1
            for p in video.parent.iterdir()
            if p.is_file() and p.suffix.lower() in MEDIA_FILE_EXTENSIONS
        )
    )
    if media_count <= 1:
        for path in candidates:
            if path.stem.casefold() in generic:
                if path.stem.casefold() not in matches or path.suffix.lower() == ".vtt":
                    matches[path.stem.casefold()] = path
    return sorted(set(matches.values()), key=lambda p: p.name.casefold())


def get_local_path_from_media_path(media_path, local_roots):
    """Map a MediaViewer media_path value back to a local filesystem path.

    Handles local paths (absolute, or relative to BASE_PATH) and b2:// URIs.
    B2 URIs are matched back to a local directory by name under one of the
    given local roots; the first root whose candidate exists wins, falling
    back to the first root.
    """
    if media_path.startswith("b2://"):
        dirname = media_path.rstrip("/").rsplit("/", 1)[-1]
        for root in local_roots:
            candidate = Path(BASE_PATH) / root / dirname
            if candidate.exists():
                return candidate
        return Path(BASE_PATH) / local_roots[0] / dirname
    if BASE_PATH not in media_path:
        return Path(BASE_PATH) / media_path
    return Path(media_path)
