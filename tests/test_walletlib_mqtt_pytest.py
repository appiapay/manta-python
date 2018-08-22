from manta.walletlib import Wallet
import pytest
import logging
import simplejson as json
import requests


@pytest.mark.timeout(2)
@pytest.mark.asyncio
async def test_connect():
    wallet = Wallet.factory('manta://localhost/123', 'file')
    await wallet.connect()
    wallet.close()


@pytest.mark.asyncio
async def test_get_payment_request():
    r = requests.post("http://localhost:8080/merchant_order",json={"amount": 10, "fiat": "eur"})
    url = r.json()
    logging.info(url)
    wallet = Wallet.factory(url, "filename")

    envelope = await wallet.get_payment_request('btc')






