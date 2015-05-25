import os

CWD = os.getcwd()
LOG_DIR = os.path.join(CWD, 'logs')
try:
    os.makedirs(LOG_DIR)
except OSError:
    pass
LOG_FILE_NAME = os.path.join(LOG_DIR, 'converterLog')

MOVIE_PATH_ID = 57

WAITER_USERNAME = 'user'
WAITER_PASSWORD = 'password'

LOCAL_MOVIE_PATH = 'movies'
LOCAL_TV_SHOWS_PATH = 'tv_shows'

#MEDIAVIEWER_MOVIE_URL = 'https://127.0.0.1:8001/mediaviewer/api/movie/'
#
#MEDIAVIEWER_PATH_URL = 'https://127.0.0.1:8001/mediaviewer/api/path/'
#MEDIAVIEWER_FILE_URL = 'https://127.0.0.1:8001/mediaviewer/api/file/'
#MEDIAVIEWER_UNSTREAMABLE_FILE_URL = 'https://127.0.0.1:8001/mediaviewer/api/unstreamablefile/'
#MEDIAVIEWER_PATHFILES_URL = 'https://127.0.0.1:8001/mediaviewer/api/file/?pathid=%s'

MEDIAVIEWER_CERT = 'mediaviewer.ca_bundle'

#MEDIAVIEWER_SUFFIX = '%s.mv-encoded.mp4'

ENCODER = 'avconv' # or 'ffmpeg'

MEDIA_FILE_EXTENSIONS = ('.mp4',
                         '.avi',
                         '.mpeg',
                         '.mkv',
                         )

#SERVER_NAME = '127.0.0.1'

# DON'T MAKE ANY EDITS BELOW THIS LINE!!!!
try:
    from local_settings import *
except:
    pass
