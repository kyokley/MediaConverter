import requests
from settings import (MEDIAVIEWER_FILE_URL,
                      MEDIAVIEWER_PATHFILES_URL,
                      MEDIAVIEWER_CERT,
                      WAITER_USERNAME,
                      WAITER_PASSWORD,
                      )
from utils import postData

class File(object):
    def __init__(self,
                 filename,
                 pathid,
                 size,
                 streamable):
        self.filename = filename
        self.pathid = pathid
        self.size = size
        self.streamable = streamable

    def post(self):
        values = {'pathid': self.pathid,
                  'filename': self.filename,
                  'skip': 1,
                  'size': self.size,
                  'finished': 1,
                  'streamable': self.streamable,
                  }
        postData(values, MEDIAVIEWER_FILE_URL)

    @classmethod
    def getFileSet(cls, pathid):
        fileSet = set()
        data = {'next': MEDIAVIEWER_PATHFILES_URL % pathid}
        while data['next']:
            r = requests.get(data['next'], verify=MEDIAVIEWER_CERT, auth=(WAITER_USERNAME, WAITER_PASSWORD))
            data = r.json()

            if data['results']:
                for result in data['results']:
                    fileSet.add(result['filename'])
        return fileSet
