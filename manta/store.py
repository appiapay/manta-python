# Manta Python
# Manta Protocol Implementation for Python
# Copyright (C) 2018-2019 Alessandro Viganò

"""
Library with a basic implementation of a Manta :term:`POS`.
"""

from __future__ import annotations

import asyncio
import base64
from decimal import Decimal
import logging
import uuid
from typing import List, Dict, Optional

import paho.mqtt.client as mqtt

from .base import MantaComponent
from .messages import MerchantOrderRequestMessage, AckMessage, Status

logger = logging.getLogger(__name__)


def generate_session_id() -> str:
    return base64.b64encode(uuid.uuid4().bytes, b"-_").decode("utf-8")
    # The following is more secure
    # return base64.b64encode(M2Crypto.m2.rand_bytes(num_bytes))


def wrap_callback(f):
    def wrapper(self: Store, *args):
        self.loop.call_soon_threadsafe(f, self, *args)

    return wrapper


class Store(MantaComponent):
    """
    Implements a Manta :term:`POS`. This class needs an *asyncio* loop
    to run correctly as some of its features are implemented as
    *coroutines*.

    Args:
        device_id: Device unique identifier (also called :term:`application_id`)
          associated with the :term:`POS`
        host: Hostname of the Manta broker
        client_options: A Dict of options to be passed to MQTT Client (like
          username, password)
        port: port of the Manta broker

    Attributes:
        acks: queue of :class:`~.messages.AckMessage` instances
        device_id: Device unique identifier (also called
          :term:`application_id`) associated with the :term:`POS`
        loop: the *asyncio* loop that manages the asynchronous parts of this
          object
        session_id: :term:`session_id` of the ongoing session, if any
    """
    loop: asyncio.AbstractEventLoop
    connected: asyncio.Event
    device_id: str
    session_id: Optional[str] = None
    acks: asyncio.Queue
    first_connect = False
    subscriptions: List[str] = []

    def __init__(self, device_id: str, host: str = "localhost",
                 client_options: Dict = None, port: int = 1883):
        client_options = {} if client_options is None else client_options

        self.device_id = device_id
        self.host = host
        self.mqtt_client = mqtt.Client(**client_options)
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
        self.port = port

    def close(self):
        """Disconnect and stop :term:`MQTT` client's processing loop."""
        self.mqtt_client.disconnect()
        self.mqtt_client.loop_stop()

    # noinspection PyUnusedLocal
    @wrap_callback
    def on_disconnect(self, client, userdata, rc):
        self.connected.clear()

    # noinspection PyUnusedLocal
    @wrap_callback
    def on_connect(self, client, userdata, flags, rc):
        logger.info("Connected")
        self.connected.set()

    # noinspection PyUnusedLocal
    @wrap_callback
    def on_message(self, client: mqtt.Client, userdata, msg):
        logger.info("Got {} on {}".format(msg.payload, msg.topic))
        tokens = msg.topic.split('/')

        if tokens[0] == 'acks':
            session_id = tokens[1]
            logger.info("Got ack message")
            ack = AckMessage.from_json(msg.payload)
            self.acks.put_nowait(ack)

    def subscribe(self, topic: str):
        """
        Subscribe to the given :term:`MQTT` topic.

        Args:
           topic: string containing the topic name.
        """
        self.mqtt_client.subscribe(topic)
        self.subscriptions.append(topic)

    def clean(self):
        """
        Clean the :class:`~.messages.AckMessage` queue and unsubscribe
        from any active :term:`MQTT` subscriptions.

        """
        self.acks = asyncio.Queue()

        if len(self.subscriptions) > 0:
            self.mqtt_client.unsubscribe(self.subscriptions)

        self.subscriptions.clear()

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

    async def merchant_order_request(self, amount: Decimal, fiat: str,
                                     crypto: str = None) -> AckMessage:
        """
        Create a new Merchant Order and publish it to the
        :ref:`merchant_order_request/{application_id}` topic. Raises an
        exception if an :class:`~.messages.AckMessage` isn't received
        in less than 3 seconds.

        Args:
            amount: Fiat Amount requested
            fiat: Fiat Currency requested (ex. 'EUR')
            crypto: Crypto Currency requested (ex. 'NANO')
        Returns:
            ack message with status 'NEW' if confirmed by Payment Processor or
              Timeout Exception

        This is a coroutine.
        """
        await self.connect()
        self.clean()
        self.session_id = generate_session_id()
        request = MerchantOrderRequestMessage(
            amount=amount,
            session_id=self.session_id,
            fiat_currency=fiat,
            crypto_currency=crypto
        )

        self.subscribe("acks/{}".format(self.session_id))
        self.mqtt_client.publish("merchant_order_request/{}".format(self.device_id),
                                 request.to_json())

        logger.info("Publishing merchant_order_request for session {}".format(self.session_id))

        result: AckMessage = await asyncio.wait_for(self.acks.get(), 3)

        if result.status != Status.NEW:
            raise Exception("Invalid ack")

        return result
