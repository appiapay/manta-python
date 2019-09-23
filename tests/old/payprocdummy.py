# Manta Python
# Manta Protocol Implementation for Python
# Copyright (C) 2018-2019 Alessandro Viganò

from decimal import Decimal
import logging

from aiohttp import web

from manta.messages import MerchantOrderRequestMessage, Destination, Merchant
from manta.payproc import PayProc


logger = logging.getLogger(__name__)

KEYFILE = "certificates/root/keys/www.brainblocks.com.key"
DESTINATIONS = [
    Destination(
        amount=Decimal("0.01"),
        destination_address="xrb_3d1ab61eswzsgx5arwqc3gw8xjcsxd7a5egtr69jixa5it9yu9fzct9nyjyx",
        crypto_currency="NANO"
    ),

]

MERCHANT = Merchant(
    name="Merchant 1",
    address="5th Avenue"
)


def get_destinations(application_id, merchant_order: MerchantOrderRequestMessage):
    if merchant_order.crypto_currency:
        destination = next(x for x in DESTINATIONS
                           if x.crypto_currency == merchant_order.crypto_currency)
        return [destination]
    else:
        return DESTINATIONS


pp = PayProc(KEYFILE)
pp.get_merchant = lambda x: MERCHANT
pp.get_destinations = get_destinations
pp.get_supported_cryptos = lambda device, payment_request: {'btc', 'xmr', 'nano'}

routes = web.RouteTableDef()


@routes.post("/confirm")
async def merchant_order(request: web.Request):
    try:
        logger.info("Got confirm request")
        json = await request.json()
        pp.confirm(json['session_id'])

        return web.json_response("ok")

    except Exception:
        raise web.HTTPInternalServerError()


logging.basicConfig(level=logging.INFO)
app = web.Application()
app.add_routes(routes)
pp.run()
web.run_app(app, port=8081)
