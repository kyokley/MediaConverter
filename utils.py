import requests
import os

from unidecode import unidecode
import smtplib

from log import LogFile

from settings import (
    WAITER_USERNAME,
    WAITER_PASSWORD,
    GMAIL_USER,
    GMAIL_PASSWORD,
    EMAIL_RECIPIENTS,
    VERIFY_REQUESTS,
    MEDIA_FILE_EXTENSIONS,
    SUBTITLE_EXTENSIONS,
    MEDIAVIEWER_INFER_SCRAPERS_URL,
)

log = LogFile().getLogger()


class EncoderException(Exception):
    pass


class MissingPathException(Exception):
    pass


def postData(values, url):
    try:
        log.debug("Posting the following values:")
        log.debug(values)
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
        log.debug("successfully sent the mail")
    except:
        log.error("failed to send mail")


def file_ext(path):
    return os.path.splitext(path)[-1]


def is_valid_media_file(path):
    return os.path.exists(path) and file_ext(path).lower() in MEDIA_FILE_EXTENSIONS


def is_valid_subtitle_file(path):
    return os.path.exists(path) and file_ext(path).lower() in SUBTITLE_EXTENSIONS


def get_localpath_by_filename(filename):
    resp = requests.get(
        MEDIAVIEWER_INFER_SCRAPERS_URL,
        params={"title": filename},
        auth=(WAITER_USERNAME, WAITER_PASSWORD),
    )

    try:
        resp.raise_for_status()
    except:
        log.warning("Unable to find path for {}".format(filename))
        log.debug(resp.text)
        return

    data = resp.json()
    return data["localpath"]
