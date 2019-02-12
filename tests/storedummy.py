# Manta Python
# Manta Protocol Implementation for Python
# Copyright (C) 2018 Alessandro Viganò
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

from decimal import Decimal
import logging
import traceback

from aiohttp import web

from manta.store import Store


logger = logging.getLogger(__name__)
routes = web.RouteTableDef()
store = Store('dummy_store')


@routes.post("/merchant_order")
async def merchant_order(request: web.Request):
    try:
        json = await request.json()
        logger.info("New http requets: %s" % json)
        json['amount'] = Decimal(json['amount'])

        reply = await store.merchant_order_request(**json)


        return web.Response(body=reply.to_json(), content_type="application/json")

    except Exception:
        traceback.print_exc()
        raise web.HTTPInternalServerError()


logging.basicConfig(level=logging.INFO)
app = web.Application()
app.add_routes(routes)
web.run_app(app, port=8080)
