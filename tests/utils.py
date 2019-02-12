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

import difflib
import pprint
from typing import NamedTuple, Dict
from unittest.mock import MagicMock

from callee import Matcher
import cattr
import pytest
import paho.mqtt.client as mqtt
import simplejson as json

from manta.messages import Message


def is_namedtuple_instance(x):
    t = type(x)
    b = t.__bases__
    if len(b) != 1 or b[0] != tuple: return False
    f = getattr(t, '_fields', None)
    if not isinstance(f, tuple): return False
    return all(type(n) == str for n in f)


class MQTTMock(MagicMock):
    def push(self, topic, payload):
        self.on_message(self, None, MQTTMessage(topic, payload))


class MQTTMessage(NamedTuple):
    topic: any
    payload: any


def compare_dicts(d1, d2):
    return ('\n' + '\n'.join(difflib.ndiff(
        pprint.pformat(d1).splitlines(),
        pprint.pformat(d2).splitlines())))


class JsonContains(Matcher):
    obj: Dict

    def __init__(self, d):
        if isinstance(d, Message):
            self.obj = cattr.unstructure(d)
        else:
            self.obj = d

    def match(self, value):
        actual = json.loads(value)
        # check if subset
        assert self.obj.items() <= actual.items(), compare_dicts(self.obj, actual)
        # assert self.obj == actual
        return True


@pytest.fixture
def mock_mqtt(monkeypatch):
    mock = MQTTMock()
    mock.return_value = mock

    def connect(host, port=1883):
        nonlocal mock
        mock.on_connect(mock, None, None, None)

    mock.connect.side_effect = connect

    monkeypatch.setattr(mqtt, 'Client', mock)
    return mock
