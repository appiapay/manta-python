# Manta Python
# Manta Protocol Implementation for Python
# Copyright (C) 2018-2019 Alessandro Viganò

import asyncio
from dataclasses import dataclass
from decimal import Decimal
import logging

import pytest

from manta.messages import PaymentRequestEnvelope, Status
from manta.wallet import Wallet


@pytest.mark.timeout(2)
@pytest.mark.asyncio
async def test_connect(broker):
    _, host, port, _ = broker
    wallet = Wallet.factory('manta://localhost:{}/123'.format(port))
    await wallet.connect()
    wallet.close()


# See https://github.com/pytest-dev/pytest-asyncio/issues/68
@pytest.yield_fixture(scope="class")
def event_loop():
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="class")
async def session_data():
    @dataclass
    class Session:
        wallet: Wallet = None
        envelope: PaymentRequestEnvelope = None

    session = Session
    return session


@pytest.mark.incremental
class TestWallet:

    @pytest.mark.asyncio
    async def test_get_payment_request(self, dummy_payproc, dummy_store,
                                       web_post):
        if dummy_store.url:
            r = await web_post(dummy_store.url + "/merchant_order",
                               json={"amount": "10", "fiat": "EUR"})
            logging.info(r)
            ack_message = r.json()
            url = ack_message['url']
        else:
            ack_message = await dummy_store.manta.merchant_order_request(
                amount=Decimal("10"), fiat='EUR')
            url = ack_message.url
        logging.info(url)
        wallet = Wallet.factory(url)

        envelope = await wallet.get_payment_request('NANO')
        self.pr = envelope.unpack()

        assert 10 == self.pr.amount
        assert "EUR" == self.pr.fiat_currency
        return wallet

    @pytest.mark.asyncio
    async def test_send_payment(self, dummy_payproc, dummy_store, web_post):
        # noinspection PyUnresolvedReferences

        wallet = await self.test_get_payment_request(dummy_payproc,
                                                     dummy_store, web_post)

        await wallet.send_payment(crypto_currency="NANO", transaction_hash="myhash")

        ack = await wallet.acks.get()

        assert Status.PENDING == ack.status
        return wallet

    @pytest.mark.asyncio
    async def test_ack_on_confirmation(self, session_data, dummy_payproc,
                                       dummy_store, web_post):
        # noinspection PyUnresolvedReferences
        wallet = await self.test_send_payment(dummy_payproc, dummy_store,
                                              web_post)

        dummy_payproc.manta.confirm(wallet.session_id)

        if dummy_payproc.url:
            web_post(dummy_payproc.url + "/confirm",
                     json={'session_id': wallet.session_id})

        ack = await wallet.acks.get()

        assert Status.PAID == ack.status
