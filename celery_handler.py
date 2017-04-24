from settings import (CELERY_VHOST,
                      CELERY_VHOST_IP,
                      )

from celery import Celery
app = Celery('tasks',
             broker='amqp://guest@{vhost_ip}/{vhost}'.format(vhost=CELERY_VHOST,
                                                             vhost_ip=CELERY_VHOST_IP))

