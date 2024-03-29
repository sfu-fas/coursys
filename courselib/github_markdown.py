"""
Code handling the Github-flavoured markdown to HTML conversion.

The library to do this is Ruby-only, so there's some complexity. Three methods are implemented here:
 1. RPC using RabbitMQ to a docker container. The container is defined in the ruby-markup directory of this repo
    and managed by docker-compose. The HTML is ultimately generated by markdown2html-server.rb.
 2. starting a Ruby subprocess (markdown2html.rb) and capturing its output.
 3. the Python markdown library (attempted only if not in production)

#1 is faster than #2 by 10 times or more, which is why it's used primarily.

#2 is used as a fallback, since it was implemented before #1, and may be available in case of other failures.

#3 is incorrect, but good enough for development if nothing else is available.
"""

import json
import os
import socket
import subprocess
import uuid

import amqp
import markdown
from django.conf import settings


TIMEOUT = 5  # all IO operations time out in this many seconds
markdown_client = None


class MarkdownRpcClient(object):
    # Started here: https://www.rabbitmq.com/tutorials/tutorial-six-python.html
    # ... then adapted from pika to pyamqp since that is already here for Celery
    QUEUE_NAME = 'markdown2html_queue'

    def __init__(self):
        self.connection = amqp.connection.Connection(
            host=settings.RABBITMQ_HOSTPORT,
            userid=settings.RABBITMQ_USER,
            password=settings.RABBITMQ_PASSWORD,
            virtual_host=settings.RABBITMQ_VHOST,
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

    def call(self, args):
        self.corr_id = str(uuid.uuid1())
        message = amqp.Message(body=args, correlation_id=self.corr_id, reply_to=self.callback_queue, expiration=str(TIMEOUT*10*1000))
        self.channel.basic_publish(message, exchange='', routing_key=MarkdownRpcClient.QUEUE_NAME, timeout=TIMEOUT)
        self.connection.drain_events(timeout=TIMEOUT)
        return self.response


def markdown_to_html_subprocess(markup, fallback=True):
    """
    Convert github markdown to HTML, by starting a subprocess.
    """
    try:
        sub = subprocess.Popen([os.path.join(settings.BASE_DIR, 'ruby-markup', 'markdown2html.rb')], stdin=subprocess.PIPE,
                               stdout=subprocess.PIPE)
        stdoutdata, stderrdata = sub.communicate(input=markup.encode('utf8'), timeout=TIMEOUT)
        ret = sub.wait()
    except OSError:
        ret = -1

    if ret != 0:
        if fallback and settings.DEPLOY_MODE != 'production':
            # ultimate fallback: Python markdown module
            return markdown.markdown(markup)
        else:
            raise RuntimeError('markdown2html.rb did not return successfully')

    return stdoutdata.decode('utf8')


def markdown_to_html_rpc(markup, retry=True, fallback=True):
    """
    Convert github markdown to HTML, by RPC over rabbitmq
    """
    # keep a single instance of MarkdownRpcClient, to minimize connection cost
    global markdown_client
    if not markdown_client:
        markdown_client = MarkdownRpcClient()

    try:
        arg = json.dumps({'md': markup})
        response = markdown_client.call(arg.encode('utf-8'))
        if not response and fallback:
            return markdown_to_html_subprocess(markup)
        html = json.loads(response.decode('utf-8'))['html']
        return html
    except (amqp.AMQPError, socket.timeout):
        if retry:
            # retry once, in case of rabbitmq restart, etc
            markdown_client = None
            return markdown_to_html_rpc(markup, retry=False, fallback=fallback)
        elif fallback:
            # then fall back to the slower subprocess method
            return markdown_to_html_subprocess(markup)
        else:
            # fallback=False used by the deployment checks to ensure the path we want
            raise


if settings.USE_CELERY:
    # assume that if celery is enabled, we have rabbitmq and docker for the RPC
    markdown_to_html = markdown_to_html_rpc
else:
    markdown_to_html = markdown_to_html_subprocess
