# curl -X PUT http://admin:password@127.0.0.1:5984/logs
import base64
import json
import iso8601
import pika
from pika import BasicProperties
from pika.channel import Channel
from pika.spec import Basic
import uuid
from urllib import request, parse


couch_db_url = 'http://localhost:5984/logs/'
couch_db_user = 'admin'
couch_db_pass = 'password'
auth_str = b'Basic ' + base64.b64encode(('%s:%s' % (couch_db_user, couch_db_pass)).encode('ascii'))


def callback(channel: Channel, method_frame: Basic.Deliver, properties: BasicProperties, body: bytes):
    data = json.loads(body)
    msg = data['msg']
    datetime = iso8601.parse_date(msg['timestamp'])
    msg['datetime'] = msg['timestamp']
    msg['timestamp'] = datetime.timestamp()
    print(msg)

    uu = uuid.uuid1()
    url = parse.urljoin(couch_db_url, uu.hex)
    data_bytes = bytes(json.dumps(msg), encoding='utf8')
    req = request.Request(url=url, method='PUT', data=data_bytes, headers={'Authorization': auth_str, 'Content-Type': 'application/json'})
    resp = request.urlopen(req)

    if resp.status == 201:
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
