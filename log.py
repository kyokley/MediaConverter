import logging
from logging.handlers import RotatingFileHandler
from logging import StreamHandler
from settings import LOG_FILE_NAME


class LogFile(object):
    logger = None

    _instance = None

    def __new__(cls, *args, **kwargs):
        if not cls._instance:
            cls._instance = super(LogFile, cls).__new__(cls, *args, **kwargs)
        return cls._instance

    @classmethod
    def getLogger(cls):
        if not cls.logger:
            formatter = logging.Formatter(
                "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
            )
            log = logging.getLogger("waiter")
            log.setLevel(logging.DEBUG)
            rfh = RotatingFileHandler(
                LOG_FILE_NAME,
                mode="a",
                maxBytes=1000000,
                backupCount=5,
            )
            rfh.setFormatter(formatter)
            log.addHandler(rfh)

            sth = StreamHandler()
            sth.setFormatter(formatter)
            log.addHandler(sth)
            cls.logger = log

        return cls.logger
