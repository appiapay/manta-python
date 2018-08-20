from typing import NamedTuple
from unittest.mock import MagicMock

import re
import paho.mqtt.client as mqtt
import pytest
import simplejson as json

from manta.storelib import Store
from manta.messages import MerchantOrderReplyMessage, AckMessage
import callee
from tests.utils import MQTTMessage, mock_mqtt

BASE64PATTERN = "(?:[A-Za-z0-9+/]{4})*(?:[A-Za-z0-9+/]{2}==|[A-Za-z0-9+/]{3}=)?"
BASE64PATTERNSAFE = "(?:[A-Za-z0-9_-]{4})*(?:[A-Za-z0-9_-]{2}==|[A-Za-z0-9_-]{3}=)?"

def reply(topic, payload):
    decoded = json.loads(payload)
    tokens = topic.split("/")
    device = tokens[1]

    r = MerchantOrderReplyMessage(
        status=200,
        session_id=decoded['session_id'],
        url="manta://testpp.com/{}".format(decoded['session_id'])
    )

    return ("generate_payment_request/{}/reply".format(device), json.dumps(r))

@pytest.mark.timeout(2)
@pytest.mark.asyncio
async def test_connect(mock_mqtt):
    store = Store('device1')
    await store.connect()


@pytest.mark.timeout(2)
def test_generate_payment_request(mock_mqtt):
    store = Store('device1')

    def se(topic, payload):
        nonlocal mock_mqtt

        print(topic)

        if topic == "generate_payment_request/device1/request":
            mock_mqtt.push(*reply(topic, payload))

    mock_mqtt.publish.side_effect = se

    url = store.generate_payment_request(amount=10, fiat='eur')
    mock_mqtt.subscribe.assert_called_with("generate_payment_request/device1/reply")
    assert re.match("^manta:\/\/testpp\.com\/" + BASE64PATTERNSAFE + "$", url)


def test_ack(mock_mqtt):
    store = Store('device1')
    ack_message: AckMessage = None
    session_id: str = None

    def on_ack (session: str, ack: AckMessage):
        nonlocal ack_message, session_id
        ack_message = ack
        session_id = session

    store.ack_callback = on_ack

    expected_ack = AckMessage (txid='1234', transaction_hash="hash_1234", status="pending" )

    mock_mqtt.push('acks/123', json.dumps(expected_ack))

    assert "123" == session_id
    assert expected_ack == ack_message