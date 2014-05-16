# A Python logging handler that will dump long entries into AMQP where they are held until a
# consumer comes along to get them.

# adapted from http://notes.variogr.am/post/143623387/broadcasting-your-logs-with-rabbitmq-and-python

from django.conf import settings
import logging, pickle
from amqplib import client_0_8 as amqp
import kombu

my_exchange = ''
queue_name = 'log_messages'

def setup_amqp():
    assert settings.BROKER_URL.startswith('amqp://')
    conn = kombu.Connection(settings.BROKER_URL) # kombu.Connection.__init__ can parse the broker URL for us.
    ch = conn.channel()
    ch.queue_declare(queue=queue_name, durable=True, exclusive=False, auto_delete=False)
    return ch


class Producer():
    "Class to produce the logging AMQP messages"
    def __init__(self):
        self.ch = setup_amqp()

    def message(self, message):
        self.ch.basic_publish(msg=amqp.Message(pickle.dumps(message), delivery_mode=2), exchange=my_exchange, routing_key=queue_name)


class Consumer():
    "Class for the consumer of the AMQP messages"
    def __init__(self, callback_function=None):
        self.ch = setup_amqp()
        self.callback_function = callback_function

    def callback(self, msg):
        message = pickle.loads(msg.body)
        if(self.callback_function):
            self.callback_function(message)

    def consume_forever(self):
        self.ch.basic_consume(queue_name, callback=self.callback, no_ack=True)
        while self.ch.callbacks:
            self.ch.wait()

    def close(self):
        self.ch.close()


class AmqpLogHandler(logging.Handler):
    "Log handler that sends messages into AMQP."
    def __init__(self):
        super(AmqpLogHandler, self).__init__()
        self.broadcaster = Producer()

    def emit(self, record):
        # Send the log message to the queue
        message = {
            "message": self.format(record),
            "level": record.levelname,
            "pathname": record.pathname,
            "lineno": record.lineno,
            "exception": record.exc_info
        }
        self.broadcaster.message(message)
