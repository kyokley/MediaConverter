import requests
import os

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
    SUBTITLE_EXTENSIONS,
    DOMAIN,
)

log = logging.getLogger(__name__)

MEDIAVIEWER_INFER_SCRAPERS_URL = f"{DOMAIN}/mediaviewer/api/inferscrapers/"


class EncoderException(Exception):
    pass


class MissingPathException(Exception):
    pass


def postData(values, url):
    try:
        log.info("Posting the following values:")
        log.info(values)
        request = requests.post(
            url,
            data=values,
            auth=(WAITER_USERNAME, WAITER_PASSWORD),
            verify=VERIFY_REQUESTS,
        )
        request.raise_for_status()
        return request
    except Exception as e:
        log.error(e)
        raise


def stripUnicode(filename, path=None):
    if isinstance(filename, bytes):
        filename = filename.decode("utf-8")

    strippedFilename = unidecode(filename).replace("'", "")
    if strippedFilename != filename:
        if path:
            currentDir = os.getcwd()
            os.chdir(path)

        os.rename(filename, strippedFilename)

        if path:
            os.chdir(currentDir)

    if path:
        return os.path.join(path, strippedFilename)
    else:
        return strippedFilename


def send_email(subject, body):
    log.info("sending error email")
    message = """From: %s\nTo: %s\nSubject: %s\n\n%s
    """ % (
        GMAIL_USER,
        ", ".join(EMAIL_RECIPIENTS),
        subject,
        body,
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


def file_ext(path):
    return os.path.splitext(path)[-1]


def is_valid_media_file(path):
    if isinstance(path, bytes):
        path = path.decode("utf-8")

    return os.path.exists(path) and file_ext(path).lower() in MEDIA_FILE_EXTENSIONS


def is_valid_subtitle_file(path):
    if isinstance(path, bytes):
        path = path.decode("utf-8")

    return os.path.exists(path) and file_ext(path).lower() in SUBTITLE_EXTENSIONS


def get_localpath_by_filename(filename):
    resp = requests.get(
        MEDIAVIEWER_INFER_SCRAPERS_URL,
        params={"title": filename},
        auth=(WAITER_USERNAME, WAITER_PASSWORD),
    )

    try:
        resp.raise_for_status()
    except Exception:
        log.warning("Unable to find path for {}".format(filename))
        log.warning(resp.text)
        return

    data = resp.json()
    return data["localpath"]
