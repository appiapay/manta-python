import traceback

from manta.storelib import Store
import paho.mqtt.client as mqtt
import logging
import simplejson as json
import asyncio

logger = logging.getLogger(__name__)


class StoreDummy:
    mqqt_client: mqtt.Client
    store: Store
    loop: asyncio.AbstractEventLoop

    def __init__(self):
        self.mqtt_client = mqtt.Client()
        self.mqtt_client.on_connect = self.on_connect
        self.mqtt_client.on_message = self.on_message
        self.mqtt_client.on_disconnect = self.on_disconnect
        self.store = Store('dummy_store')
        self.mqtt_client.connect("localhost")
        self.loop = asyncio.get_event_loop()

    def run(self):
        self.mqtt_client.loop_forever()

    def on_connect(self, client: mqtt.Client, userdata, flags, rc):
        logger.info("Connected")
        client.subscribe("test/store/#")

    def on_disconnect(self, client, userdata, rc):
        pass

    def on_message(self, client: mqtt.Client, userdata, msg):
        logger.info("Got {} on {}".format(msg.payload, msg.topic))
        tokens = msg.topic.split('/')

        if tokens[0] == "test" and tokens[1] == "store":
            if tokens[2] == "merchant_order":
                logger.info("Got merchant order")
                try:
                    self.loop.run_until_complete(
                        self.store.merchant_order_request(**json.loads(msg.payload))
                    )
                except Exception:
                    traceback.print_exc()



if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    store_dummuy = StoreDummy()
    store_dummuy.run()





