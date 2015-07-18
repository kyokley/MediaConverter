import requests, os
from unidecode import unidecode

from log import LogFile
log = LogFile().getLogger()

from settings import (WAITER_USERNAME,
                      WAITER_PASSWORD,
                      )

def postData(values, url):
    try:
        log.debug(values)
        request = requests.post(url, data=values, auth=(WAITER_USERNAME, WAITER_PASSWORD), verify=False)
        request.raise_for_status()
        return request
    except Exception, e:
        log.error(e)

def stripUnicode(path, filename):
    strippedFilename = unidecode(filename)
    if strippedFilename != filename:
        currentDir = os.getcwd()
        os.chdir(path)
        os.rename(filename, strippedFilename)
        os.chdir(currentDir)
    return os.path.join(path, strippedFilename)
