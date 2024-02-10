import requests
import os
import time

from pathlib import Path
from unidecode import unidecode
import smtplib

import logging

from settings import (
    WAITER_USERNAME,
    WAITER_PASSWORD,
    GMAIL_USER,
    GMAIL_PASSWORD,
    EMAIL_RECIPIENTS,
    VERIFY_REQUESTS,
    MEDIA_FILE_EXTENSIONS,
    DOMAIN,
)

log = logging.getLogger(__name__)

MEDIAVIEWER_INFER_SCRAPERS_URL = f"{DOMAIN}/mediaviewer/api/inferscrapers/"

EXTERNAL_REQUEST_COOLDOWN = 0.25


class EncoderException(Exception):
    pass


class MissingPathException(Exception):
    pass


def post_data(values, url):
    try:
        request = _make_request('POST', url, values=values)

        try:
            requests.post(
                MEDIAVIEWER_INFER_SCRAPERS_URL,
                data={},
                auth=(WAITER_USERNAME, WAITER_PASSWORD),
                verify=VERIFY_REQUESTS,
            )
            time.sleep(EXTERNAL_REQUEST_COOLDOWN)
        except Exception as e:
            log.error(e)
            log.warning("Ignoring error generated during scraping")

        return request
    except Exception as e:
        log.error(e)
        raise


def get_data(url):
    try:
        return _make_request('GET', url)
    except Exception as e:
        log.error(e)
        raise


def _make_request(verb, url, values=None):
    verb = verb.upper()

    try:
        if values:
            log.info(f"{verb}-ing the following values to {url}:")
            log.info(values)
        else:
            log.info(f"{verb}-ing to {url}")

        request_method = None
        if verb == 'GET':
            request_method = requests.get
        elif verb == 'POST':
            request_method = requests.post
        else:
            raise ValueError(f'Got invalid verb {verb}')

        request = request_method(
            url,
            data=values,
            auth=(WAITER_USERNAME, WAITER_PASSWORD),
            verify=VERIFY_REQUESTS,
        )
        request.raise_for_status()
        time.sleep(EXTERNAL_REQUEST_COOLDOWN)

        return request
    except Exception as e:
        log.error(e)
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
    resp = requests.get(
        MEDIAVIEWER_INFER_SCRAPERS_URL,
        params={"title": filename},
        auth=(WAITER_USERNAME, WAITER_PASSWORD),
    )

    try:
        resp.raise_for_status()
    except Exception:
        log.warning(f"Unable to find path for {filename}")
        log.warning(resp.text)
        return

    data = resp.json()
    return data["localpath"]
