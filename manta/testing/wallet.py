# -*- coding: utf-8 -*-
# Manta Python
# Manta Protocol Implementation for Python
# Copyright (C) 2018-2019 Alessandro Viganò

from __future__ import annotations

from asyncio import TimeoutError
import logging
import sys

import aiohttp
from cryptography import x509
from cryptography.x509 import NameOID
import inquirer
import nano

from ..messages import (verify_chain, Destination,
                        PaymentRequestEnvelope, PaymentRequestMessage)
from ..wallet import Wallet
from . import AppRunnerConfig
from .runner import AppRunner

logger = logging.getLogger(__name__)


def dummy_wallet(runner: AppRunner) -> AppRunnerConfig:
    assert runner.app_config is not None
    assert runner.app_config.wallet is not None

    from .config import DummyWalletConfig

    cfg: DummyWalletConfig = runner.app_config.wallet
    if cfg.web is not None and cfg.web.enable:
        routes = aiohttp.web.RouteTableDef()

        @routes.post("/scan")
        async def scan(request: aiohttp.web.Request):
            try:
                json = await request.json()
                logger.info("Got scan request for {}".format(json['url']))
                await pay(json['url'])

                return aiohttp.web.json_response("ok")

            except Exception:
                logger.exception("Error while executing '/scan' web endpoint")
                raise aiohttp.web.HTTPInternalServerError()

        more_params = dict(web_routes=routes,
                           allow_port_reallocation=cfg.web.allow_port_reallocation,
                           web_bind_address=cfg.web.bind_address,
                           web_bind_port=cfg.web.bind_port)
    else:
        more_params = {}

    async def starter():
        nonlocal runner, cfg
        runner.pay = pay
        if cfg.url is not None:
            await pay(cfg.url, once=True)
            return True  # inform the runner that we want it to stop

    def pay(url: str, *args, **kwargs):
        nonlocal runner, cfg
        wallet = Wallet.factory(url)
        runner.manta = wallet
        kwargs['wallet'] = wallet
        kwargs.setdefault('interactive', cfg.interactive)
        kwargs.setdefault('account', cfg.account)
        kwargs.setdefault('ca_certificate', cfg.certificate)
        kwargs.setdefault('nano_wallet', cfg.wallet)
        return _get_payment(*args, **kwargs)

    def stopper():
        if isinstance(runner.manta, Wallet):
            runner.manta.mqtt_client.loop_stop()

    return AppRunnerConfig(starter=starter,  # type: ignore
                           stopper=stopper, **more_params)


async def _get_payment(url: str = None,
                       interactive: bool = False,
                       nano_wallet: str = None,
                       account: str = None,
                       ca_certificate: str = None,
                       wallet: Wallet = None,
                       once: bool = False):

    if wallet is None:
        assert url is not None
        wallet = Wallet.factory(url)

    assert wallet is not None
    try:
        envelope = await _get_payment_request(wallet, once=once)
    except TimeoutError as e:
        if once:
            return
        else:
            raise e

    certificate: x509.Certificate = None

    verified = False

    if ca_certificate:
        certificate = await wallet.get_certificate()
        verified = _verify_envelope(envelope, certificate, ca_certificate)

    payment_req = envelope.unpack()
    logger.info("Payment request: {}".format(payment_req))

    if interactive:
        await _interactive_payment(wallet, payment_req, nano_wallet=nano_wallet,
                                   account=account, certificate=certificate,
                                   ca_certificate=ca_certificate, once=once,
                                   verified=verified)
    else:
        await wallet.send_payment("myhash",
                                  payment_req.destinations[0].crypto_currency)

    ack = await wallet.acks.get()
    print(ack)


async def _get_payment_request(wallet: Wallet, crypto_currency: str = 'all',
                               once: bool = False) -> PaymentRequestEnvelope:
    try:
        envelope = await wallet.get_payment_request(crypto_currency)
    except TimeoutError as e:
        logger.error("Timeout exception in waiting for payment")
        raise e
    return envelope


async def _interactive_payment(wallet: Wallet, payment_req: PaymentRequestMessage,
                               nano_wallet: str = None, account: str = None,
                               certificate: x509.Certificate = None,
                               ca_certificate: str = None,
                               once: bool = False,
                               verified: bool = False):
    """Pay a ``PaymentRequestMessage`` interactively asking questions on
    ``sys.stdout`` and reading answers on ``sys.stdin``."""

    options = [x for x in payment_req.supported_cryptos]
    questions = [inquirer.List('crypto',
                               message=' What crypto you want to pay with?',
                               choices=options)]
    answers = inquirer.prompt(questions)
    chosen_crypto = answers['crypto']

    # Check if we have already the destination
    destination = payment_req.get_destination(chosen_crypto)

    # Otherwise ask payment provider
    if not destination:
        logger.info('Requesting payment request for {}'.format(chosen_crypto))
        try:
            envelope = await _get_payment_request(wallet, chosen_crypto, once=once)
        except TimeoutError as e:
            if once:
                return
            else:
                raise e

        verified = False

        if ca_certificate:
            verified = _verify_envelope(envelope, certificate,
                                        ca_certificate)

        # Double unpack, why?
        payment_req = envelope.unpack()
        logger.info("Payment request: {}".format(payment_req))
        destination = payment_req.get_destination(chosen_crypto)

    if answers['crypto'] == 'NANO':
        rpc = nano.rpc.Client(host="http://localhost:7076")
        balance = rpc.account_balance(account=account)
        print()
        print("Actual balance: {}".format(
            str(nano.convert(from_unit="raw", to_unit="XRB",
                             value=balance['balance']))
        ))

        if not verified:
            print("WARNING!!!! THIS IS NOT VERIFIED REQUEST")

        destination = payment_req.get_destination('NANO')

        assert isinstance(destination, Destination)
        if _query_yes_no("Pay {} {} ({} {}) to {}".format(
                destination.amount, destination.crypto_currency,
                payment_req.amount, payment_req.fiat_currency,
                payment_req.merchant)):
            amount = int(nano.convert(from_unit='XRB', to_unit="raw",
                                      value=destination.amount))

            print(amount)

            block = rpc.send(wallet=nano_wallet,
                             source=account,
                             destination=destination.destination_address,
                             amount=amount)

            await wallet.send_payment(transaction_hash=block,
                                      crypto_currency='NANO')
    elif answers['crypto'] == 'TESTCOIN':
        destination = payment_req.get_destination('TESTCOIN')
        await wallet.send_payment(transaction_hash='test_hash',
                                  crypto_currency='TESTCOIN')
    else:
        print("Not supported!")
        sys.exit()


def _query_yes_no(question, default="yes"):
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


def _verify_envelope(envelope: PaymentRequestEnvelope, certificate,
                     ca_certificate) -> bool:
    verified = False

    if ca_certificate:
        path = verify_chain(certificate, ca_certificate)

        if path:
            if envelope.verify(certificate):
                verified = True
                logger.info("Verified Request")
                logger.info("Certificate issued to {}".format(
                    certificate.subject.get_attributes_for_oid(
                        NameOID.COMMON_NAME)[0].value))
            else:
                logger.error("Invalid Signature")
        else:
            logger.error("Invalid Certification Path")

    return verified
