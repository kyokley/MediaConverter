import requests, os
from unidecode import unidecode

from log import LogFile
log = LogFile().getLogger()

from settings import (WAITER_USERNAME,
                      WAITER_PASSWORD,
                      )

class EncoderException(Exception):
    pass

class MissingPathException(Exception):
    pass

def postData(values, url):
    try:
        log.debug(values)
        request = requests.post(url, data=values, auth=(WAITER_USERNAME, WAITER_PASSWORD), verify=False)
        request.raise_for_status()
        return request
    except Exception, e:
        log.error(e)

def stripUnicode(filename, path=None):
    strippedFilename = unidecode(filename.decode('utf-8'))
    if strippedFilename != filename:
        if path:
            currentDir = os.getcwd()
            os.chdir(path)

        os.rename(filename, strippedFilename)

        if path:
            os.chdir(currentDir)

    if path:
        return os.path.join(path, strippedFilename)
    else:
        return strippedFilename
