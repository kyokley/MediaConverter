import commands, requests
from datetime import datetime
from settings import (MOVIE_PATH_ID,
                      WAITER_USERNAME,
                      WAITER_PASSWORD,
                      LOCAL_MOVIE_PATH,
                      MEDIAVIEWER_MOVIE_URL,
                      )
from convert import reencodeFilesInDirectory

from log import LogFile
log = LogFile().getLogger()

class Client(object):
    def __init__(self):
        log.debug("Initializing Client Obj")
        self.movies = set()

    def loadMovies(self):
        log.info("Loading movie paths")
        data = {'next': MEDIAVIEWER_MOVIE_URL}
        while data['next']:
            try:
                log.debug("Making API call with data: %s" % (data,))
                request = requests.get(data['next'])
                data = request.json()

                if data['results']:
                    for result in data['results']:
                        self.movies.add(result['filename'])
            except Exception, e:
                log.error("An error has occurred")
                log.error(e)

    def postMovies(self):
        res = commands.getoutput("ls '%s'" % (LOCAL_MOVIE_PATH,))
        tokens = res.split('\n')

        for token in tokens:
            if token not in self.movies:
                print "Found %s" % token
                print "Attempting to re-encode media files"
                log.info("Found %s. Starting re-encoding..." % token)
                try:
                    reencodeFilesInDirectory(token)
                except Exception, e:
                    print "Error processing %s" % token
                    log.error("Error processing %s" % token)
                    log.error(e)
                print "Posting %s" % (token,)
                log.info("Posting %s" % (token,))
                self.post(token)

    def post(self, name):
        values = {'pathid': MOVIE_PATH_ID,
                  'filename': name,
                  'skip': 1,
                  'size': 0,
                  'finished': 1,
                  'streamable': True,
                  }
        log.debug(values)

        try:
            requests.post(MEDIAVIEWER_MOVIE_URL, data=values, auth=(WAITER_USERNAME, WAITER_PASSWORD))
        except Exception, e:
            print e
            log.error(e)

def run():
    log.info("Starting %s" % (datetime.now(),))
    client = Client()
    client.loadMovies()
    client.postMovies()
    print "Done"
    log.info("Done")

if __name__ == '__main__':
    run()
