# -*- coding: utf-8 -*-
# Manta Python
# Manta Protocol Implementation for Python
# Copyright (C) 2018-2019 Alessandro Viganò

from functools import partial
import logging
from typing import List

import aiohttp

from ..messages import MerchantOrderRequestMessage, Destination, Merchant
from ..payproc import PayProc
from . import AppRunnerConfig, config2msg
from .runner import AppRunner

logger = logging.getLogger(__name__)


def dummy_payproc(runner: AppRunner) -> AppRunnerConfig:
    assert runner.app_config is not None
    assert runner.app_config.payproc is not None

    from .config import DummyPayProcConfig

    cfg: DummyPayProcConfig = runner.app_config.payproc

    pp = PayProc(cfg.keyfile, cert_file=cfg.certfile, host=runner.app_config.broker.host,
                 port=runner.app_config.broker.port)
    merchant = config2msg(cfg.merchant, Merchant)
    destinations = [config2msg(d, Destination) for d in cfg.destinations]
    cryptos = set(cfg.supported_cryptos)
    pp.get_merchant = lambda x: merchant
    pp.get_destinations = partial(_get_destinations, destinations)
    pp.get_supported_cryptos = lambda device, payment_request: cryptos

    if cfg.web is not None and cfg.web.enable:
        routes = aiohttp.web.RouteTableDef()

        @routes.post("/confirm")
        async def merchant_order(request: aiohttp.web.Request):
            try:
                logger.info("Got confirm request")
                json = await request.json()
                pp.confirm(json['session_id'])

                return aiohttp.web.json_response("ok")

            except Exception:
                raise aiohttp.web.HTTPInternalServerError()

        more_params = dict(web_routes=routes,
                           allow_port_reallocation=cfg.web.allow_port_reallocation,
                           web_bind_address=cfg.web.bind_address,
                           web_bind_port=cfg.web.bind_port)
    else:
        more_params = {}

    def starter() -> bool:
        pp.run()
        return False

    def stopper() -> None:
        pp.mqtt_client.loop_stop()

    return AppRunnerConfig(manta=pp, starter=starter, stopper=stopper,
                           **more_params)


def _get_destinations(destinations: List[Destination], application_id,
                      merchant_order: MerchantOrderRequestMessage):
    if merchant_order.crypto_currency:
        destination = next(x for x in destinations
                           if x.crypto_currency == merchant_order.crypto_currency)
        return [destination]
    else:
        return destinations
