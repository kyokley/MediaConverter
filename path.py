import requests, commands, os
from settings import (LOCAL_TV_SHOWS_PATH,
                      SERVER_NAME,
                      MEDIAVIEWER_PATH_URL,
                      WAITER_USERNAME,
                      WAITER_PASSWORD,
                      )
from utils import postData

class Path(object):
    def __init__(self,
                 localpath,
                 remotepath):
        self.localpath = localpath
        self.remotepath = remotepath

    def post(self):
        values = {'localpath': self.localpath,
                  'remotepath': self.remotepath,
                  'skip': False,
                  'server': SERVER_NAME,
                  }
        postData(values, MEDIAVIEWER_PATH_URL)

    @classmethod
    def getPaths(cls):
        pathDict = dict()
        data = {'next': MEDIAVIEWER_PATH_URL}
        while data['next']:
            request = requests.get(data['next'], verify=False, auth=(WAITER_USERNAME, WAITER_PASSWORD))
            data = request.json()

            if data['results']:
                for result in data['results']:
                    pathDict.setdefault(result['localpath'], set()).add(result['pk'])
        return pathDict

    @classmethod
    def getLocalPaths(cls):
        res = commands.getoutput("ls '%s'" % LOCAL_TV_SHOWS_PATH)
        res = res.split('\n')
        res = set([os.path.join(LOCAL_TV_SHOWS_PATH, path) for path in res])
        return res

    @classmethod
    def getAllPaths(cls):
        ''' Returns a dict of localpaths related to pathids
            Local paths not in the server are represented with pathid -1.
        '''
        allPaths = cls.getPaths()
        localPaths = cls.getLocalPaths()

        for path in localPaths:
            allPaths.setdefault(path, set()).add(-1)
        return allPaths

    @classmethod
    def getPathByLocalPathAndRemotePath(cls,
                                        localpath,
                                        remotepath,
                                        ):
        payload = {'localpath': localpath, 'remotepath': remotepath}
        request = requests.get(MEDIAVIEWER_PATH_URL,
                               params=payload,
                               verify=False,
                               auth=(WAITER_USERNAME, WAITER_PASSWORD),
                               )
        data = request.json()
        return data

