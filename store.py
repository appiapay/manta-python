from typing import Any, NamedTuple

import random
import paho.mqtt.client as mqtt
import json


class Conf(NamedTuple):
    pp: str
    url: str
    deviceID: str

CONF = Conf(
    pp=1,
    url='127.0.0.1',
    deviceID='device1'
)


def generate_qr(txid):
    return {
        'pp': CONF.pp,
        'txid': txid
    }


def generate_txid():
    return 1234
    #return random.randint(0, 2 ** 32)


def ask_generate_payment_request(client, txid, amount):
    client.publish('/generate_payment_request/{deviceID}'.format(deviceID=CONF.deviceID),
                   json.dumps({'amount': amount, 'txid': txid}))


def on_connect(client, userdata, flags, rc):
    print("Connected with result code " + str(rc))
    client.subscribe('/acks/{}'.format(userdata[0]))
    ask_generate_payment_request(client, userdata[0], userdata[1])


def on_message(client: mqtt.Client, userdata, msg):
    print("Got {} on {}".format(msg.payload, msg.topic))

    #parsed = parse(msg.topic)

    tokens = msg.topic.strip('/').split('/')

    if tokens[0] == 'acks':
        print_ack(tokens[1])
        client.disconnect()


def print_ack(txid):
    print('Received confirmation for tx {}'.format(txid))


if __name__ == "__main__":

    txid = generate_txid()
    amount = 100
    generate_qr(txid)

    print('TXID:{}'.format(txid))

    c = mqtt.Client(userdata=(txid, amount))

    c.on_connect = on_connect
    c.on_message = on_message

    c.connect(CONF.url)

    c.loop_forever()



