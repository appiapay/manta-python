from manta.messages import AckMessage
from manta.storelib import Store
import simplejson as json
import pytest
import logging

#logging.basicConfig(level=logging.INFO)

@pytest.mark.timeout(2)
@pytest.mark.asyncio
async def test_connect():
    store = Store('device1')
    await store.connect()
    store.close()


@pytest.mark.timeout(2)
@pytest.mark.asyncio
async def test_generate_payment_request():
    store = Store('device1')
    url = await store.generate_payment_request(amount=10, fiat='eur')
    assert url.startswith("manta://")
    store.close()


@pytest.mark.timeout(5)
@pytest.mark.asyncio
async def test_ack(caplog):
    caplog.set_level(logging.INFO)

    store = Store('device1')
    ack_message: AckMessage = None
    session_id: str = None

    url = await store.generate_payment_request(amount=10, fiat='eur')

    ack_request = {
        "session_id": store.session_id,
        "status": "pending",
        "transaction_hash": "txhash",
        "txid":"0"
    }

    # store.loop.call_soon_threadsafe(
    #     store.mqtt_client.publish,
    #     "test/ack",
    #     json.dumps(ack_request)
    # )
    store.mqtt_client.publish("test/ack", json.dumps(ack_request))

    ack_message = await store.acks.get()

    assert "pending" == ack_message.status

