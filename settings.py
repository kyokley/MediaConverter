import logging

logging.getLogger().setLevel(level=logging.DEBUG)
logging.getLogger("faker").setLevel(logging.WARN)

CELERY_VHOST = ""

WAITER_USERNAME = "waiter"
WAITER_PASSWORD = "password"

LOCAL_MOVIE_PATHS = ["movies"]
LOCAL_TV_SHOWS_PATHS = ["tv_shows"]
UNSORTED_PATHS = ["unsorted"]
BASE_PATH = "/home/user"

DOMAIN = "https://127.0.0.1:8001"  # Do not include trailing slash

MEDIAVIEWER_SUFFIX = "mv-encoded.mp4"

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

SERVER_NAME = "127.0.0.1"

SEND_EMAIL = False
GMAIL_USER = "some@user.com"
GMAIL_PASSWORD = "some_password"
EMAIL_RECIPIENTS = ["another@user.com"]

VERIFY_REQUESTS = True

MINIMUM_FILE_SIZE = 10000000

# DON'T MAKE ANY EDITS BELOW THIS LINE!!!!
try:
    from local_settings import *  # noqa
except:  # nosec # noqa
    pass
