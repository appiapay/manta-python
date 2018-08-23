import traceback

from manta.wallet import Wallet
from aiohttp import web
import logging

logger = logging.getLogger(__name__)
routes = web.RouteTableDef()
app = web.Application()


@routes.post("/scan")
async def scan(request: web.Request):
    try:
        json = await request.json()
        logger.info("Got scan request for {}".format(json['url']))
        wallet = Wallet.factory(json['url'], "file")

        if not wallet:
            raise web.HTTPInternalServerError()

        envelope = await wallet.get_payment_request()
        pr = envelope.unpack()

        logger.info("Payment request: {}".format(pr))

        wallet.send_payment("myhash", pr.destinations[0].crypto_currency)

        return web.json_response("ok")

    except Exception:
        traceback.print_exc()
        raise web.HTTPInternalServerError()


logging.basicConfig(level=logging.INFO)

app.add_routes(routes)
web.run_app(app, port=8082)
