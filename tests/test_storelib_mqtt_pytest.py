from manta.messages import AckMessage
from manta.storelib import Store
import simplejson as json
import pytest
import logging


@pytest.mark.timeout(2)
@pytest.mark.asyncio
async def test_connect():
    store = Store('device1')
    await store.connect()
    store.close()


@pytest.mark.timeout(2)
def test_generate_payment_request():
    store = Store('device1')
    url = store.generate_payment_request(amount=10, fiat='eur')
    assert url.startswith("manta://")
    store.close()


@pytest.mark.timeout(5)
def test_ack():
    store = Store('device1')
    ack_message: AckMessage = None
    session_id: str = None

    def on_ack (session: str, ack: AckMessage):
        nonlocal ack_message, session_id
        ack_message = ack
        session_id = session

    store.ack_callback = on_ack
    url = store.generate_payment_request(amount=10, fiat='eur')

    ack_request = {
        "session_id": store.session_id,
        "status": "pending",
        "transaction_hash": "txhash",
        "txid":"0"
    }

    store.mqtt_client.publish("test/ack", json.dumps(ack_request))

    while ack_message is None:
        pass

    assert store.session_id == session_id
    assert "pending" == ack_message.status
