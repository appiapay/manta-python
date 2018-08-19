import paho.mqtt.client as mqtt
import asyncio
import logging
import threading
import simplejson as json
import base64, uuid

from typing import Callable

from manta.messages import MerchantOrderReplyMessage, MerchantOrderRequestMessage, AckMessage

logger = logging.getLogger(__name__)


def generate_session_id() -> str:
    return base64.b64encode(uuid.uuid4().bytes)
    # The following is more secure
    # return base64.b64encode(M2Crypto.m2.rand_bytes(num_bytes))


class Store:
    mqtt_client: mqtt.Client
    loop: asyncio.AbstractEventLoop
    connected: bool = False
    connect_future: asyncio.Future = None
    generate_payment_future: asyncio.Future = None
    device_id: str
    session_id: str = None
    ack_callback: Callable[[str, AckMessage], None]

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

        self.mqtt_client.loop_start()

    def on_disconnect(self, client, userdata, rc):
        self.connected = False

    def on_connect(self, client, userdata, flags, rc):
        logger.info("Connected")
        self.connected = True
        self.loop.call_soon_threadsafe(self.connect_future.set_result, None)

    def on_message(self, client: mqtt.Client, userdata, msg):
        logger.info("Got {} on {}".format(msg.payload, msg.topic))
        tokens = msg.topic.split('/')

        if tokens[0] == 'generate_payment_request':
            decoded = json.loads(msg.payload)
            reply = MerchantOrderReplyMessage(**decoded)

            if reply.status == 200:
                self.loop.call_soon_threadsafe(self.generate_payment_future.set_result, reply.url)
            else:
                self.loop.call_soon_threadsafe(self.generate_payment_future.set_exception, Exception(reply.status))
        elif tokens[0] == 'acks':
            session_id = tokens[1]
            logger.info("Got ack message")
            decoded = json.loads(msg.payload)
            ack = AckMessage(**decoded)
            self.ack_callback(session_id, ack)

    async def connect(self):
        if self.connected:
            return

        if self.connect_future is None:
            self.connect_future = self.loop.create_future()
            self.mqtt_client.connect("localhost")

        if self.connect_future.done():
            self.connect_future = self.loop.create_future()  

        await self.connect_future

    def generate_payment_request(self, amount: float, fiat: str, crypto: str = None):
        return self.loop.run_until_complete(self.__generate_payment_request(amount, fiat, crypto))

    async def __generate_payment_request(self, amount: float, fiat: str, crypto: str = None):
        await self.connect()
        self.session_id = generate_session_id()
        request = MerchantOrderRequestMessage(
            amount=amount,
            session_id=self.session_id,
            fiat_currency=fiat,
            crypto_currency=crypto
        )
        self.generate_payment_future = self.loop.create_future()
        self.mqtt_client.publish("generate_payment_request/{}".format(self.device_id),
                                 json.dumps(request))

        result = await asyncio.wait_for(self.generate_payment_future, 3)

        return result


if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)
    store = Store("device1")
    store.generate_payment_request()
