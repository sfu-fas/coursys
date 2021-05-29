import multiprocessing

import pika
import uuid
import json
queue_name = 'markdown2html_queue'


class MarkdownRpcClient(object):
    def __init__(self):
        self.connection = pika.BlockingConnection(
            pika.ConnectionParameters(
                host='127.0.0.1',
                virtual_host='myvhost',
                credentials=pika.credentials.PlainCredentials('coursys', 'the_rabbitmq_password')
            )
        )

        self.channel = self.connection.channel()
        self.response = None
        self.corr_id = None

        result = self.channel.queue_declare(queue='', exclusive=True)
        self.callback_queue = result.method.queue

        self.channel.basic_consume(
            queue=self.callback_queue,
            on_message_callback=self.on_response,
            auto_ack=True)

    def __del__(self):
        self.connection.close()

    def on_response(self, ch, method, props, body):
        if self.corr_id == props.correlation_id:
            self.response = body

    def call(self, md):
        self.response = None
        self.corr_id = str(uuid.uuid4())
        self.channel.basic_publish(
            exchange='',
            routing_key=queue_name,
            properties=pika.BasicProperties(
                reply_to=self.callback_queue,
                correlation_id=self.corr_id,
            ),
            body=md)
        while self.response is None:
            self.connection.process_data_events()
        return self.response


md = "## Hello\U0001F4A9\n\nworld\u2713."


def docker_method(n):
    markdown_rpc = MarkdownRpcClient()
    for i in range(n):
        arg = json.dumps({'md': md})
        response = markdown_rpc.call(arg.encode('utf-8'))
        html = json.loads(response.decode('utf-8'))['html']
    return html


import subprocess, os
def markdown_to_html(markup):
    sub = subprocess.Popen([os.path.join('courselib', 'markdown2html.rb')], stdin=subprocess.PIPE,
                           stdout=subprocess.PIPE)
    stdoutdata, stderrdata = sub.communicate(input=markup.encode('utf8'))
    ret = sub.wait()
    if ret != 0:
        raise RuntimeError('markdown2html.rb did not return successfully')
    return stdoutdata.decode('utf8')


def local_method(n):
    for i in range(n):
        html = markdown_to_html(md)
    return html


def concurrent_1(i):
    markdown_rpc = MarkdownRpcClient()
    arg = json.dumps({'md': md})
    response = markdown_rpc.call(arg.encode('utf-8'))
    html = json.loads(response.decode('utf-8'))['html']
    return html


def concurrent_method(n):
    # let's make sure concurrent requests happen okay too
    with multiprocessing.Pool(12) as pool:
        res = pool.map(concurrent_1, range(n))
    return res[0]


import time
start = time.time()
print(docker_method(100))
end = time.time()
print(end - start)

# Approximate timings with n=100:
# local_method: 9.5s
# docker_method: 0.1s
# docker_method (with MarkdownRpcClient in the loop): 0.9s
