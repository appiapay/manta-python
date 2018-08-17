from typing import NamedTuple
from unittest.mock import MagicMock

import re
import paho.mqtt.client as mqtt
import pytest
import simplejson as json

from manta.storelib import Store
from manta.messages import GeneratePaymentReplyMessage, AckMessage

BASE64PATTERN = "(?:[A-Za-z0-9+/]{4})*(?:[A-Za-z0-9+/]{2}==|[A-Za-z0-9+/]{3}=)?"

class MQTTMock(MagicMock):
    def push(self, topic, payload):
        self.on_message(self, None, MQTTMessage(topic, payload))

class MQTTMessage(NamedTuple):
    topic: any
    payload: any


def reply(topic, payload):
    decoded = json.loads(payload)
    tokens = topic.split("/")
    device = tokens[1]

    r = GeneratePaymentReplyMessage(
        status=200,
        session_id=decoded['session_id'],
        url="manta://testpp.com/{}".format(decoded['session_id'])
    )

    return MQTTMessage(topic="generate_payment_request/{}/reply".format(device), payload=json.dumps(r))


@pytest.fixture
def mock_mqtt(monkeypatch):
    mock = MQTTMock()
    mock.return_value = mock
    mock.connect.side_effect = lambda host: mock.on_connect(mock, None, None, None)

    monkeypatch.setattr(mqtt, 'Client', mock)
    return mock


@pytest.mark.timeout(2)
@pytest.mark.asyncio
async def test_connect(mock_mqtt):
    store = Store('device1')
    await store.connect()


@pytest.mark.timeout(2)
def test_generate_payment_request(mock_mqtt):
    store = Store('device1')
    mock_mqtt.publish.side_effect = lambda topic, payload: mock_mqtt.on_message(mock_mqtt, None, reply(topic, payload))

    url = store.generate_payment_request(amount=10, fiat='eur')
    assert re.match("^manta:\/\/testpp\.com\/" + BASE64PATTERN + "$", url)


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