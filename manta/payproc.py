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
from manta.dispatcher import Dispatcher

from manta.messages import PaymentRequestMessage, MerchantOrderRequestMessage, PaymentRequestEnvelope, Destination, \
    PaymentMessage, AckMessage, Status, Merchant

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


def generate_crypto_legacy_url(crypto: str, address: str, amount: float) -> str:
    if crypto == 'btc':
        return "bitcoin:{}?amount={}".format(address, amount)


class PayProc:
    mqtt_client: mqtt.Client
    host: str
    key: RSAPrivateKey
    get_merchant: Callable[[str], Merchant]
    get_destinations: Callable[[str, MerchantOrderRequestMessage], List[Destination]] = None
    get_supported_cryptos: Callable[[str, MerchantOrderRequestMessage], Set[str]] = None
    # device: str, amount: float, fiat_currency: str
    # get_destinations: Callable[[str, float, ], List[Destination]]
    # get_destinations: (device: str, amount: float, fiat_currency: str) -> List [Destination]
    # payment_requests: Dict[str, PaymentRequestMessage] = {}
    session_data: Dict[str, SessionData] = {}
    dispatcher: Dispatcher
    txid: int = 0

    def __init__(self, key_file: str, host: str = "localhost"):

        self.dispatcher = Dispatcher(self)
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

    # noinspection PyUnusedLocal,PyMethodMayBeStatic
    def on_connect(self, client, userdata, flags, rc):
        logger.info("Connected with result code " + str(rc))

        client.subscribe("merchant_order_request/+")

    @Dispatcher.method_topic("merchant_order_request/+")
    def on_merchant_order_request(self, device, payload):

        logger.info("Processing merchant_order message")

        p = MerchantOrderRequestMessage(**json.loads(payload))

        # This is a manta request
        if p.crypto_currency is None:
            # envelope = self.generate_payment_request(device, p)

            self.mqtt_client.subscribe('payment_requests/{}/+'.format(p.session_id))
            self.mqtt_client.subscribe('payments/{}'.format(p.session_id))

            ack = AckMessage(
                status=Status.NEW,
                url="manta://{}/{}".format(self.host, p.session_id),
                txid=str(self.txid)
            )

            self.ack(p.session_id, ack)

            self.session_data[p.session_id] = SessionData(
                device=device,
                merchant_order=p,
                ack=ack
            )

            self.txid = self.txid + 1

        else:
            destinations = self.get_destinations(device, p)
            d = destinations[0]

            ack = AckMessage(
                txid=str(self.txid),
                status=Status.NEW,
                url=generate_crypto_legacy_url(d.crypto_currency, d.destination_address, d.amount)
            )

            self.ack(p.session_id, ack)

    # noinspection PyUnusedLocal
    @Dispatcher.method_topic("payment_requests/+/+")
    def on_get_payment_request(self, session_id: str, crypto_currency: str, payload: str):
        logger.info("Processing payment request message")
        session_data = self.session_data[session_id]
        request = MerchantOrderRequestMessage(
            fiat_currency=session_data.merchant_order.fiat_currency,
            amount=session_data.merchant_order.amount,
            session_id=session_id,
            crypto_currency=None if crypto_currency == 'all' else crypto_currency
        )
        device = session_data.device

        envelope = self.generate_payment_request(session_data.device, request)
        session_data.payment_request = envelope.unpack()

        logger.info(envelope)
        self.mqtt_client.publish('payment_requests/{}'.format(session_id), envelope.to_json())

    @Dispatcher.method_topic("payments/+")
    def on_payment(self, session_id: str, payload: str):

        if session_id in self.session_data:
            payment_message = PaymentMessage.from_json(payload)
            ack = self.session_data[session_id].ack

            ack.status = Status.PENDING
            ack.transaction_hash = payment_message.transaction_hash
            ack.url = None

            self.ack(session_id, ack)

    # noinspection PyUnusedLocal
    def on_message(self, client: mqtt.Client, userdata, msg):
        logger.info("New Message {} on {}".format(msg.payload, msg.topic))

        self.dispatcher.dispatch(msg.topic, payload=msg.payload)

    def ack(self, session_id: str, ack: AckMessage):
        logger.info("Publishing ack for {} as {}".format(session_id, ack.status.value))

        self.mqtt_client.publish('acks/{}'.format(session_id), ack.to_json())

    def confirm(self, session_id: str):

        if session_id in self.session_data:
            ack = self.session_data[session_id].ack
            ack.status = Status.PAID
            self.ack(session_id, ack)

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
