import requests, os
from unidecode import unidecode
import smtplib

from log import LogFile
log = LogFile().getLogger()

from settings import (WAITER_USERNAME,
                      WAITER_PASSWORD,
                      GMAIL_USER,
                      GMAIL_PASSWORD,
                      EMAIL_RECIPIENTS,
                      VERIFY_REQUESTS,
                      )

class EncoderException(Exception):
    pass

class MissingPathException(Exception):
    pass

def postData(values, url):
    try:
        log.debug(values)
        request = requests.post(url, data=values, auth=(WAITER_USERNAME, WAITER_PASSWORD), verify=VERIFY_REQUESTS)
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

def send_email(subject, body):
    # Prepare actual message
    message = """\From: %s\nTo: %s\nSubject: %s\n\n%s
    """ % (GMAIL_USER, ", ".join(EMAIL_RECIPIENTS), subject, body)
    try:
        server = smtplib.SMTP("smtp.gmail.com", 587)
        server.ehlo()
        server.starttls()
        server.login(GMAIL_USER, GMAIL_PASSWORD)
        server.sendmail(GMAIL_USER, EMAIL_RECIPIENTS, message)
        server.close()
        print 'successfully sent the mail'
    except:
        print "failed to send mail"
