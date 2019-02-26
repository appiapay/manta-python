# -*- coding: utf-8 -*-
# Manta Python
# Manta Protocol Implementation for Python
# Copyright (C) 2019 xxx
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

from __future__ import annotations

import logging
from threading import Timer
from typing import Awaitable

import aiohttp
import paho.mqtt.client as mqtt

from ..store import Store
from . import AppRunnerConfig
from .runner import AppRunner

logger = logging.getLogger(__name__)


def echo() -> mqtt.Client:
    """Returns an MQTT client configured as store echo."""

    import time

    from ..messages import AckMessage, Status

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
                                 transaction_hash="B50DB45966850AD4B11ECFDD8A"
                                 "E0A7AD97DF74864631D8C1495E46DDDFC1802A")
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

    client = mqtt.Client(protocol=mqtt.MQTTv31)

    client.on_connect = on_connect
    client.on_message = on_message
    return client


def dummy_store(runner: AppRunner) -> AppRunnerConfig:
    from decimal import Decimal

    assert runner.app_config is not None
    assert runner.app_config.store is not None

    from .config import DummyStoreConfig

    cfg: DummyStoreConfig = runner.app_config.store
    store = Store('dummy_store', host=runner.app_config.broker.host,
                  port=runner.app_config.broker.port)

    if cfg.web is not None and cfg.web.enable:
        routes = aiohttp.web.RouteTableDef()

        @routes.post("/merchant_order")
        async def merchant_order(request: aiohttp.web.Request):
            try:
                json = await request.json()
                logger.info("New http requets: %s" % json)
                json['amount'] = Decimal(json['amount'])

                reply = await store.merchant_order_request(**json)

                return aiohttp.web.Response(body=reply.to_json(),
                                            content_type="application/json")

            except Exception:
                logger.exception("Error during '/merchant_order' web endpoint")
                raise aiohttp.web.HTTPInternalServerError()

        more_params = dict(web_routes=routes,
                           allow_port_reallocation=cfg.web.allow_port_reallocation,
                           web_bind_address=cfg.web.bind_address,
                           web_bind_port=cfg.web.bind_port)
    else:
        more_params = {}

    def starter() -> Awaitable:
        return store.connect()

    def stopper() -> None:
        store.mqtt_client.loop_stop()

    return AppRunnerConfig(manta=store, starter=starter, stopper=stopper,
                           **more_params)
