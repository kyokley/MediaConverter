import logging

logging.getLogger().setLevel(level=logging.DEBUG)

CELERY_VHOST = ""

WAITER_USERNAME = "user"
WAITER_PASSWORD = "password"

LOCAL_MOVIE_PATHS = ["movies"]
LOCAL_TV_SHOWS_PATHS = ["tv_shows"]
UNSORTED_PATHS = ["unsorted"]
BASE_PATH = "/home/user"

DOMAIN = 'https://127.0.0.1:8001'  # Do not include trailing slash

MEDIAVIEWER_MOVIE_PATH_URL = f"{DOMAIN}/mediaviewer/api/moviepath/"
MEDIAVIEWER_TV_PATH_URL = f"{DOMAIN}/mediaviewer/api/tvpath/"

MEDIAVIEWER_MOVIE_FILE_URL = f"{DOMAIN}/mediaviewer/api/movie/"
MEDIAVIEWER_TV_FILE_URL = f"{DOMAIN}/mediaviewer/api/tv/"

MEDIAVIEWER_TV_PATHFILES_URL = f"{DOMAIN}/mediaviewer/api/tv/?pathid=%s"
MEDIAVIEWER_MOVIE_PATHFILES_URL = (
    f"{DOMAIN}/mediaviewer/api/movie/?pathid=%s"
)

MEDIAVIEWER_UNSTREAMABLE_FILE_URL = (
    f"{DOMAIN}/mediaviewer/api/unstreamablefile/"
)
MEDIAVIEWER_INFER_SCRAPERS_URL = f"{DOMAIN}/mediaviewer/api/inferscrapers/"

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

# DON'T MAKE ANY EDITS BELOW THIS LINE!!!!
try:
    from local_settings import *
except:  # nosec
    pass
