# Manta Python
# Manta Protocol Implementation for Python
# Copyright (C) 2018 Alessandro Viganò
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

# from __future__ import annotations

"""
Library for implementing a Manta Payment Processor
"""

from abc import abstractmethod
import base64
from dataclasses import dataclass
from decimal import Decimal
import logging
import traceback
from typing import Any, Callable, Dict, List, NamedTuple, Optional, Set

import attr
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import padding
from cryptography.hazmat.primitives.asymmetric.rsa import RSAPrivateKey
from cryptography.hazmat.primitives.serialization import load_pem_private_key
import paho.mqtt.client as mqtt

from .base import MantaComponent
from .dispatcher import Dispatcher
from .messages import (PaymentRequestMessage, MerchantOrderRequestMessage,
                       PaymentRequestEnvelope, Destination, PaymentMessage,
                       AckMessage, Status, Merchant)


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
    # noinspection PyUnresolvedReferences
    """
        Transaction State represents state of a Transaction

        Args:
            txid: Transaction ID
            session_id: Session ID of transaction
            application: Application ID of transaction
            order: Merchant order for transaction
            payment_request: Last payment request of transaction
            payment_message: Last payment message of transaction
            ack: Last ack of transaction
            wallet_request: Last wallet request of transaction
            notify: callback to be called when attributes of transaction change
        """
    txid: int
    session_id: str
    application: str
    order: MerchantOrderRequestMessage
    payment_request: Optional[PaymentRequestMessage] = None
    payment_message: Optional[PaymentMessage] = None
    ack: Optional[AckMessage] = None
    wallet_request: Optional[str] = None

    notify: Optional[Callable[[int, str, Any], None]] = None

    def __setattr__(self, key, value):
        if callable(self.notify):
            self.notify(self.txid, key, value)

        super().__setattr__(key, value)


class TXStorage:
    """
    Storage for Active Session Data of Transaction

    This is an abstract class to be implemented in subclassing.
    This is meant to be used with external storage like a database.
    Payproc will use a memory TXStorage implementation by default, which is not persistent.

    Transaction with status 'PAID' or 'INVALID' must not be present

    """
    @abstractmethod
    def create(self, txid: int,
               session_id: str,
               application: str,
               order: MerchantOrderRequestMessage,
               ack: AckMessage = None) -> TransactionState:
        """
        Create a new transaction

        Args:
            txid: txid of Transaction
            session_id: session_id of Transaction
            application: application_id of Transaction
            order: Merchant Order of Transaction
            ack: First Ack Message (ie status=NEW)

        Returns:

        """
        pass

    @abstractmethod
    def get_state_for_session(self, session_id: str) -> TransactionState:
        """
        Get state for transaction with session_id

        Args:
            session_id: session_id of transaction

        Returns: state of transaction

        """
        pass

    @abstractmethod
    def session_exists(self, session_id: str) -> bool:
        """
        Check if session exist

        Args:
            session_id: session_id of transaction

        Returns: true if session exist

        """
        pass

    def __iter__(self):
        return self

    def __next__(self):
        pass

    @abstractmethod
    def __len__(self):
        pass


class TXStorageMemory(TXStorage):
    """
    Implmentation of TXStorage as memory storage
    """
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


