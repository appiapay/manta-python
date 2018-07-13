from typing import Any, NamedTuple

from pycoin.key import Key
from collections import namedtuple
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives.serialization import load_pem_private_key
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import padding

import paho.mqtt.client as mqtt
import json
import re
import base64


class Conf(NamedTuple):
    url: str
    nano_address: str
    key_file: str


CONF = Conf(
    url='127.0.0.1',
    nano_address='xrb_1234',
    key_file='certificates/root/keys/www.brainblocks.com.key'
)

DB = {
    'device1': {
        'name': 'Nano Coffee Shop',
        'address': 'Milano',
    }
}

PAYMENT_REQUESTS = {}
TXID = 0


def parse(topic):
    m = re.search("^\/rpc\/(\w+)\/request(?:$|\/(.*))", topic)

    return (None if m is None else {
        'method': m.group(1),
        'args': None if len(m.groups()) == 1 else m.group(2).split('/')
    })


def load_key():
    with open(CONF.key_file, 'rb') as myfile:
        key_data = myfile.read()
    return key_data


def key_from_keydata(key_data):
    return load_pem_private_key(key_data, password=None, backend=default_backend())


def sign(message, key):
    signature = key.sign(message,
                         padding.PSS(
                             mgf=padding.MGF1(hashes.SHA256()),
                             salt_length=padding.PSS.MAX_LENGTH
                         ),
                         hashes.SHA256())
    return base64.b64encode(signature)


def generate_payment_request(device, amount, txid):

    key = key_from_keydata(load_key())
    merchant = DB[device]

    message = {
        'name': merchant['name'],
        'address': merchant['address'],
        'amount': amount,
        'dest_address': CONF.nano_address,
    }

    json_message = json.dumps(message)
    signature = sign(json_message.encode('utf-8'), key).decode('utf-8')

    payment_request = {
        'message': json_message,
        'signature': signature,
    }

    return json.dumps(payment_request)


def on_connect(client, userdata, flags, rc):
    print("Connected with result code " + str(rc))

    client.subscribe('/generate_payment_request/#')
    client.subscribe('/payments/#')


def check_key(key, path):
    kd = Key.from_text(CONF['masterkey']).subkey_for_path(path)

    print('Got key:{} and path:{}. Derivation:{}'.format(key, path, kd.wallet_key()))

    return kd.wallet_key() == key


# Check confirmation on blockchain
def check_blockchain(txhash):
    return True


def on_message(client: mqtt.Client, userdata, msg):
    global TXID

    print("Got {} on {}".format(msg.payload, msg.topic))

    #parsed = parse(msg.topic)

    tokens = msg.topic.strip('/').split('/')

    if tokens[0] == 'generate_payment_request':
        device = tokens[1]
        p = json.loads(msg.payload)

        if p['crypto_currency'] == 'nanoray':
            PAYMENT_REQUESTS[p['session_id']] = generate_payment_request(device, p['amount'], p['session_id'])
            print(PAYMENT_REQUESTS[p['session_id']])
            client.publish('/payment_requests/{}'.format(p['session_id']), PAYMENT_REQUESTS[p['session_id']], retain=True)
            client.subscribe('/payments/{}'.format(p['session_id']))
            #generate_payment_request reply
            topic = '/generate_payment_request/{}/reply'.format(device)
            message = {'status': 200,
                       'session_id': p['session_id']}
            client.publish(topic, json.dumps(message))
        else:
            topic = '/generate_payment_request/{}/reply'.format(device)
            message = {'status': 200,
                       'session_id': p['session_id'],
                       'crypto_currency:': p['crypto_currency'],
                       'address': '1BvBMSEYstWetqTFn5Au4m4GFg7xJaNVN2'}
            client.publish(topic, json.dumps(message))

    if tokens[0] == 'payments':
        payment_message = json.loads(msg.payload)
        if check_blockchain(payment_message['txhash']):
            client.publish('/acks/{}'.format(tokens[1]), json.dumps({'txid': TXID}))
            TXID = TXID + 1


if __name__ == "__main__":
    c = mqtt.Client()

    c.on_connect = on_connect
    c.on_message = on_message

    c.connect(CONF.url)

    c.loop_forever()
