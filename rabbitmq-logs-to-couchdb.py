import json

import pika
from pika import BasicProperties
from pika.channel import Channel
from pika.spec import Basic


def callback(channel: Channel, method_frame: Basic.Deliver, properties: BasicProperties, body: bytes):
    data = json.loads(body)
    msg = data['msg']
    print(msg)
    channel.basic_ack(delivery_tag=method_frame.delivery_tag)


credentials = pika.PlainCredentials('coursys', 'rabbitmq_password')
connection = pika.BlockingConnection(pika.ConnectionParameters('localhost', 5672, 'myvhost', credentials))
channel = connection.channel()

binding_key = 'django-logging.*'
result = channel.queue_declare('tester1', durable=True, exclusive=False, auto_delete=False)
queue_name = result.method.queue

channel.queue_bind(exchange='log', queue=queue_name, routing_key=binding_key)

channel.basic_consume(queue=queue_name, on_message_callback=callback, auto_ack=False)

channel.start_consuming()
