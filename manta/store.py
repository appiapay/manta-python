from __future__ import annotations

import asyncio
import base64
import logging
import uuid
from typing import List

import paho.mqtt.client as mqtt

from manta.messages import MerchantOrderRequestMessage, AckMessage, Status
from decimal import Decimal

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
    mqtt_client: mqtt.Client
    loop: asyncio.AbstractEventLoop
    connected: asyncio.Event
    device_id: str
    session_id: str = None
    acks = asyncio.Queue
    first_connect = False
    subscriptions: List[str] = []

    def __init__(self, device_id: str):
        self.device_id = device_id
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
            self.mqtt_client.connect("localhost")
            self.mqtt_client.loop_start()
            self.first_connect = True

        await self.connected.wait()

    # def generate_payment_request(self, amount: float, fiat: str, crypto: str = None):
    #     return self.loop.run_until_complete(self.__generate_payment_request(amount, fiat, crypto))

    async def merchant_order_request(self, amount: Decimal, fiat: str, crypto: str = None) -> AckMessage:
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
