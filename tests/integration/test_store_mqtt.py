# Manta Python
# Manta Protocol Implementation for Python
# Copyright (C) 2018-2019 Alessandro Viganò

import pytest

from manta.messages import Status
from manta.store import Store

# logging.basicConfig(level=logging.INFO)


@pytest.fixture
async def store(broker) -> Store:
    _, host, port, _ = broker
    return Store('device1', host=host, port=port)


@pytest.mark.timeout(2)
@pytest.mark.asyncio
async def test_connect(store):
    # noinspection PyUnresolvedReferences
    await store.connect()
    store.close()


@pytest.mark.timeout(2)
@pytest.mark.asyncio
async def test_generate_payment_request(store, dummy_payproc):
    # noinspection PyUnresolvedReferences
    ack = await store.merchant_order_request(amount=10, fiat='eur')
    assert ack.url.startswith("manta://")


# noinspection PyUnresolvedReferences
@pytest.mark.timeout(5)
@pytest.mark.asyncio
async def test_ack(store, dummy_wallet, dummy_payproc, web_post):

    ack = await store.merchant_order_request(amount=10, fiat='eur')
    if dummy_wallet.url:
        web_post(dummy_wallet.url + "/scan", json={"url": ack.url})
    else:
        await dummy_wallet.pay(url=ack.url)
    ack_message = await store.acks.get()

    assert Status.PENDING == ack_message.status


@pytest.mark.timeout(5)
@pytest.mark.asyncio
# noinspection PyUnresolvedReferences
async def test_ack_paid(store, dummy_wallet, dummy_payproc, web_post):
    await test_ack(store, dummy_wallet, dummy_payproc, web_post)

    if dummy_payproc.url:
        web_post(dummy_payproc.url + "/confirm",
                 json={'session_id': store.session_id})
    else:
        dummy_payproc.manta.confirm(store.session_id)

    ack_message = await store.acks.get()

    assert Status.PAID == ack_message.status


@pytest.mark.timeout(5)
@pytest.mark.asyncio
# noinspection PyUnresolvedReferences
async def test_store_complete_session(store, dummy_wallet, dummy_payproc,
                                      web_post):
    ack = await store.merchant_order_request(amount=10, fiat='eur')
    await dummy_wallet.pay(url=ack.url)
    dummy_payproc.manta.confirm(dummy_wallet.manta.session_id)
    while True:
        ack = await store.acks.get()
        if ack.status is Status.PAID:
            break
    assert ack.status is Status.PAID