class PayProc(MantaComponent):
    # noinspection PyUnresolvedReferences
    """
        Manta Protocol Payment Processor Implementation

        Args:
            key_file: File name of PEM private key of Payment Processor. This will be used to sign messages
            certificate: File name of Manta Certificate Authority, IE Appia
            host: MQTT Broker host
            starting_txid: Transaction ID are progressive, starting from the one specified
            tx_storage: TXStorage instance to store session information
            mqtt_options: A Dict of options to be passed to MQTT Client (like username, password)

        Attributes:
            get_destinations: Callback function to retrieve list of Destination
            get_supported_cryptos: Callback function to retrieve list of supported cryptos
        """

    key: RSAPrivateKey
    certificate: str

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

    def __init__(self, key_file: str, cert_file: str = None, host: str = "localhost",
                 starting_txid: int = 0, tx_storage: TXStorage = None,
                 mqtt_options: Dict[str, Any] = None, port: int = 1883) -> None:

        self.txid = starting_txid
        self.tx_storage = tx_storage if tx_storage is not None else TXStorageMemory()
        self.dispatcher = Dispatcher(self)
        mqtt_options = mqtt_options if mqtt_options else {}
        self.mqtt_client = mqtt.Client(**mqtt_options)
        self.mqtt_client.on_connect = self.on_connect
        self.mqtt_client.on_message = self.on_message
        self.mqtt_client.enable_logger()
        self.host = host
        self.port = port

        with open(key_file, 'rb') as myfile:
            key_data = myfile.read()

        self.key = PayProc.key_from_keydata(key_data)

        if cert_file is not None:
            with open(cert_file, 'r') as cfile:
                self.certificate = cfile.read()
        else:
            self.certificate = ""

        self.get_merchant: Callable[[str], Merchant]
        # get_destinations(application: str, merchant_order: MerchantOrderRequestMessage)
        self.get_destinations: Callable[[str, MerchantOrderRequestMessage], List[Destination]]

        # get_supported_cryptos(application: str, merchant_order: MerchantOrderRequestMessage)
        self.get_supported_cryptos: Callable[[str, MerchantOrderRequestMessage], Set[str]]

    def run(self):
        """
            Start processing network requests
        """
        self.mqtt_client.connect(host=self.host, port=self.port)
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
        self._subscribe("merchant_order_cancel/+")

        for session, value in self.tx_storage:
            self._subscribe("payment_requests/{}/+".format(session))
            self._subscribe("payments/{}".format(session))

        self.mqtt_client.publish("certificate", self.certificate, retain=True)

    def _subscribe(self, topic):
        self.mqtt_client.subscribe(topic)
        logger.info('Subscribed to %r', topic)

    @Dispatcher.method_topic("merchant_order_cancel/+")
    def on_merchant_order_cancel(self, session_id, payload):
        logger.info("Request for canceling order with session_id %r", session_id)

        self.invalidate(session_id, "Canceled by Merchant")

    @Dispatcher.method_topic("merchant_order_request/+")
    def on_merchant_order_request(self, application_id, payload):

        logger.info("Processing merchant_order message")

        # p = MerchantOrderRequestMessage(**json.loads(payload))
        p = MerchantOrderRequestMessage.from_json(payload)

        ack: AckMessage = None

        # This is a manta request
        if not p.crypto_currency:
            # envelope = self.generate_payment_request(device, p)

            self.mqtt_client.subscribe('payment_requests/{}/+'.format(p.session_id))
            self.mqtt_client.subscribe('payments/{}'.format(p.session_id))

            ack = AckMessage(
                status=Status.NEW,
                url="manta://{}{}/{}".format(self.host,
                                             ':' + str(self.port) if self.port != 1883
                                             else '',
                                             p.session_id),
                txid=str(self.txid)
            )

            self.ack(p.session_id, ack)

            self.tx_storage.create(self.txid, p.session_id, application_id, p, ack)

            self.txid = self.txid + 1

        else:
            destinations = self.get_destinations(application_id, p)
            d = destinations[0]

            ack = AckMessage(
                txid=str(self.txid),
                status=Status.NEW,
                url=generate_crypto_legacy_url(d.crypto_currency, d.destination_address, Decimal(d.amount))
            )

            self.ack(p.session_id, ack)

            self.tx_storage.create(self.txid, p.session_id, application_id, p, ack),

            self.txid = self.txid + 1

        if callable(self.on_processed_order):
            self.on_processed_order(ack.txid, p, ack)

    # noinspection PyUnusedLocal
    @Dispatcher.method_topic("payment_requests/+/+")
    def on_get_payment_request(self, session_id: str, crypto_currency: str, payload: str):
        logger.info("Processing payment request message")

        state: TransactionState = self.tx_storage.get_state_for_session(session_id)

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

        if callable(self.on_processed_get_payment):
            assert state.ack is not None
            self.on_processed_get_payment(state.ack.txid, crypto_currency, envelope.unpack())

    @Dispatcher.method_topic("payments/+")
    def on_payment(self, session_id: str, payload: str):

        if self.tx_storage.session_exists(session_id):
            payment_message = PaymentMessage.from_json(payload)

            state = self.tx_storage.get_state_for_session(session_id)

            # check if crypto is one of the supported
            payment_request = state.payment_request

            assert payment_request is not None
            if payment_message.crypto_currency.upper() not in \
               [x.upper() for x in payment_request.supported_cryptos]:
                return

            new_ack = attr.evolve(state.ack,
                                  status=Status.PENDING,
                                  transaction_hash=payment_message.transaction_hash,
                                  transaction_currency=payment_message.crypto_currency,
                                  url=None)
            assert new_ack is not None

            state.payment_message = payment_message
            state.ack = new_ack

            self.ack(session_id, new_ack)

            if callable(self.on_processed_payment):
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

    def confirming(self, session_id: str):
        """

        Change the status of session_id to CONFIRMING and send the ack

        Args:
            session_id: session to change

        """

        if self.tx_storage.session_exists(session_id):
            state = self.tx_storage.get_state_for_session(session_id)

            new_ack = attr.evolve(state.ack, status=Status.CONFIRMING)
            assert new_ack is not None
            state.ack = new_ack
            self.ack(session_id, new_ack)

    def confirm(self, session_id: str):
        """

        Change the status of session_id to PAID and send the ack

        Args:
            session_id: session to change

        """

        if self.tx_storage.session_exists(session_id):
            state = self.tx_storage.get_state_for_session(session_id)

            new_ack = attr.evolve(state.ack, status=Status.PAID)
            assert new_ack is not None

            state.ack = new_ack
            self.ack(session_id, new_ack)

            if callable(self.on_processed_confirmation):
                self.on_processed_confirmation(state.ack.txid, new_ack)

    def invalidate(self, session_id: str, reason: str = ""):
        """

            Change the status of session_id to INVALID and send the ack

        Args:
            session_id: session to change
            reason: reason for INVALID (ex. 'Timeout')
        """

        if self.tx_storage.session_exists(session_id):
            state = self.tx_storage.get_state_for_session(session_id)

            new_ack = attr.evolve(state.ack, status=Status.INVALID, memo=reason)
            assert new_ack is not None

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

        payment_request_envelope = PaymentRequestEnvelope(
            message=json_message, signature=signature)

        return payment_request_envelope
