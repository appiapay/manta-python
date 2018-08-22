from __future__ import annotations

import base64
import logging
from dataclasses import dataclass
from typing import NamedTuple, TYPE_CHECKING, Callable, List, Dict, Set

import paho.mqtt.client as mqtt
import simplejson as json
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import padding
from cryptography.hazmat.primitives.serialization import load_pem_private_key
from manta.messages import PaymentRequestMessage, MerchantOrderRequestMessage, PaymentRequestEnvelope, Destination, \
    MerchantOrderReplyMessage, PaymentMessage, AckMessage

# from cryptography.hazmat.primitives.asymmetric.rsa import RSAPrivateKey

if TYPE_CHECKING:
    from cryptography.hazmat.primitives.asymmetric.rsa import RSAPrivateKey

logger = logging.getLogger(__name__)


class Conf(NamedTuple):
    url: str
    nano_address: str
    key_file: str
    nano_euro: float


@dataclass
class SessionData:
    device: str
    merchant_order: MerchantOrderRequestMessage
    ack: AckMessage = None
    payment_request: PaymentRequestMessage = None


def isnamedtupleinstance(x):
    _type = type(x)
    bases = _type.__bases__
    if len(bases) != 1 or bases[0] != tuple:
        return False
    fields = getattr(_type, '_fields', None)
    if not isinstance(fields, tuple):
        return False
    return all(type(i) == str for i in fields)


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


def generate_crypto_legacy_url(crypto: str, address: str, amount: float) -> str:
    if crypto == 'btc':
        return "bitcoin:{}?amount={}".format(address, amount)


class PayProc:
    mqtt_client: mqtt.Client
    host: str
    key: RSAPrivateKey
    get_merchant: Callable[[str], str]
    _get_pino: Callable[[str], str]
    get_destinations: Callable[[str, MerchantOrderRequestMessage], List[Destination]] = None
    get_supported_cryptos: Callable[[str, MerchantOrderRequestMessage], Set[str]] = None
    # device: str, amount: float, fiat_currency: str
    # get_destinations: Callable[[str, float, ], List[Destination]]
    # get_destinations: (device: str, amount: float, fiat_currency: str) -> List [Destination]
    # payment_requests: Dict[str, PaymentRequestMessage] = {}
    session_data: Dict[str, SessionData] = {}
    txid: int = 0
    testing: bool = False

    def __init__(self, key_file: str, host: str = "localhost", testing: bool = False):

        self.testing = testing
        self.mqtt_client = mqtt.Client()
        self.mqtt_client.on_connect = self.on_connect
        self.mqtt_client.on_message = self.on_message
        self.host = host

        with open(key_file, 'rb') as myfile:
            key_data = myfile.read()

        self.key = PayProc.key_from_keydata(key_data)

    def run(self):
        self.mqtt_client.connect(host=self.host)
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

    def on_connect(self, client, userdata, flags, rc):
        logger.info("Connected with result code " + str(rc))

        client.subscribe('generate_payment_request/+/request')
        client.subscribe('payments/#')

        if self.testing:
            client.subscribe('test/#')

    def on_message(self, client: mqtt.Client, userdata, msg):
        global TXID

        logger.info("Got {} on {}".format(msg.payload, msg.topic))

        tokens = msg.topic.split('/')

        if tokens[0] == 'generate_payment_request':
            logger.info("Processing generate_payment_request message")
            device = tokens[1]
            p = MerchantOrderRequestMessage(**json.loads(msg.payload))

            # This is a manta request
            if p.crypto_currency is None:
                # envelope = self.generate_payment_request(device, p)
                self.session_data[p.session_id] = SessionData(
                    device=device,
                    merchant_order=p)
                #
                # logger.info(envelope)
                # client.publish('payment_requests/{}'.format(p.session_id), json.dumps(envelope),
                #                retain=True)
                client.subscribe('payment_requests/{}/+'.format(p.session_id))
                client.subscribe('payments/{}'.format(p.session_id))
                # generate_payment_request reply
                topic = 'generate_payment_request/{}/reply'.format(device)
                reply = MerchantOrderReplyMessage(
                    status=200,
                    session_id=p.session_id,
                    url="manta://{}/{}".format(self.host, p.session_id)
                )
                client.publish(topic, reply.to_json())
            else:
                topic = 'generate_payment_request/{}/reply'.format(device)
                destinations = self.get_destinations(device, p)
                d = destinations[0]
                reply = MerchantOrderReplyMessage(
                    status=200,
                    session_id=p.session_id,
                    url=generate_crypto_legacy_url(d.crypto_currency, d.destination_address, d.amount)
                )

                client.publish(topic, reply.to_json())

        elif tokens[0] == 'payment_requests':
            session_id = tokens[1]
            session_data = self.session_data[session_id]
            request = MerchantOrderRequestMessage(
                fiat_currency=session_data.merchant_order.fiat_currency,
                amount=session_data.merchant_order.amount,
                session_id=session_id,
                crypto_currency=None if tokens[2] == 'all' else tokens[2]
            )
            device = session_data.device

            envelope = self.generate_payment_request(session_data.device, request)
            session_data.payment_request = envelope.unpack()

            logger.info(envelope)
            client.publish('payment_requests/{}'.format(session_id), envelope.to_json())

        elif tokens[0] == 'payments':
            session_id = tokens[1]

            if session_id in self.session_data:
                decoded = json.loads(msg.payload)

                # Duplicate message
                if self.session_data[session_id].ack:
                    return

                payment_message = PaymentMessage(**decoded)

                reply = self.ack(
                    txid=str(self.txid),
                    transaction_hash=payment_message.transaction_hash,
                    status='pending',
                    session_id=session_id
                )

                self.session_data[session_id].ack = reply

                self.txid = self.txid + 1

        elif tokens[0] == 'confirm':
            session_id = tokens[1]
            self.confirm(session_id, client)

        if not self.testing:
            return

        if tokens[0] == 'test':
            logger.info('Got test message')
            if tokens[1] == 'ack':
                decode = json.loads(msg.payload)

                self.ack(**decode)

    def ack(self, status: str, txid: int, transaction_hash: str, session_id: str) -> AckMessage:
        logger.info("Publishing ack for {} as {}".format(session_id, status))

        ack_message = AckMessage(
            txid=str(txid),
            transaction_hash=transaction_hash,
            status=status
        )

        self.mqtt_client.publish('acks/{}'.format(session_id), ack_message.to_json())

        return ack_message

    def confirm(self, session_id: str, client: mqtt.Client = None):
        if client is None:
            client = self.mqtt_client

        if session_id in self.session_data:
            ack = self.session_data[session_id].ack

            self.ack(
                txid=ack.txid,
                transaction_hash=ack.transaction_hash,
                status='paid',
                session_id=session_id
            )

    def generate_payment_request(self, device: str,
                                 payment_request: MerchantOrderRequestMessage) -> PaymentRequestEnvelope:

        merchant = self.get_merchant(device)
        destinations = self.get_destinations(device, payment_request)
        supported_cryptos = self.get_supported_cryptos(device=device, payment_request=payment_request)

        message = PaymentRequestMessage(merchant=merchant,
                                        amount=payment_request.amount,
                                        fiat_currency=payment_request.fiat_currency,
                                        destinations=destinations,
                                        supported_cryptos=supported_cryptos)

        json_message = message.to_json()
        signature = self.sign(json_message.encode('utf-8')).decode('utf-8')

        payment_request_envelope = PaymentRequestEnvelope(json_message, signature)

        return payment_request_envelope
