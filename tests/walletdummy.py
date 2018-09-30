import traceback
import nano
import argparse
import configparser

from manta.wallet import Wallet
from aiohttp import web
# from aiohttp_swagger import *
import logging
import os
import sys
import asyncio
from concurrent.futures._base import TimeoutError

#sys.path.append('.')

ONCE = False

logger = logging.getLogger(__name__)
routes = web.RouteTableDef()
app = web.Application()




def query_yes_no(question, default="yes"):
    """Ask a yes/no question via raw_input() and return their answer.

    "question" is a string that is presented to the user.
    "default" is the presumed answer if the user just hits <Enter>.
        It must be "yes" (the default), "no" or None (meaning
        an answer is required of the user).

    The "answer" return value is True for "yes" or False for "no".
    """
    valid = {"yes": True, "y": True, "ye": True,
             "no": False, "n": False}
    if default is None:
        prompt = " [y/n] "
    elif default == "yes":
        prompt = " [Y/n] "
    elif default == "no":
        prompt = " [y/N] "
    else:
        raise ValueError("invalid default answer: '%s'" % default)

    while True:
        sys.stdout.write(question + prompt)
        choice = input().lower()
        if default is not None and choice == '':
            return valid[default]
        elif choice in valid:
            return valid[choice]
        else:
            sys.stdout.write("Please respond with 'yes' or 'no' "
                             "(or 'y' or 'n').\n")


async def get_payment(url: str, nano_wallet: str = None, account: str = None):
    wallet = Wallet.factory(url, "file")

    try:
        envelope = await wallet.get_payment_request()
    except TimeoutError as e:
        if ONCE:
            print("Timeout exception in waiting for payment")
            sys.exit(1)
        else:
            raise(e)

    pr = envelope.unpack()

    logger.info("Payment request: {}".format(pr))

    if nano_wallet:
        rpc = nano.rpc.Client(host="http://localhost:7076")
        balance = rpc.account_balance(account=account)
        print()
        print("Actual balance: {}".format(
            str(nano.convert(from_unit="raw", to_unit="XRB", value=balance['balance']))
        ))
        if query_yes_no("Pay {} {} ({} {}) to {}".format(pr.destinations[0].amount,
                                                         pr.destinations[0].crypto_currency,
                                                         pr.amount,
                                                         pr.fiat_currency,
                                                         pr.merchant)):
            amount = int(nano.convert(from_unit='XRB', to_unit="raw", value=pr.destinations[0].amount))

            print(amount)

            block = rpc.send(wallet=nano_wallet,
                             source=account,
                             destination=pr.destinations[0].destination_address,
                             amount=amount)

            wallet.send_payment(transaction_hash=block, crypto_currency='NANO')

    else:
        wallet.send_payment("myhash", pr.destinations[0].crypto_currency)

    ack = await wallet.acks.get()
    print(ack)


@routes.post("/scan")
async def scan(request: web.Request):
    try:
        json = await request.json()
        logger.info("Got scan request for {}".format(json['url']))
        await get_payment(json['url'])

        return web.json_response("ok")

    except Exception:
        traceback.print_exc()
        raise web.HTTPInternalServerError()


logging.basicConfig(level=logging.INFO)

config = configparser.ConfigParser()

folder = os.path.dirname(os.path.realpath(__file__))

file = os.path.join(folder, 'walletdummy.conf')

config.read(file)
default=config['DEFAULT']

parser = argparse.ArgumentParser(description="Wallet Dummy for Testing")
parser.add_argument('url', metavar="url", type=str, nargs="?")
parser.add_argument('--wallet', type=str, default=default.get('wallet', None))
parser.add_argument('--account', type=str, default=default.get('account', None))

ns = parser.parse_args()

print(ns)

if len([x for x in (ns.wallet, ns.account) if x is not None]) == 1:
    parser.error("--wallet and --account must be given together")

if ns.url:
    ONCE = True
    loop = asyncio.get_event_loop()

    loop.run_until_complete(get_payment(ns.url, ns.wallet, ns.account))

else:
    app.add_routes(routes)
    #swagger_file = os.path.join(os.path.dirname(__file__), 'swagger/wallet.yaml')
    #setup_swagger(app, swagger_from_file=swagger_file)
    web.run_app(app, port=8082)
