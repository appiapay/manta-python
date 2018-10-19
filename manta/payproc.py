from __future__ import annotations

import base64
import logging
import traceback
from dataclasses import dataclass
from typing import NamedTuple, TYPE_CHECKING, Callable, List, Dict, Set, Optional
import paho.mqtt.client as mqtt
import simplejson as json
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import padding
from cryptography.hazmat.primitives.serialization import load_pem_private_key
from manta.dispatcher import Dispatcher
from decimal import Decimal

from manta.messages import PaymentRequestMessage, MerchantOrderRequestMessage, PaymentRequestEnvelope, Destination, \
    PaymentMessage, AckMessage, Status, Merchant

from abc import abstractmethod
import attr

# from cryptography.hazmat.primitives.asymmetric.rsa import RSAPrivateKey

if TYPE_CHECKING:
    from cryptography.hazmat.primitives.asymmetric.rsa import RSAPrivateKey

logger = logging.getLogger(__name__)


class Conf(NamedTuple):
    url: str
    nano_address: str
    key_file: str
    nano_euro: float


class SessionDoesNotExist(Exception):
    pass


@dataclass()
class TransactionState:
    txid: int
    session_id: str
    application: str
    order: MerchantOrderRequestMessage
    payment_request: Optional[PaymentRequestMessage] = None
    payment_message: Optional[PaymentMessage] = None
    ack: Optional[AckMessage] = None
    wallet_request: str = None

    notify: Callable[[int, str, any], None] = None

    def __setattr__(self, key, value):
        if self.notify:
            self.notify(self.txid, key, value)

        super().__setattr__(key, value)


class TXStorage:
    @abstractmethod
    def create(self, txid: int,
               session_id: str,
               application: str,
               order: MerchantOrderRequestMessage,
               ack: AckMessage = None) -> TransactionState:
        pass

    @abstractmethod
    def get_state_for_session(self, session_id: str) -> TransactionState:
        pass

    @abstractmethod
    def session_exists(self, session_id: str) -> bool:
        pass

    def __iter__(self):
        return self

    def __next__(self):
        pass

    @abstractmethod
    def __len__(self):
        pass


class TXStorageMemory(TXStorage):
    states: Dict[str, TransactionState]

    def __init__(self):
        self.states = {}

    def _on_notify(self, txid, key, value):
        if key == 'ack':
            value: AckMessage
            if value.status in [Status.PAID, Status.INVALID]:
                session_id = next(key for key, state in self.states.items()
                                  if state.txid == int(value.txid))
                del self.states[session_id]

    def create(self, txid: int,
               session_id: str,
               application: str,
               order: MerchantOrderRequestMessage,
               ack: AckMessage = None) -> TransactionState:

        tx = TransactionState(txid=txid,
                              session_id=session_id,
                              application=application,
                              order=order,
                              ack=ack,
                              notify=self._on_notify)

        self.states[session_id] = tx

        return tx

    def get_state_for_session(self, session_id: str) -> TransactionState:
        return self.states[session_id]

    def session_exists(self, session_id: str) -> bool:
        return session_id in self.states

    def __iter__(self):
        return iter(self.states.items())

    def __len__(self):
        return len(self.states)


def generate_crypto_legacy_url(crypto: str, address: str, amount: float) -> str:
    if crypto == 'btc':
        return "bitcoin:{}?amount={}".format(address, amount)

    return ""


