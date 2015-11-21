import requests, commands
from settings import (MOVIE_PATH_ID,
                      MEDIAVIEWER_MOVIE_URL,
                      LOCAL_MOVIE_PATH,
                      WAITER_USERNAME,
                      WAITER_PASSWORD,
                      )
from convert import reencodeFilesInDirectory
from utils import postData

from log import LogFile
log = LogFile().getLogger()

class MovieRunner(object):
    def __init__(self):
        self.movies = set()

    def loadMovies(self):
        self.movies = set()

        log.info("Loading movie paths")
        data = {'next': MEDIAVIEWER_MOVIE_URL}
        while data['next']:
            try:
                log.debug("Making API call with data: %s" % (data,))
                request = requests.get(data['next'], verify=False, auth=(WAITER_USERNAME, WAITER_PASSWORD))
                data = request.json()

                if data['results']:
                    for result in data['results']:
                        self.movies.add(result['filename'])
            except Exception, e:
                log.error("An error has occurred")
                log.error(e)
                raise

    def postMovies(self):
        res = commands.getoutput("ls '%s'" % (LOCAL_MOVIE_PATH,))
        tokens = res.split('\n')

        for token in tokens:
            if token not in self.movies:
                log.info("Found %s" % token)
                log.info("Starting re-encoding of %s..." % token)
                try:
                    reencodeFilesInDirectory(token)
                except Exception, e:
                    log.error("Error processing %s" % token)
                    log.error(e)
                    raise
                log.info("Posting %s" % (token,))
                self._postMovie(token)

    def run(self):
        self.loadMovies()
        self.postMovies()
        log.debug('Done running movies')

    def _postMovie(self, name):
        values = {'pathid': MOVIE_PATH_ID,
                  'filename': name,
                  'skip': 1,
                  'size': 0,
                  'finished': 1,
                  'streamable': True,
                  }
        postData(values, MEDIAVIEWER_MOVIE_URL)
