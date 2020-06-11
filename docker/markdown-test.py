import pika
import uuid
import json


class MarkdownRpcClient(object):
    def __init__(self):
        self.connection = pika.BlockingConnection(
            pika.ConnectionParameters(
                host='127.0.0.1',
                virtual_host='myvhost',
                credentials=pika.credentials.PlainCredentials('coursys', 'supersecretpassword')
            )
        )

        self.channel = self.connection.channel()

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
            routing_key='markdown2html_queue',
            properties=pika.BasicProperties(
                reply_to=self.callback_queue,
                correlation_id=self.corr_id,
            ),
            body=md)
        while self.response is None:
            self.connection.process_data_events()
        return self.response


md = "## Hello\U0001F4A9\n\nworld\u2713."
arg = json.dumps({'md': md})
markdown_rpc = MarkdownRpcClient()
response = markdown_rpc.call(arg.encode('utf-8'))
html = json.loads(response.decode('utf-8'))['html']
print(html)
