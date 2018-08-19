import pytest
from unittest.mock import MagicMock
from typing import NamedTuple, Dict
from callee import Matcher
import paho.mqtt.client as mqtt
import simplejson as json


def is_namedtuple_instance(x):
    t = type(x)
    b = t.__bases__
    if len(b) != 1 or b[0] != tuple: return False
    f = getattr(t, '_fields', None)
    if not isinstance(f, tuple): return False
    return all(type(n)==str for n in f)

class MQTTMock(MagicMock):
    def push(self, topic, payload):
        self.on_message(self, None, MQTTMessage(topic, payload))


class MQTTMessage(NamedTuple):
    topic: any
    payload: any


class JsonEqual(Matcher):
    obj: Dict

    def __init__(self, d):
        if is_namedtuple_instance(d):
            self.obj = json.loads(json.dumps(d))
        else:
            self.obj = d

    def match(self, value):
        actual = json.loads(value)
        assert self.obj == actual
        return True


@pytest.fixture
def mock_mqtt(monkeypatch):
    mock = MQTTMock()
    mock.return_value = mock
    mock.connect.side_effect = lambda host: mock.on_connect(mock, None, None, None)

    monkeypatch.setattr(mqtt, 'Client', mock)
    return mock
