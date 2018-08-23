from __future__ import annotations

import asyncio
import logging
import re
from typing import Optional, Any, Callable

import paho.mqtt.client as mqtt

from manta.messages import PaymentRequestMessage, PaymentRequestEnvelope, PaymentMessage, AckMessage
from certvalidator import CertificateValidator

logger = logging.getLogger(__name__)


def wrap_callback(f):
    def wrapper(self: Wallet, *args):
        self.loop.call_soon_threadsafe(f, self, *args)

    return wrapper


class Wallet:
    mqtt_client: mqtt.Client
    loop: asyncio.AbstractEventLoop
    connected: asyncio.Event
    host: str
    port: int
    session_id: str
    payment_request_future: asyncio.Future = None
    acks: asyncio.Queue
    first_connect = False

    @classmethod
    def factory(cls, url: str, certificate: str):
        match = cls.parse_url(url)
        if match:
            port = 1883 if match[2] is None else int(match[2])
            return cls(url, match[3], host=match[1], port=port)
        else:
            return None

    def __init__(self, url: str, session_id: str, host: str = "localhost", port: int = 1883):
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
        self.mqtt_client.disconnect()
        self.mqtt_client.loop_stop()

    @wrap_callback
    def on_disconnect(self, client, userdata, rc):
        self.connected.clear()

    @wrap_callback
    def on_connect(self, client, userdata, flags, rc):
        logger.info("Connected")
        self.connected.set()

    @wrap_callback
    def on_message(self, client: mqtt.Client, userdata, msg):
        logger.info("New message {} on {}".format(msg.payload, msg.topic))
        tokens = msg.topic.split('/')

        if tokens[0] == "payment_requests":
            envelope = PaymentRequestEnvelope.from_json(msg.payload)
            self.loop.call_soon_threadsafe(self.payment_request_future.set_result, envelope)
        elif tokens[0] == "acks":
            ack = AckMessage.from_json(msg.payload)
            self.acks.put_nowait(ack)

    @staticmethod
    def parse_url(url: str) -> Optional[re.Match]:
        # TODO: What is session format?
        pattern = "^manta:\\/\\/((?:\\w|\\.)+)(?::(\\d+))?\\/(.+)$"
        return re.match(pattern, url)

    async def connect(self):
        if not self.first_connect:
            self.mqtt_client.connect(self.host, port=self.port)
            self.mqtt_client.loop_start()
            self.first_connect = True

        await self.connected.wait()

    async def get_payment_request(self, crypto_currency: str = "all") -> PaymentRequestEnvelope:
        await self.connect()

        self.payment_request_future = self.loop.create_future()
        self.mqtt_client.subscribe("payment_requests/{}".format(self.session_id))
        self.mqtt_client.publish("payment_requests/{}/{}".format(self.session_id, crypto_currency))

        logger.info("Published on payment_requests")

        result = await asyncio.wait_for(self.payment_request_future, 3)
        return result

    def send_payment(self, transaction_hash: str, crypto_currency: str):
        message = PaymentMessage(
            transaction_hash=transaction_hash,
            crypto_currency=crypto_currency
        )
        self.mqtt_client.subscribe("acks/{}".format(self.session_id))
        self.mqtt_client.publish("payments/{}".format(self.session_id), message.to_json())
