import unittest
import json
from typing import NamedTuple
from unittest.mock import MagicMock, patch

from store import ask_generate_payment_request, on_message


class MQTT_Message(NamedTuple):
    topic: any
    payload: any


class TestStore(unittest.TestCase):
    def test_ask_generation_payment_request(self):
        client = MagicMock()
        ask_generate_payment_request(client, 123, 100)
        client.publish.assert_called_once()
        self.assertRegex(client.publish.call_args[0][0], '^\/generate_payment_request\/\w+')
        message = json.loads(client.publish.call_args[0][1])
        self.assertEqual(123, message['session_id'])
        self.assertEqual(100, message['amount'])

    @patch('store.print_ack')
    def test_on_message_ack(self, print_ack_mock):
        client = MagicMock()
        message = MQTT_Message(topic='/acks/123', payload=None)

        on_message(client, None, message)
        print_ack_mock.assert_called_with('123')