# Manta Python
# Manta Protocol Implementation for Python
# Copyright (C) 2018-2019 Alessandro Viganò

import logging
import time
from threading import Timer

import paho.mqtt.client as mqtt

from manta.messages import AckMessage, Status

logger = logging.getLogger(__name__)

WAITING_INTERVAL = 4


def on_connect(client: mqtt.Client, userdata, flags, rc):
    logger.info("Connected")
    client.subscribe("acks/#")


def on_message(client: mqtt.Client, userdata, msg: mqtt.MQTTMessage):
    ack: AckMessage = AckMessage.from_json(msg.payload)
    tokens = msg.topic.split('/')
    session_id = tokens[1]

    if ack.status == Status.NEW:
        new_ack = AckMessage(txid=ack.txid,
                             status=Status.PENDING,
                             transaction_currency="NANO",
                             transaction_hash="B50DB45966850AD4B11ECFDD8AE0A7AD97DF74864631D8C1495E46DDDFC1802A")
        logging.info("Waiting...")

        time.sleep(WAITING_INTERVAL)

        logging.info("Sending first ack...")

        client.publish("acks/{}".format(session_id), new_ack.to_json())

        new_ack.status = Status.PAID

        logging.info("Waiting...")

        def pub_second_ack():
            logging.info("Sending second ack...")
            client.publish("acks/{}".format(session_id), new_ack.to_json())

        t = Timer(WAITING_INTERVAL, pub_second_ack)
        t.start()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    client = mqtt.Client(protocol=mqtt.MQTTv31)

    client.on_connect = on_connect
    client.on_message = on_message

    client.connect("localhost")
    client.loop_forever()
