import os

CWD = os.getcwd()
LOG_DIR = os.path.join(CWD, 'logs')
try:
    os.makedirs(LOG_DIR)
except OSError:
    pass
LOG_FILE_NAME = os.path.join(LOG_DIR, 'converterLog')

CELERY_VHOST = '/'

WAITER_USERNAME = 'user'
WAITER_PASSWORD = 'password'

LOCAL_MOVIE_PATHS = ['movies']
LOCAL_TV_SHOWS_PATHS = ['tv_shows']

MEDIAVIEWER_MOVIE_PATH_URL = 'https://127.0.0.1:8001/mediaviewer/api/moviepath/'
MEDIAVIEWER_TV_PATH_URL = 'https://127.0.0.1:8001/mediaviewer/api/tvpath/'

MEDIAVIEWER_MOVIE_FILE_URL = 'https://127.0.0.1:8001/mediaviewer/api/movie/'
MEDIAVIEWER_TV_FILE_URL = 'https://127.0.0.1:8001/mediaviewer/api/tv/'

MEDIAVIEWER_TV_PATHFILES_URL = 'https://127.0.0.1:8001/mediaviewer/api/tv/?pathid=%s'
MEDIAVIEWER_MOVIE_PATHFILES_URL = 'https://127.0.0.1:8001/mediaviewer/api/movie/?pathid=%s'

MEDIAVIEWER_UNSTREAMABLE_FILE_URL = 'https://127.0.0.1:8001/mediaviewer/api/unstreamablefile/'
MEDIAVIEWER_INFER_SCRAPERS_URL = 'https://127.0.0.1:8001/mediaviewer/api/inferscrapers/'

MEDIAVIEWER_SUFFIX = '%s.mv-encoded.mp4'

ENCODER = 'avconv' # or 'ffmpeg'

MEDIA_FILE_EXTENSIONS = ('.mp4',
                         '.avi',
                         '.mpeg',
                         '.mkv',
                         )

SERVER_NAME = '127.0.0.1'

SEND_EMAIL = False
GMAIL_USER = 'some@user.com'
GMAIL_PASSWORD = 'some_password'
EMAIL_RECIPIENTS = ['another@user.com']

ALEXA_AUTH = 'secret'

VERIFY_REQUESTS = True

# DON'T MAKE ANY EDITS BELOW THIS LINE!!!!
try:
    from local_settings import *
except:
    pass
