import unittest
import json
from unittest.mock import MagicMock, patch
from typing import Any, NamedTuple

from wallet import get_payment_request, verify_payment_request, on_message


class MQTT_Message(NamedTuple):
    topic: any
    payload: any


class TestWallet(unittest.TestCase):
    def test_get_payment_request(self):
        client = MagicMock()

        get_payment_request(client, 123)

        client.subscribe.assert_called_with('/payment_requests/123')

    def test_verify_payment_request(self):
        payment_request = r"""
{"message": "{\"name\": \"Nano Coffee Shop\", \"address\": \"Milano\", \"amount\": 100, \"dest_address\": \"xrb_1234\"}", "signature": "R1nNnvBY6MPxbIoCk7yjzcAjCCESr3gSwrQF87L2XWRWpvQoF08/RQW1nldEbnc5RNMhxIolSHpGxYPs1hP9wwmRwexRzep5EsqsbyGfhkyfr318kAjo+r1PoTX2u4jOgsMxKRu1h5ycI1qqd8fYJ1IfkcKc5AuKiJPI3IC4AFB0Cg2RvZ0MTFYH0KAsO3yjkKsC7/dIVoD9+hzFzJijJ/+Ur+TWPrJJf9paXlqD9qgcreUZjfqAN5IC2fDoV/TYeVwvuMcIcSA3rA+Gxf6Wi82C0i31M6lzUyGV0PzY4DI0DyodpCofpG/b09weIupzPpCBaGr0KsSH48pc2OEaDA=="}
"""
        #json.loads(payment_request)
        self.assertIsNotNone(verify_payment_request(payment_request))

    def test_verify_payment_request_wrong_signature(self):
        payment_request = r"""
{"message": "{\"name\": \"Nano Coffee Shop\", \"address\": \"Milano\", \"amount\": 101, \"dest_address\": \"xrb_1234\"}", "signature": "R1nNnvBY6MPxbIoCk7yjzcAjCCESr3gSwrQF87L2XWRWpvQoF08/RQW1nldEbnc5RNMhxIolSHpGxYPs1hP9wwmRwexRzep5EsqsbyGfhkyfr318kAjo+r1PoTX2u4jOgsMxKRu1h5ycI1qqd8fYJ1IfkcKc5AuKiJPI3IC4AFB0Cg2RvZ0MTFYH0KAsO3yjkKsC7/dIVoD9+hzFzJijJ/+Ur+TWPrJJf9paXlqD9qgcreUZjfqAN5IC2fDoV/TYeVwvuMcIcSA3rA+Gxf6Wi82C0i31M6lzUyGV0PzY4DI0DyodpCofpG/b09weIupzPpCBaGr0KsSH48pc2OEaDA=="}
"""
        # json.loads(payment_request)
        self.assertIsNone(verify_payment_request(payment_request))


    @patch('wallet.ask_confirmation', return_value=True)
    @patch('wallet.send_money', return_value=123456)
    def test_on_message_payment_request(self, ask_confirmation_mock, send_money_mock):
        client = MagicMock()
        payment_request = r"""
{"message": "{\"name\": \"Nano Coffee Shop\", \"address\": \"Milano\", \"amount\": 100, \"dest_address\": \"xrb_1234\"}", "signature": "R1nNnvBY6MPxbIoCk7yjzcAjCCESr3gSwrQF87L2XWRWpvQoF08/RQW1nldEbnc5RNMhxIolSHpGxYPs1hP9wwmRwexRzep5EsqsbyGfhkyfr318kAjo+r1PoTX2u4jOgsMxKRu1h5ycI1qqd8fYJ1IfkcKc5AuKiJPI3IC4AFB0Cg2RvZ0MTFYH0KAsO3yjkKsC7/dIVoD9+hzFzJijJ/+Ur+TWPrJJf9paXlqD9qgcreUZjfqAN5IC2fDoV/TYeVwvuMcIcSA3rA+Gxf6Wi82C0i31M6lzUyGV0PzY4DI0DyodpCofpG/b09weIupzPpCBaGr0KsSH48pc2OEaDA=="}
"""

        message = MQTT_Message(topic='/payment_requests/123', payload=payment_request)

        on_message(client, None, message)

        client.publish.assert_called_once()
        self.assertEqual('/payments/123', client.publish.call_args[0][0])

        payment_message = json.loads(client.publish.call_args[0][1])

        self.assertEqual(123456, payment_message['txhash'])

        client.subscribe.assert_called_with('/acks/123')

    @patch('wallet.print_ack')
    def test_on_message_ack(self, print_ack_mock):
        client = MagicMock()
        message = MQTT_Message(topic='/acks/123', payload=None)

        on_message(client, None, message)
        print_ack_mock.assert_called_with('123')
