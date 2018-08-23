from manta.messages import MerchantOrderRequestMessage, Destination
from manta.payproclib import PayProc
from aiohttp import web
import logging

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


pp = PayProc(KEYFILE)
pp.get_merchant = lambda x: "merchant1"
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