class PayProc:
    mqtt_client: mqtt.Client
    host: str
    key: RSAPrivateKey
    certificate: str
    get_merchant: Callable[[str], Merchant]

    # get_destinations(application: str, merchant_order: MerchantOrderRequestMessage)
    get_destinations: Callable[[str, MerchantOrderRequestMessage], List[Destination]]

    # get_supported_cryptos(application: str, merchant_order: MerchantOrderRequestMessage)
    get_supported_cryptos: Callable[[str, MerchantOrderRequestMessage], Set[str]]

    # str is txid
    on_processed_order: Optional[Callable[[str, MerchantOrderRequestMessage, AckMessage], None]] = None

    # on_processed_get_payment(txid, crypto, payment_request_message)
    on_processed_get_payment: Optional[Callable[[str, str, PaymentRequestMessage], None]] = None

    # str is txid
    on_processed_payment: Optional[Callable[[str, PaymentMessage, AckMessage], None]] = None

    on_processed_confirmation: Optional[Callable[[str, AckMessage], None]] = None

    tx_storage: TXStorage
    dispatcher: Dispatcher
    txid: int

    def __init__(self, key_file: str, cert_file: str=None, host: str = "localhost", starting_txid: int = 0,
                 tx_storage: TXStorage = None, mqtt_options: Dict[str:any]= None) -> None:

        self.txid = starting_txid
        self.tx_storage = tx_storage if tx_storage is not None else TXStorageMemory()
        self.dispatcher = Dispatcher(self)
        mqtt_options = mqtt_options if mqtt_options else {}
        self.mqtt_client = mqtt.Client(**mqtt_options)
        self.mqtt_client.on_connect = self.on_connect
        self.mqtt_client.on_message = self.on_message
        self.mqtt_client.enable_logger()
        self.host = host

        with open(key_file, 'rb') as myfile:
            key_data = myfile.read()

        self.key = PayProc.key_from_keydata(key_data)

        if cert_file is not None:
            with open(cert_file, 'r') as myfile:
                self.certificate = myfile.read()
        else:
            self.certificate = ""

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

        self._subscribe("merchant_order_request/+")

        for session, value in self.tx_storage:
            self._subscribe("acks/{}".format(session))
            self._subscribe("payment_requests/{}/+".format(session))
            self._subscribe("payments/{}".format(session))

        self.mqtt_client.publish("certificate", self.certificate, retain=True)

    def _subscribe(self, topic):
        self.mqtt_client.subscribe(topic)
        logger.info('Subscribed to {}'.format(topic))

    @Dispatcher.method_topic("merchant_order_request/+")
    def on_merchant_order_request(self, device, payload):

        logger.info("Processing merchant_order message")

        p = MerchantOrderRequestMessage(**json.loads(payload))

        ack: AckMessage = None

        # This is a manta request
        if not p.crypto_currency:
            # envelope = self.generate_payment_request(device, p)

            self.mqtt_client.subscribe('payment_requests/{}/+'.format(p.session_id))
            self.mqtt_client.subscribe('payments/{}'.format(p.session_id))

            ack = AckMessage(
                status=Status.NEW,
                url="manta://{}/{}".format(self.host, p.session_id),
                txid=str(self.txid)
            )

            self.ack(p.session_id, ack)

            self.tx_storage.create(self.txid, p.session_id, device, p, ack)

            self.txid = self.txid + 1

        else:
            destinations = self.get_destinations(device, p)
            d = destinations[0]

            ack = AckMessage(
                txid=str(self.txid),
                status=Status.NEW,
                url=generate_crypto_legacy_url(d.crypto_currency, d.destination_address, Decimal(d.amount))
            )

            self.ack(p.session_id, ack)

            self.tx_storage.create(self.txid, p.session_id, device, p, ack),

            self.txid = self.txid + 1

        if self.on_processed_order:
            self.on_processed_order(ack.txid, p, ack)

    # noinspection PyUnusedLocal
    @Dispatcher.method_topic("payment_requests/+/+")
    def on_get_payment_request(self, session_id: str, crypto_currency: str, payload: str):
        logger.info("Processing payment request message")

        state = self.tx_storage.get_state_for_session(session_id)

        state.wallet_request = crypto_currency

        request = MerchantOrderRequestMessage(
            fiat_currency=state.order.fiat_currency,
            amount=state.order.amount,
            session_id=session_id,
            crypto_currency=None if crypto_currency == 'all' else crypto_currency
        )
        application = state.application

        envelope = self.generate_payment_request(application, request)
        state.payment_request = envelope.unpack()

        logger.info("Publishing {}".format(envelope))
        self.mqtt_client.publish('payment_requests/{}'.format(session_id), envelope.to_json())

        if self.on_processed_get_payment:
            self.on_processed_get_payment(state.ack.txid, crypto_currency, envelope.unpack())

    @Dispatcher.method_topic("payments/+")
    def on_payment(self, session_id: str, payload: str):

        if self.tx_storage.session_exists(session_id):
            payment_message = PaymentMessage.from_json(payload)
            state = self.tx_storage.get_state_for_session(session_id)
            new_ack = attr.evolve(state.ack,
                                  status=Status.PENDING,
                                  transaction_hash=payment_message.transaction_hash,
                                  transaction_currency=payment_message.crypto_currency,
                                  url=None
                                  )

            state.ack = new_ack
            state.payment_message = payment_message

            self.ack(session_id, new_ack)

            if self.on_processed_payment:
                self.on_processed_payment(state.ack.txid, payment_message, new_ack)

    # noinspection PyUnusedLocal
    def on_message(self, client: mqtt.Client, userdata, msg):
        logger.info("New Message {} on {}".format(msg.payload, msg.topic))

        try:
            self.dispatcher.dispatch(msg.topic, payload=msg.payload)
        except Exception as e:
            logger.error(e)
            traceback.print_exc()

    def ack(self, session_id: str, ack: AckMessage):
        logger.info("Publishing ack for {} as {}".format(session_id, ack.status.value))

        self.mqtt_client.publish('acks/{}'.format(session_id), ack.to_json())

    def confirm(self, session_id: str):

        if self.tx_storage.session_exists(session_id):
            state = self.tx_storage.get_state_for_session(session_id)

            new_ack = attr.evolve(state.ack, status=Status.PAID)

            state.ack = new_ack
            self.ack(session_id, new_ack)

            if self.on_processed_confirmation:
                self.on_processed_confirmation(state.ack.txid, new_ack)

    def invalidate(self, session_id: str, reason: str=""):
        if self.tx_storage.session_exists(session_id):
            state = self.tx_storage.get_state_for_session(session_id)

            new_ack = attr.evolve(state.ack, status=Status.INVALID, memo=reason)

            state.ack = new_ack
            self.ack(session_id, new_ack)

    def generate_payment_request(self, device: str,
                                 payment_request: MerchantOrderRequestMessage) -> PaymentRequestEnvelope:

        merchant = self.get_merchant(device)
        destinations = self.get_destinations(device, payment_request)
        supported_cryptos = self.get_supported_cryptos(device, payment_request)

        message = PaymentRequestMessage(merchant=merchant,
                                        amount=payment_request.amount,
                                        fiat_currency=payment_request.fiat_currency,
                                        destinations=destinations,
                                        supported_cryptos=supported_cryptos)

        json_message = message.to_json()
        signature = self.sign(json_message.encode('utf-8')).decode('utf-8')

        payment_request_envelope = PaymentRequestEnvelope(json_message, signature)

        return payment_request_envelope
