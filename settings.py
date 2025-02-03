import os
import logging

logging.getLogger().setLevel(level=logging.DEBUG)
logging.getLogger("faker").setLevel(logging.WARN)

CELERY_VHOST = ""

WAITER_USERNAME = os.getenv("MC_WAITER_USERNAME", "waiter")
WAITER_PASSWORD = os.getenv("MC_WAITER_PASSWORD", "password")

LOCAL_MOVIE_PATHS = (
    os.getenv("MC_LOCAL_MOVIE_PATHS").split(",")
    if os.getenv("MC_LOCAL_MOVIE_PATHS")
    else ["movies"]
)
LOCAL_TV_SHOWS_PATHS = (
    os.getenv("MC_LOCAL_TV_SHOWS_PATHS").split(",")
    if os.getenv("MC_LOCAL_TV_SHOWS_PATHS")
    else ["tv_shows"]
)
UNSORTED_PATHS = (
    os.getenv("MC_UNSORTED_PATHS").split(",")
    if os.getenv("MC_UNSORTED_PATHS")
    else ["unsorted"]
)
BASE_PATH = os.getenv("MC_BASE_PATH", "/home/user")

DOMAIN = os.getenv(
    "MC_DOMAIN", "https://127.0.0.1:8001"
)  # Do not include trailing slash

MEDIAVIEWER_SUFFIX = os.getenv("MC_MEDIAVIEWER_SUFFIX", "mv-encoded.mp4")

ENCODER = "ffmpeg"  # or 'avconv'

MEDIA_FILE_EXTENSIONS = (
    ".mp4",
    ".avi",
    ".mpeg",
    ".mkv",
    ".m4v",
    ".mpg",
)

SUBTITLE_EXTENSIONS = (".srt",)
SUBTITLE_FILES = ("2_Eng.srt", "English.srt", "2_English.srt")

SERVER_NAME = os.getenv("MC_SERVER_NAME", "127.0.0.1")

SEND_EMAIL = os.getenv("MC_SEND_EMAIL", False)
GMAIL_USER = os.getenv("MC_GMAIL_USER", "some@user.com")
GMAIL_PASSWORD = os.getenv("MC_GMAIL_PASSWORD", "some_password")
EMAIL_RECIPIENTS = (
    os.getenv("MC_EMAIL_RECIPIENTS").split(",")
    if os.getenv("MC_EMAIL_RECIPIENTS")
    else ["another@user.com"]
)

VERIFY_REQUESTS = True

MINIMUM_FILE_SIZE = int(os.getenv("MC_MINIMUM_FILE_SIZE", 10000000))

# DON'T MAKE ANY EDITS BELOW THIS LINE!!!!
try:
    from local_settings import *  # noqa
except:  # nosec # noqa
    pass
