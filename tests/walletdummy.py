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

import traceback
from typing import Optional, List

import nano
import argparse
import configparser

from cryptography.x509 import NameOID

from manta.wallet import Wallet
from aiohttp import web
# from aiohttp_swagger import *
import logging
import os
import sys
import asyncio
from concurrent.futures._base import TimeoutError
from manta.messages import verify_chain, Destination, PaymentRequestEnvelope
import inquirer

# sys.path.append('.')

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


async def get_payment_request(wallet: Wallet, crypto_currency: str = 'all') -> PaymentRequestEnvelope:
    try:
        envelope = await wallet.get_payment_request(crypto_currency)
    except TimeoutError as e:
        if ONCE:
            print("Timeout exception in waiting for payment")
            sys.exit(1)
        else:
            raise e

    return envelope


def verify_envelope(envelope: PaymentRequestEnvelope, certificate, ca_certificate) -> bool:
    verified = False

    if ca_certificate:
        path = verify_chain(certificate, ca_certificate)

        if path:
            if envelope.verify(certificate):
                verified = True
                logger.info("Verified Request")
                logger.info("Certificate issued to {}".format(
                    certificate.subject.get_attributes_for_oid(NameOID.COMMON_NAME)[0].value))
            else:
                logger.error("Invalid Signature")
        else:
            logger.error("Invalid Certification Path")

    return verified


async def get_payment(url: str,
                      interactive: bool,
                      nano_wallet: str = None,
                      account: str = None,
                      ca_certificate: str = None):
    wallet = Wallet.factory(url)

    envelope = await get_payment_request(wallet)

    verified = False
    certificate = None

    if ca_certificate:
        certificate = await wallet.get_certificate()

        verified = verify_envelope(envelope, certificate, ca_certificate)

    pr = envelope.unpack()

    logger.info("Payment request: {}".format(pr))

    options = [x for x in pr.supported_cryptos]

    questions = [inquirer.List('crypto',
                               message=' What crypto you want to pay with?',
                               choices=options)]

    if interactive:
        answers = inquirer.prompt(questions)

        chosen_crypto = answers['crypto']

        # Check if we have already the destination
        destination = pr.get_destination(chosen_crypto)

        # Otherwise ask payment provider
        if not destination:
            logger.info('Requesting payment request for {}'.format(chosen_crypto))
            envelope = await get_payment_request(wallet, chosen_crypto)
            verified = False

            if ca_certificate:
                verified = verify_envelope(envelope, certificate, ca_certificate)

            pr = envelope.unpack()
            logger.info("Payment request: {}".format(pr))

            destination = pr.get_destination(chosen_crypto)

        if answers['crypto'] == 'NANO':
            rpc = nano.rpc.Client(host="http://localhost:7076")
            balance = rpc.account_balance(account=account)
            print()
            print("Actual balance: {}".format(
                str(nano.convert(from_unit="raw", to_unit="XRB", value=balance['balance']))
            ))

            if not verified:
                print("WARNING!!!! THIS IS NOT VERIFIED REQUEST")

            destination = pr.get_destination('NANO')

            if query_yes_no("Pay {} {} ({} {}) to {}".format(destination.amount,
                                                             destination.crypto_currency,
                                                             pr.amount,
                                                             pr.fiat_currency,
                                                             pr.merchant)):
                amount = int(nano.convert(from_unit='XRB', to_unit="raw", value=destination.amount))

                print(amount)

                block = rpc.send(wallet=nano_wallet,
                                 source=account,
                                 destination=destination.destination_address,
                                 amount=amount)

                await wallet.send_payment(transaction_hash=block, crypto_currency='NANO')
        elif answers['crypto'] == 'TESTCOIN':
            destination = pr.get_destination('TESTCOIN')
            await wallet.send_payment(transaction_hash='test_hash', crypto_currency='TESTCOIN')
        else:
            print("Not supported!")
            sys.exit()

    else:
        await wallet.send_payment("myhash", pr.destinations[0].crypto_currency)

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
default = config['DEFAULT']

parser = argparse.ArgumentParser(description="Wallet Dummy for Testing")
parser.add_argument('url', metavar="url", type=str, nargs="?")
parser.add_argument('-i', '--interactive', action='store_true', default=default.get('interactive', False))
parser.add_argument('--wallet', type=str, default=default.get('wallet', None))
parser.add_argument('--account', type=str, default=default.get('account', None))
parser.add_argument('--certificate', type=str, default=default.get('certificate', None))

ns = parser.parse_args()

print(ns)

if len([x for x in (ns.wallet, ns.account) if x is not None]) == 1:
    parser.error("--wallet and --account must be given together")

if ns.url:
    ONCE = True
    loop = asyncio.get_event_loop()

    loop.run_until_complete(get_payment(url=ns.url,
                                        interactive=ns.interactive,
                                        nano_wallet=ns.wallet,
                                        account=ns.account,
                                        ca_certificate=ns.certificate))

else:
    app.add_routes(routes)
    # swagger_file = os.path.join(os.path.dirname(__file__), 'swagger/wallet.yaml')
    # setup_swagger(app, swagger_from_file=swagger_file)
    web.run_app(app, port=8082)
