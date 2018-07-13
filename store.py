from typing import Any, NamedTuple

import random
import paho.mqtt.client as mqtt
import json
import logging


class Conf(NamedTuple):
    url: str
    deviceID: str


CONF = Conf(
    url='127.0.0.1',
    deviceID='device1'
)

logging.basicConfig(level=logging.INFO)

def generate_qr(data):
    logging.info("QR Code:{}".format(data))


def generate_session_id():
    return 1234
    #return random.randint(0, 2 ** 32)


def get_generate_payment_request(txid, amount, fiat_currency="euro", crypto_currency="nanoray"):
    topic = '/generate_payment_request/{deviceID}/request'.format(deviceID=CONF.deviceID)
    payload = json.dumps({'amount': amount,
                          'session_id': txid,
                          'fiat_currency': fiat_currency,
                          'crypto_currency': crypto_currency,
                          })
    return (topic, payload)


def on_connect(client, userdata, flags, rc):
    logging.info("Connected with result code " + str(rc))
    client.subscribe('/acks/{}'.format(userdata['session_id']))
    client.subscribe('/generate_payment_request/{deviceID}/reply'.format(deviceID=CONF.deviceID))

    (topic, payload) = get_generate_payment_request(userdata['session_id'], userdata['amount'])
    client.publish (topic, payload)


def on_message(client: mqtt.Client, userdata, msg):
    logging.info("Got {} on {}".format(msg.payload, msg.topic))

    #parsed = parse(msg.topic)

    tokens = msg.topic.strip('/').split('/')

    if tokens[0] == 'acks':
        print_ack(tokens[1])
        client.disconnect()
    elif tokens[0] == 'generate_payment_request':
        if userdata['crypto_currency'] == 'nanoray':
            generate_qr("manta://{}/{}".format(CONF.url, userdata['session_id']))
        else: #Legacy format
            message = json.loads(msg.payload)
            generate_qr("bitcoin:{}?amount={}".format(message['address'], userdata['amount']))


def print_ack(txid):
    logging.info('Received confirmation for tx {}'.format(txid))


if __name__ == "__main__":

    session_id = generate_session_id()
    amount = 100

    logging.info('session_id:{}'.format(session_id))

    userdata = {
        'session_id': session_id,
        'amount': amount,
        'crypto_currency': 'nanoray',
        'fiat_currency': 'euro'
    }

    c = mqtt.Client(userdata=userdata)

    c.on_connect = on_connect
    c.on_message = on_message

    c.connect(CONF.url)

    c.loop_forever()



