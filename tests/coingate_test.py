import unittest
import responses
from coingate import Coingate

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


