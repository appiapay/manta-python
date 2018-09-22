from dataclasses import dataclass

from manta.messages import PaymentRequestEnvelope, Status
from manta.wallet import Wallet
import pytest
import logging
import asyncio
import requests

STORE_URL = "http://localhost:8080/"
PP_HOST = "http://localhost:8081"


@pytest.mark.timeout(2)
@pytest.mark.asyncio
async def test_connect():
    wallet = Wallet.factory('manta://localhost/123', 'file')
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
        wallet = Wallet.factory(url, "filename")

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

        wallet.send_payment(crypto_currency="NANO", transaction_hash="myhash")
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
