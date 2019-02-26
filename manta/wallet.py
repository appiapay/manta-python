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

"""
Library with a basic implementation of a Manta :term:`Wallet`.
"""

from __future__ import annotations

import asyncio
import logging
import re
from typing import Match, Optional

from cryptography import x509
from cryptography.hazmat.backends import default_backend
import paho.mqtt.client as mqtt

from .base import MantaComponent
from .messages import PaymentRequestEnvelope, PaymentMessage, AckMessage


logger = logging.getLogger(__name__)


def wrap_callback(f):
    def wrapper(self: Wallet, *args):
        self.loop.call_soon_threadsafe(f, self, *args)

    return wrapper


class Wallet(MantaComponent):
    """
    Implements a Manta :term:`Wallet`. This class needs an *asyncio* loop
    to run correctly as some of its features are implemented as
    *coroutines*.

    This is usually instantiated from a :term:`Manta URL` using the
    :meth:`.factory` classmethod.

    Args:
        url: a string containing a :term:`Manta URL`
        session_id: a session_id
        host: :term:`MQTT` broker IP addresses
        port: optional port number of the broker service

    Attributes:
        acks: queue of :class:`~.messages.AckMessage` instances
        loop: the *asyncio* loop that manages the asynchronous parts of this
          object
        session_id: :term:`session_id` of the ongoing session, if any
    """
    loop: asyncio.AbstractEventLoop
    connected: asyncio.Event
    port: int
    session_id: str
    payment_request_future: Optional[asyncio.Future] = None
    certificate_future: Optional[asyncio.Future] = None
    acks: asyncio.Queue
    first_connect = False

    @classmethod
    def factory(cls, url: str):
        """
        This creates an instance from a :term:`Manta URL`. Can be ``None``
        if the URL is invalid.

        Args:
            url: manta url (ex. manta://developer.beappia.com/2848839943)

        Returns:
            a new configured but unconnected instance
        """
        match = cls.parse_url(url)
        if match:
            port = 1883 if match[2] is None else int(match[2])
            return cls(url, match[3], host=match[1], port=port)
        else:
            return None

    def __init__(self, url: str, session_id: str, host: str = "localhost",
                 port: int = 1883):
        self.host = host
        self.port = port
        self.session_id = session_id

        self.mqtt_client = mqtt.Client()
        self.mqtt_client.on_connect = self.on_connect
        self.mqtt_client.on_message = self.on_message
        self.mqtt_client.on_disconnect = self.on_disconnect

        try:
            self.loop = asyncio.get_event_loop()
        except RuntimeError:
            self.loop = asyncio.new_event_loop()
            asyncio.set_event_loop(self.loop)

        self.acks = asyncio.Queue(loop=self.loop)
        self.connected = asyncio.Event(loop=self.loop)

    def close(self):
        """Disconnect and stop :term:`MQTT` client's processing loop."""
        self.mqtt_client.disconnect()
        self.mqtt_client.loop_stop()

    @wrap_callback
    def on_disconnect(self, client, userdata, rc):
        self.connected.clear()

    @wrap_callback
    def on_connect(self, client: mqtt.Client, userdata, flags, rc):
        logger.info("Connected")
        self.certificate_future = self.loop.create_future()
        client.subscribe("certificate")
        self.connected.set()

    @wrap_callback
    def on_message(self, client: mqtt.Client, userdata, msg):
        logger.info("New message {} on {}".format(msg.payload, msg.topic))
        tokens = msg.topic.split('/')

        if tokens[0] == "payment_requests":
            envelope = PaymentRequestEnvelope.from_json(msg.payload)
            assert self.payment_request_future is not None
            self.loop.call_soon_threadsafe(self.payment_request_future.set_result, envelope)
        elif tokens[0] == "acks":
            ack = AckMessage.from_json(msg.payload)
            self.acks.put_nowait(ack)
        elif tokens[0] == "certificate":
            assert self.certificate_future is not None
            self.loop.call_soon_threadsafe(self.certificate_future.set_result, msg.payload)

    @staticmethod
    def parse_url(url: str) -> Optional[Match]:
        """
        Convenience method to check if Manta url is valid
        Args:
            url: manta url (ex. manta://developer.beappia.com/2848839943)

        Returns:
            A match object
        """
        # TODO: What is session format?
        pattern = r"^manta://((?:\w|\.)+)(?::(\d+))?/(.+)$"
        return re.match(pattern, url)

    async def connect(self):
        """
        Connect to the :term:`MQTT` broker and wait for the connection
        confirmation.

        This is a coroutine.
        """
        if not self.first_connect:
            self.mqtt_client.connect(self.host, port=self.port)
            self.mqtt_client.loop_start()
            self.first_connect = True

        await self.connected.wait()

    async def get_certificate(self) -> x509.Certificate:
        """
        Get :term:`Payment Processor`'s certificate retained by the
        :term:`MQTT` broker service.

        This is a coroutine
        """
        await self.connect()
        assert self.certificate_future is not None
        certificate = await self.certificate_future
        return x509.load_pem_x509_certificate(certificate, default_backend())

    async def get_payment_request(self, crypto_currency: str = "all") -> PaymentRequestEnvelope:
        """
        Get the :class:`~.messages.PaymentRequestMessage` for specific crypto
        currency, or ``all`` to obtain informations about all the supported
        crypto currencies.

        Args:
            crypto_currency: crypto to request payment for (ex. 'NANO')

        Returns:
            The Payment Request Envelope. It's ``all`` by default

        This is a coroutine
        """
        await self.connect()

        self.payment_request_future = self.loop.create_future()
        self.mqtt_client.subscribe("payment_requests/{}".format(self.session_id))
        self.mqtt_client.publish("payment_requests/{}/{}".format(self.session_id, crypto_currency))

        logger.info("Published payment_requests/{}".format(self.session_id))

        result = await asyncio.wait_for(self.payment_request_future, 3)
        return result

    async def send_payment(self, transaction_hash: str, crypto_currency: str):
        """
        Send payment info

        Args:
            transaction_hash: the hash of transaction sent to blockchain
            crypto_currency: the crypto currency used for transaction

        This is a coroutine
        """
        await self.connect()
        message = PaymentMessage(
            transaction_hash=transaction_hash,
            crypto_currency=crypto_currency
        )
        self.mqtt_client.subscribe("acks/{}".format(self.session_id))
        self.mqtt_client.publish("payments/{}".format(self.session_id),
                                 message.to_json(), qos=1)
