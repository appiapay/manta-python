from __future__ import annotations

from typing import Any, NamedTuple, TYPE_CHECKING, Callable, List, Dict



from collections import namedtuple
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives.serialization import load_pem_private_key
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import padding
#from cryptography.hazmat.primitives.asymmetric.rsa import RSAPrivateKey

import logging
import paho.mqtt.client as mqtt
import simplejson as json
import re
import base64

if TYPE_CHECKING:
    from cryptography.hazmat.primitives.asymmetric.rsa import RSAPrivateKey

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)


class Conf(NamedTuple):
    url: str
    nano_address: str
    key_file: str
    nano_euro: float


class Destination(NamedTuple):
    amount: float
    destination_address: str
    crypto_currency: str


class PaymentRequestMessage(NamedTuple):
    merchant: str
    amount: float
    fiat_currency: str
    destinations: list[Destination]

    @classmethod
    def from_json(cls, json_str:str):
        dict = json.loads(json_str)
        destinations = [Destination(**x) for x in dict['destinations']]
        dict['destinations'] = destinations
        return cls(**dict)


class PaymentRequestEnvelope(NamedTuple):
    message: str
    signature: str

    def unpack(self):
        pr = PaymentRequestMessage.from_json(self.message)
        return pr


class POSPaymentRequestMessage(NamedTuple):
    amount: float
    session_id: str
    fiat_currency: str
    crypto_currency: str


logging.basicConfig(level=logging.INFO)


def isnamedtupleinstance(x):
    _type = type(x)
    bases = _type.__bases__
    if len(bases) != 1 or bases[0] != tuple:
        return False
    fields = getattr(_type, '_fields', None)
    if not isinstance(fields, tuple):
        return False
    return all(type(i)==str for i in fields)


def unpack(obj):
    if isinstance(obj, dict):
        return {key: unpack(value) for key, value in obj.items()}
    elif isinstance(obj, list):
        return [unpack(value) for value in obj]
    elif isnamedtupleinstance(obj):
        return {key: unpack(value) for key, value in obj._asdict().items()}
    elif isinstance(obj, tuple):
        return tuple(unpack(value) for value in obj)
    else:
        return obj


class PayProc:
    mqtt_client: mqtt_client.Client
    key: RSAPrivateKey
    get_merchant: Callable[[str], str]
    #device: str, amount: float, fiat_currency: str
    #get_destinations: Callable[[str, float, ], List[Destination]]
    #get_destinations: (device: str, amount: float, fiat_currency: str) -> List [Destination]
    payment_requests: Dict[str, PaymentRequestMessage] = {}
    txid: int = 0

    def __init__(self, key_file: str):
        self.mqtt_client = mqtt.Client()
        self.mqtt_client.on_connect = PayProc.on_connect
        self.mqtt_client.on_message = self.on_message

        with open(key_file, 'rb') as myfile:
            key_data = myfile.read()

        self.key = PayProc.key_from_keydata(key_data)
        self.get_destinations = None

    def run(self):
        self.mqtt_client.connect(host='localhost')
        self.mqtt_client.loop_start()

    @staticmethod
    def key_from_keydata(key_data: bytes) -> RSAPrivateKey:
        return load_pem_private_key(key_data, password=None, backend=default_backend())

    def sign(self, message: bytes) -> bytes:
        # signature = key.sign(message,
        #                      padding.PSS(
        #                          mgf=padding.MGF1(hashes.SHA256()),
        #                          salt_length=padding.PSS.MAX_LENGTH
        #                      ),
        #                      hashes.SHA256())

        signature = self.key.sign(message, padding.PKCS1v15(), hashes.SHA256())

        return base64.b64encode(signature)

    @staticmethod
    def on_connect(client, userdata, flags, rc):
        logger.info("Connected with result code " + str(rc))

        client.subscribe('/generate_payment_request/+/request')
        client.subscribe('/payments/#')

    def on_message(self, client: mqtt.Client, userdata, msg):
        global TXID

        logger.info("Got {} on {}".format(msg.payload, msg.topic))

        tokens = msg.topic.strip('/').split('/')

        if tokens[0] == 'generate_payment_request':
            device = tokens[1]
            p = POSPaymentRequestMessage(**json.loads(msg.payload))

            if p.crypto_currency == 'nanoray':
                envelope = self.generate_payment_request(device, p)
                self.payment_requests[p.session_id] = envelope.unpack()
                logger.info(envelope)
                client.publish('/payment_requests/{}'.format(p.session_id), json.dumps(envelope),
                               retain=True)
                client.subscribe('/payments/{}'.format(p.session_id))
                # generate_payment_request reply
                topic = '/generate_payment_request/{}/reply'.format(device)
                message = {'status': 200,
                           'session_id': p.session_id}
                client.publish(topic, json.dumps(message))
            else:
                topic = '/generate_payment_request/{}/reply'.format(device)
                message = {'status': 200,
                           'session_id': p.session_id,
                           'crypto_currency:': p.crypto_currency,
                           'address': '1BvBMSEYstWetqTFn5Au4m4GFg7xJaNVN2'}
                client.publish(topic, json.dumps(message))

        elif tokens[0] == 'payments':
            payment_message = json.loads(msg.payload)
            # if check_blockchain(payment_message['txhash']):
            #     client.publish('/acks/{}'.format(tokens[1]), json.dumps({'txid': TXID}))
            #     TXID = TXID + 1

        elif tokens[0] == 'confirm':
            session_id = tokens[1]
            self.confirm(session_id, client)

    def confirm(self, session_id: str, client: mqtt.Client= None):
        if client is None:
            client = self.mqtt_client

        self.txid = self.txid + 1

        client.publish('/acks/{}'.format(session_id), json.dumps({'txid': self.txid}))

    def generate_payment_request(self, device: str, payment_request: POSPaymentRequestMessage) -> PaymentRequestEnvelope:

        merchant = self.get_merchant(device)
        destinations = self.get_destinations(device=device, payment_request= payment_request)

        message = PaymentRequestMessage(merchant=merchant,
                                        amount=payment_request.amount,
                                        fiat_currency=payment_request.fiat_currency,
                                        destinations=destinations)

        #json_message = json.dumps(unpack(message))
        json_message = json.dumps(message)
        signature = self.sign(json_message.encode('utf-8')).decode('utf-8')

        payment_request_envelope = PaymentRequestEnvelope(json_message, signature)

        return payment_request_envelope



