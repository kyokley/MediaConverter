import requests

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
    except Exception, e:
        log.error(e)
