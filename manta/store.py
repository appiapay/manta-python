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
Library for implementing a Manta Pos
"""

from __future__ import annotations

import asyncio
import base64
from decimal import Decimal
import logging
import uuid
from typing import List, Dict

import paho.mqtt.client as mqtt

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


class Store:
    """
    Store Class for implement Manta POS

    Args:
        device_id: Device unique identifier of POS
        host: Hostname of the Manta Broker
        client_options: A Dict of options to be passed to MQTT Client (like username, password)

    Attributes:
        acks (asyncio.Queue): Queue of Acks messages. Wait for it to retrieve the first available message


    """
    mqtt_client: mqtt.Client
    loop: asyncio.AbstractEventLoop
    connected: asyncio.Event
    device_id: str
    session_id: str = None
    acks: asyncio.Queue
    first_connect = False
    subscriptions: List[str] = []
    host: str

    def __init__(self, device_id: str, host: str= "localhost", client_options: Dict = None):
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

    def close(self):
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
        self.mqtt_client.subscribe(topic)
        self.subscriptions.append(topic)

    def clean(self):
        self.acks = asyncio.Queue()

        if len(self.subscriptions) > 0:
            self.mqtt_client.unsubscribe(self.subscriptions)

    async def connect(self):
        if not self.first_connect:
            self.mqtt_client.connect(self.host)
            self.mqtt_client.loop_start()
            self.first_connect = True

        await self.connected.wait()

    # def generate_payment_request(self, amount: float, fiat: str, crypto: str = None):
    #     return self.loop.run_until_complete(self.__generate_payment_request(amount, fiat, crypto))

    async def merchant_order_request(self, amount: Decimal, fiat: str, crypto: str = None) -> AckMessage:
        """
        Create a new Merchant Order

        Args:
            amount: Fiat Amount requested
            fiat: Fiat Currency requested (ex. 'EUR')
            crypto: Crypto Currency requested (ex. 'NANO')

        Returns:
            AckMessage with status 'NEW' if confirmed by Payment Processor or Timeout Exception

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
