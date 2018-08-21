from manta.walletlib import Wallet
import pytest


@pytest.mark.timeout(2)
@pytest.mark.asyncio
async def test_connect():
    store = Wallet.factory('manta://localhost/123', 'file')
    await store.connect()




