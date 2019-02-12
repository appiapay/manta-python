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

import asyncio
from dataclasses import dataclass
import logging

import pytest
import requests

from manta.messages import PaymentRequestEnvelope, Status
from manta.wallet import Wallet

STORE_URL = "http://localhost:8080/"
PP_HOST = "http://localhost:8081"


@pytest.mark.timeout(2)
@pytest.mark.asyncio
async def test_connect():
    wallet = Wallet.factory('manta://localhost/123')
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
    async def test_get_payment_request(self, session_data):
        r = requests.post(STORE_URL + "merchant_order", json={"amount": "10", "fiat": "EUR"})
        logging.info(r)
        ack_message = r.json()
        url = ack_message['url']
        logging.info(url)
        wallet = Wallet.factory(url)

        envelope = await wallet.get_payment_request('NANO')
        self.pr = envelope.unpack()

        assert 10 == self.pr.amount
        assert "EUR" == self.pr.fiat_currency

        session_data.wallet = wallet
        session_data.envelope = envelope

    @pytest.mark.asyncio
    async def test_send_payment(self, session_data):
        # noinspection PyUnresolvedReferences
        wallet = session_data.wallet

        await wallet.send_payment(crypto_currency="NANO", transaction_hash="myhash")
        ack = await wallet.acks.get()

        assert Status.PENDING == ack.status

    @pytest.mark.asyncio
    async def test_ack_on_confirmation(self, session_data):
        # noinspection PyUnresolvedReferences
        wallet = session_data.wallet

        requests.post(PP_HOST + "/confirm",
                      json={'session_id': wallet.session_id})

        ack = await wallet.acks.get()

        assert Status.PAID == ack.status
