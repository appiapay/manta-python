import asyncio
import logging

import paho.mqtt.client as mqtt

from manta.messages import Destination, MerchantOrderRequestMessage
from manta.payproclib import PayProc

logger = logging.getLogger(__name__)

KEYFILE = "certificates/root/keys/www.brainblocks.com.key"
DESTINATIONS = [
    Destination(
        amount=5,
        destination_address="btc_daddress",
        crypto_currency="btc"
    ),
    Destination(
        amount=10,
        destination_address="nano_daddress",
        crypto_currency="nano"
    ),

]


def get_destinations(device, merchant_order: MerchantOrderRequestMessage):
    if merchant_order.crypto_currency:
        destination = next(x for x in DESTINATIONS if x.crypto_currency == merchant_order.crypto_currency)
        return [destination]
    else:
        return DESTINATIONS


class PayProcDummy:
    mqqt_client: mqtt.Client
    pp: PayProc
    loop: asyncio.AbstractEventLoop

    def __init__(self):
        self.mqtt_client = mqtt.Client()
        self.mqtt_client.on_connect = self.on_connect
        self.mqtt_client.on_message = self.on_message
        self.mqtt_client.on_disconnect = self.on_disconnect
        self.pp = PayProc(KEYFILE)

        self.pp.get_merchant = lambda x: "merchant1"
        self.pp.get_destinations = get_destinations
        self.pp.get_supported_cryptos = lambda device, payment_request: {'btc', 'xmr', 'nano'}

        self.mqtt_client.connect("localhost")
        self.loop = asyncio.get_event_loop()

    def run(self):
        self.pp.run()
        self.mqtt_client.loop_forever()

    def on_connect(self, client: mqtt.Client, userdata, flags, rc):
        logger.info("Connected")
        client.subscribe("test/payproc/#")

    def on_disconnect(self, client, userdata, rc):
        pass

    def on_message(self, client: mqtt.Client, userdata, msg):
        logger.info("Got {} on {}".format(msg.payload, msg.topic))
        tokens = msg.topic.split('/')

        if tokens[0] == "test" and tokens[1] == "payproc":
            pass
            # if tokens[2] == "merchant_order":
            #     logger.info("Got merchant order")
            #     try:
            #         self.loop.run_until_complete(
            #             self.store.merchant_order_request(**json.loads(msg.payload))
            #         )
            #     except Exception:
            #         traceback.print_exc()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    pp_dummy = PayProcDummy()
    pp_dummy.run()





