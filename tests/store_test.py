import unittest
import json
import callee
from typing import NamedTuple
from unittest.mock import MagicMock, patch, ANY

from store import get_generate_payment_request, on_message, on_connect, CONF


class MQTTMessage(NamedTuple):
    topic: any
    payload: any


class TestStore(unittest.TestCase):
    def test_get_generation_payment_request(self):
        (topic, payload) = get_generate_payment_request(123, 100)

        self.assertRegex(topic, '^\/generate_payment_request\/\w+\/request')
        message = json.loads(payload)
        self.assertEqual(123, message['session_id'])
        self.assertEqual(100, message['amount'])
        self.assertEqual('euro', message['fiat_currency'])
        self.assertEqual('nanoray', message['crypto_currency'])

    def test_on_connect(self):
        client = MagicMock()

        userdata = {
            'session_id': 123,
            'amount': 100,
            'crypto_currency': 'nanoray',
            'fiat_currency': 'euro'
        }

        on_connect(client, userdata, None, None)

        client.subscribe.assert_any_call('/acks/123')
        client.subscribe.assert_any_call(callee.Regex('^\/generate_payment_request\/\w+\/reply$'))
        client.publish.assert_called_once_with(callee.Regex('^\/generate_payment_request\/\w+\/request$'), ANY)

    @patch('store.print_ack')
    def test_on_message_ack(self, print_ack_mock):
        client = MagicMock()
        message = MQTTMessage(topic='/acks/123', payload=None)

        on_message(client, None, message)
        print_ack_mock.assert_called_with('123')

    @patch('store.generate_qr')
    def test_on_message_generate_payment_request(self, generate_qr_mock):
        client = MagicMock()
        topic = '/generate_payment_request/{}/reply'.format(CONF.deviceID)
        payload = {'status': '200',
                   'session_id': '123',
                   }
        message = MQTTMessage(topic=topic, payload=json.dumps(payload))
        userdata = {
            'session_id': 123,
            'amount': 100,
            'crypto_currency': 'nanoray',
            'fiat_currency': 'euro'
        }
        on_message(client, userdata, message)

        generate_qr_mock.assert_called_with("manta://{}/{}".format(CONF.url, 123))

    @patch('store.generate_qr')
    def test_on_message_generate_payment_request_legacy(self, generate_qr_mock):
        client = MagicMock()
        topic = '/generate_payment_request/{}/reply'.format(CONF.deviceID)
        payload = {'status': '200',
                   'session_id': '123',
                   'crypto_currency': 'BTC',
                   'address': '1BvBMSEYstWetqTFn5Au4m4GFg7xJaNVN2'
                   }
        message = MQTTMessage(topic=topic, payload=json.dumps(payload))
        userdata = {
            'session_id': 123,
            'amount': 100,
            'crypto_currency': 'BTC',
            'fiat_currency': 'euro'
        }
        on_message(client, userdata, message)

        generate_qr_mock.assert_called_with("bitcoin:1BvBMSEYstWetqTFn5Au4m4GFg7xJaNVN2?amount=100")
