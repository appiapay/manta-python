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

import re

import pytest

from manta.store import Store
from manta.messages import AckMessage, Status, MerchantOrderRequestMessage

BASE64PATTERN = "(?:[A-Za-z0-9+/]{4})*(?:[A-Za-z0-9+/]{2}==|[A-Za-z0-9+/]{3}=)?"
BASE64PATTERNSAFE = "(?:[A-Za-z0-9_-]{4})*(?:[A-Za-z0-9_-]{2}==|[A-Za-z0-9_-]{3}=)?"


def reply(topic, payload):
    order = MerchantOrderRequestMessage.from_json(payload)
    tokens = topic.split("/")
    device = tokens[1]

    r = AckMessage(
        txid="0",
        status=Status.NEW,
        url="manta://testpp.com/{}".format(order.session_id)
    )

    return "acks/{}".format(device), r.to_json()


@pytest.mark.timeout(2)
@pytest.mark.asyncio
async def test_connect(mock_mqtt):
    store = Store("device1")
    await store.connect()


@pytest.mark.asyncio
async def test_generate_payment_request(mock_mqtt):
    store = Store('device1')

    def se(topic, payload):
        nonlocal mock_mqtt

        if topic == "merchant_order_request/device1":
            order = MerchantOrderRequestMessage.from_json(payload)
            reply = AckMessage(
                status=Status.NEW,
                url="manta://testpp.com/{}".format(order.session_id),
                txid="0"
            )

            topic = "acks/{}".format(order.session_id)

            mock_mqtt.push(topic, reply.to_json())

    mock_mqtt.publish.side_effect = se

    ack = await store.merchant_order_request(amount=10, fiat='eur')
    mock_mqtt.subscribe.assert_any_call("acks/{}".format(store.session_id))
    assert re.match("^manta:\/\/testpp\.com\/" + BASE64PATTERNSAFE + "$", ack.url)


@pytest.mark.asyncio
async def test_ack(mock_mqtt):
    store = Store('device1')
    ack_message: AckMessage = None

    expected_ack = AckMessage(txid='1234', transaction_hash="hash_1234", status=Status.PENDING)

    mock_mqtt.push('acks/123', expected_ack.to_json())

    ack_message = await store.acks.get()
    assert expected_ack == ack_message
