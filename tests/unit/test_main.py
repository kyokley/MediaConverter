from celery.events import EventReceiver

from main import app


def test_control_mailbox_queues_are_exclusive_and_nondurable():
    mailbox = app.control.mailbox

    command_queue = mailbox.get_queue("test-worker")
    reply_queue = mailbox.get_reply_queue()

    for queue in (command_queue, reply_queue):
        assert queue.exclusive is True
        assert queue.durable is False


def test_event_receiver_queue_is_exclusive_and_nondurable():
    event_queue = EventReceiver(channel=None, app=app).queue

    assert event_queue.exclusive is True
    assert event_queue.durable is False
