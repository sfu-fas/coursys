import uuid

import amqp
import json


class MarkdownRpcClient(object):
    # Started here: https://www.rabbitmq.com/tutorials/tutorial-six-python.html
    # ... then adapted from pika to pyamqp since that is already here for Celery
    QUEUE_NAME = 'markdown2html_queue'

    def __init__(self):
        self.connection = amqp.connection.Connection(
            host='127.0.0.1',
            userid='coursys',
            password='the_rabbitmq_password',
            virtual_host='myvhost',
        )
        self.connection.connect()
        self.channel = amqp.channel.Channel(self.connection)
        self.channel.open()

        result = self.channel.queue_declare('', auto_delete=False, exclusive=True)
        self.callback_queue = result.queue
        self.response = None
        self.corr_id = None

        self.channel.basic_consume(queue=self.callback_queue, callback=self.on_response, no_ack=True)

    def __del__(self):
        self.connection.close()

    def on_response(self, message: amqp.Message):
        if self.corr_id == message.correlation_id:
            self.response = message.body

    def call(self, md):
        self.corr_id = str(uuid.uuid4())

        message = amqp.Message(body=md, correlation_id=self.corr_id, reply_to=self.callback_queue)
        self.channel.basic_publish(message, exchange='', routing_key=queue_name)
        self.connection.drain_events()
        return self.response


md = "## Hello\U0001F4A9\n\nworld\u2713."


def docker_method(n):
    markdown_rpc = MarkdownRpcClient()
    for i in range(n):
        arg = json.dumps({'md': md})
        response = markdown_rpc.call(arg.encode('utf-8'))
        html = json.loads(response.decode('utf-8'))['html']
    return html

import time
start = time.time()
print(docker_method(100))
end = time.time()
print(end - start)