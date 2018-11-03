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

import unittest
import responses
from coingate import Coingate
from unittest.mock import MagicMock, patch

CREATE_ORDER_RESPONSE = """
{
  "id": 1195862,
  "status": "new",
  "price_currency": "USD",
  "price_amount": "2000.0",
  "receive_currency": "EUR",
  "receive_amount": "",
  "created_at": "2018-04-25T13:28:16+00:00",
  "order_id": "111",
  "payment_url": "https://coingate.com/invoice/6003de09-ee9a-4584-be0e-5c0c71c5e497",
  "token": "MVsgsjGXv-pRWMnZzsuD4B5xcdnj-w"
}
"""

CHECKOUT_RESPONSE = """
{
    "id": 1723,
    "order_id": "",
    "pay_amount": "0.000023",
    "pay_currency": "BTC",
    "payment_address": "2MzyF5xfYRAmHVPwG6YPRMY74dojhAVEtmm",
    "payment_url": "http://coingate.com/invoice/4949cf0a-fccb-4cc2-9342-7af1890cc664",
    "price_amount": "0.01",
    "price_currency": "USD",
    "receive_amount": "0.01",
    "receive_currency": "USD",
    "status": "pending",
    "created_at": "2018-05-04T21:46:07+00:00",
    "expire_at": "2018-05-04T22:11:58+00:00"
}
"""

PAYMENT_CALLBACK = {
    'id' : 343,
    'order_id' : 14037,
    'status' : 'paid',
    'price_amount' : 1050.99,
    'price_currency' : 'USD',
    'receive_amount' : 926.73,
    'receive_currency' : 'EUR',
    'pay_amount' : 4.81849315,
    'pay_currency' : 'BTC',
    'created_at' : '2014-11-03T13:07:28+00:00',
    'token' : 'ff7a7343-93bf-42b7-b82c-b38687081a4e',
}


class TestCoingate(unittest.TestCase):
    def setUp(self):
        self.coingate = Coingate()

    @responses.activate
    def test_create_order(self):

        responses.add(responses.POST, "https://api-sandbox.coingate.com/v2/orders",
                      body=CREATE_ORDER_RESPONSE,
                      content_type='application/json',
                      status=200)
        responses.add(responses.POST, "https://api-sandbox.coingate.com/v2/orders/1195862/checkout",
                      body=CHECKOUT_RESPONSE,
                      content_type='application/json',
                      status=200)

        amount, address= self.coingate.create_order("my_token", 10, 'eur', '1234')

        self.assertEqual("2MzyF5xfYRAmHVPwG6YPRMY74dojhAVEtmm", address)
        self.assertEqual(0.000023, amount)


class TestCoingateFlask(unittest.TestCase):
    def setUp(self):
        pass
        self.coingate = Coingate()
        self.coingate.app.config['TESTING'] = True
        self.client = self.coingate.app.test_client()
        self.mockPP = MagicMock()
        self.coingate.pp = self.mockPP

 #   @patch('paho.mqtt.client.Client')
    def test_change_status_paid(self):
        rv = self.client.post("/status-change", data=PAYMENT_CALLBACK)

        #See https://stackoverflow.com/questions/36067124/python-patch-mock-appears-to-be-called-but-assert-fails
        #mqtt_mock.return_value.publish.assert_called()
        self.mockPP.confirm.assert_called()
        self.mockPP.confirm.assert_called_with("14037")
        #self.assertEqual(200, rv.status_code)

    def test_change_status_pending(self):
        PAYMENT_CALLBACK['status'] = 'pending'
        rv = self.client.post("/status-change", data=PAYMENT_CALLBACK)
        self.mockPP.confirm.assert_not_called()

