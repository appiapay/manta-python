from collections import namedtuple
from typing import Any, NamedTuple
from cryptography import x509
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives.asymmetric import padding
from cryptography.hazmat.primitives import hashes
from cryptography.exceptions import InvalidSignature

import paho.mqtt.client as mqtt
import json
import random
import re
import base64


class Conf(NamedTuple):
    url: str
    cert_file: str


CONF = Conf(
    url='127.0.0.1',
    cert_file='certificates/root/certs/www.brainblocks.com.crt'
)

Method = namedtuple('Method', ['name', 'args'])


def parse(topic):
    m = re.search("^\/rpc\/(\w+)\/reply(?:$|\/(.*))", topic)

    return (None if m is None else Method(
        name=m.group(1),
        args=None if len(m.groups()) == 1 else m.group(2).split('/')
    ))


def get_payment_request(client: mqtt.Client, txid):
    client.subscribe('/payment_requests/{}'.format(txid))


def load_certificate(filename):
    with open(filename, 'rb') as myfile:
        pem = myfile.read()
    return x509.load_pem_x509_certificate(pem, default_backend())


def verify_payment_request(payment_request):
    # Verify signature of message
    cert = load_certificate(CONF.cert_file)

    j_payment_request = json.loads(payment_request)
    signature = j_payment_request['signature']
    message = j_payment_request['message']

    try:
        cert.public_key().verify(
            base64.b64decode(signature),
            message.encode('utf-8'),
            padding.PSS(
                mgf=padding.MGF1(hashes.SHA256()),
                salt_length=padding.PSS.MAX_LENGTH
            ),
            hashes.SHA256()
        )
    except InvalidSignature:
        return None

    # Verify address signature
    j_message = json.loads(message)

    signature = j_message['address_sig']
    dest_address = j_message['dest_address']

    try:
        cert.public_key().verify(
            base64.b64decode(signature),
            dest_address.encode('utf-8'),
            padding.PSS(
                mgf=padding.MGF1(hashes.SHA256()),
                salt_length=padding.PSS.MAX_LENGTH
            ),
            hashes.SHA256()
        )
    except InvalidSignature:
        return None

    return j_message


def on_connect(client, userdata, flags, rc):
    print("Connected with result code " + str(rc))

    get_payment_request(client, userdata)


def handle_payment_request(client, msg):
    payment_request = verify_payment_request(msg)

    if payment_request is not None:
        if ask_confirmation(payment_request):
            tx_hash = send_money(10, 15)
            txid = payment_request['txid']
            client.publish('/payments/{}'.format(txid),
                           create_payment_message(tx_hash,
                                                  payment_request['address_sig'],
                                                  txid))
            client.subscribe('/acks/{}'.format(txid))


def print_ack(txid):
    print('Received confirmation for tx {}'.format(txid))


def on_message(client, userdata, msg):
    print("Got {} on {}".format(msg.payload, msg.topic))

    tokens = msg.topic.strip('/').split('/')

    if tokens[0] == 'payment_requests':
        handle_payment_request(client, msg.payload)

    if tokens[0] == 'acks':
        print_ack(tokens[1])


def create_payment_message(txhash, address_sig, txid):
    return json.dumps({
        'txhash': txhash,
        'address_sig': address_sig,
        'txid': txid,
    })


def ask_confirmation(payment_request):
    print("\n### PAYMENT REQUEST ###\n{}".format(json.dumps(payment_request, indent=4, sort_keys=True)))
    input("Do you confirm?")
    return True


def send_money(address, amount):
    return random.randint(0, 2 ** 32)


if __name__ == "__main__":
    # qr_code = input("Qr Code?")

    qr_code = 1234

    index = 0

    c = mqtt.Client(userdata=qr_code)

    c.on_connect = on_connect
    c.on_message = on_message

    c.connect(CONF.url)

    c.loop_forever()
