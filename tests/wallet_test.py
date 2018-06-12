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
{"message": "{\"name\": \"Nano Coffee Shop\", \"address\": \"Milano\", \"amount\": 100, \"txid\": 123, \"dest_address\": \"xrb_1234\", \"address_sig\": \"E46LrE9vGUUmxfnWkTAc8KOglpAjsiN8b6ATAnqXQYKreW4fbC2paFuS4hWHWuqlK5o48l5JXNMOiW+yzNYsJrVTtSzL5eGsNm/+UadodRAMjRXSkzlLqo3IYx6KUp+OSbnksjrJ9nDM5LY1lKoGtb7da8aIAyl66NGjOs9gQU4LCi0W4hi1/Vjle1ZLVvxDLGj8OAwY6dUQ/4wteh7/35njbw5rUJ6oPSOMI9OYYamPW+fZBrjH9jftiYZvJN8b0ZvHnbIFc1oX5E+9fujp7rapioHfSfQC5xBnF8X29fHzHpArn9Yo4hKbnr3VqpitF51W+Eb2u4s8WEJ/+fUSOQ==\"}", "signature": "SS+I4UiZmiqnL74bObC11c3/5fixe6ECLgDpal0+kvEDmzcRu+dJMqdWgLC8QD7fKJkN7Zqza1ue+C5+rLHKTMmUwcxe/CrsOxD3vjwG38FMi2qp+Qjr8B3UL7q27cyuQqyQcNRbFKhqxdyxq+gndir0h51dxw09qqcDh4TtFAzJ8xnxMDTQZXYEXl0Av76GEqvARi8xuVsZ5mmB4CTU1Q96jqPIFkZ9odrGIM6woZmzgXPH6qk4paM0Ty3U5ZAYyS47FxeoMq78obUltiasxKN7SqumrB5JT5vAbWxKvZf2+0MlpHKp7j+2QBvGd0oNV/Qzq8S43OHvICcB9GwU3A=="}
"""
        #json.loads(payment_request)
        self.assertIsNotNone(verify_payment_request(payment_request))

    def test_verify_payment_request_wrong_signature(self):
        payment_request = r"""
        {"message": "{\"name\": \"Nano Coffee Shop\", \"address\": \"Milano\", \"amount\": 101, \"txid\": 123, \"dest_address\": \"xrb_1234\", \"address_sig\": \"E46LrE9vGUUmxfnWkTAc8KOglpAjsiN8b6ATAnqXQYKreW4fbC2paFuS4hWHWuqlK5o48l5JXNMOiW+yzNYsJrVTtSzL5eGsNm/+UadodRAMjRXSkzlLqo3IYx6KUp+OSbnksjrJ9nDM5LY1lKoGtb7da8aIAyl66NGjOs9gQU4LCi0W4hi1/Vjle1ZLVvxDLGj8OAwY6dUQ/4wteh7/35njbw5rUJ6oPSOMI9OYYamPW+fZBrjH9jftiYZvJN8b0ZvHnbIFc1oX5E+9fujp7rapioHfSfQC5xBnF8X29fHzHpArn9Yo4hKbnr3VqpitF51W+Eb2u4s8WEJ/+fUSOQ==\"}", "signature": "SS+I4UiZmiqnL74bObC11c3/5fixe6ECLgDpal0+kvEDmzcRu+dJMqdWgLC8QD7fKJkN7Zqza1ue+C5+rLHKTMmUwcxe/CrsOxD3vjwG38FMi2qp+Qjr8B3UL7q27cyuQqyQcNRbFKhqxdyxq+gndir0h51dxw09qqcDh4TtFAzJ8xnxMDTQZXYEXl0Av76GEqvARi8xuVsZ5mmB4CTU1Q96jqPIFkZ9odrGIM6woZmzgXPH6qk4paM0Ty3U5ZAYyS47FxeoMq78obUltiasxKN7SqumrB5JT5vAbWxKvZf2+0MlpHKp7j+2QBvGd0oNV/Qzq8S43OHvICcB9GwU3A=="}
        """
        # json.loads(payment_request)
        self.assertIsNone(verify_payment_request(payment_request))

    def test_verify_payment_request_wrong_address_signature(self):
        # TO BE DONE
        pass

    @patch('wallet.ask_confirmation', return_value=True)
    def test_on_message_payment_request(self, ask_confirmation_mock):
        client = MagicMock()
        payment_request = r"""
{"message": "{\"name\": \"Nano Coffee Shop\", \"address\": \"Milano\", \"amount\": 100, \"txid\": 123, \"dest_address\": \"xrb_1234\", \"address_sig\": \"E46LrE9vGUUmxfnWkTAc8KOglpAjsiN8b6ATAnqXQYKreW4fbC2paFuS4hWHWuqlK5o48l5JXNMOiW+yzNYsJrVTtSzL5eGsNm/+UadodRAMjRXSkzlLqo3IYx6KUp+OSbnksjrJ9nDM5LY1lKoGtb7da8aIAyl66NGjOs9gQU4LCi0W4hi1/Vjle1ZLVvxDLGj8OAwY6dUQ/4wteh7/35njbw5rUJ6oPSOMI9OYYamPW+fZBrjH9jftiYZvJN8b0ZvHnbIFc1oX5E+9fujp7rapioHfSfQC5xBnF8X29fHzHpArn9Yo4hKbnr3VqpitF51W+Eb2u4s8WEJ/+fUSOQ==\"}", "signature": "SS+I4UiZmiqnL74bObC11c3/5fixe6ECLgDpal0+kvEDmzcRu+dJMqdWgLC8QD7fKJkN7Zqza1ue+C5+rLHKTMmUwcxe/CrsOxD3vjwG38FMi2qp+Qjr8B3UL7q27cyuQqyQcNRbFKhqxdyxq+gndir0h51dxw09qqcDh4TtFAzJ8xnxMDTQZXYEXl0Av76GEqvARi8xuVsZ5mmB4CTU1Q96jqPIFkZ9odrGIM6woZmzgXPH6qk4paM0Ty3U5ZAYyS47FxeoMq78obUltiasxKN7SqumrB5JT5vAbWxKvZf2+0MlpHKp7j+2QBvGd0oNV/Qzq8S43OHvICcB9GwU3A=="}
"""

        message = MQTT_Message(topic='/payment_requests/123', payload=payment_request)

        on_message(client, None, message)

        client.publish.assert_called_once()
        self.assertEqual('/payments/123', client.publish.call_args[0][0])

        payment_message = json.loads(client.publish.call_args[0][1])

        self.assertEqual(123, payment_message['txid'])
        self.assertEqual("E46LrE9vGUUmxfnWkTAc8KOglpAjsiN8b6ATAnqXQYKreW4fbC2paFuS4hWHWuqlK5o48l5JXNMOiW"
                         "+yzNYsJrVTtSzL5eGsNm/+UadodRAMjRXSkzlLqo3IYx6KUp"
                         "+OSbnksjrJ9nDM5LY1lKoGtb7da8aIAyl66NGjOs9gQU4LCi0W4hi1/Vjle1ZLVvxDLGj8OAwY6dUQ/4wteh7"
                         "/35njbw5rUJ6oPSOMI9OYYamPW+fZBrjH9jftiYZvJN8b0ZvHnbIFc1oX5E"
                         "+9fujp7rapioHfSfQC5xBnF8X29fHzHpArn9Yo4hKbnr3VqpitF51W+Eb2u4s8WEJ/+fUSOQ==",
                         payment_message['address_sig'])

        client.subscribe.assert_called_with('/acks/123')

    @patch('wallet.print_ack')
    def test_on_message_ack(self, print_ack_mock):
        client = MagicMock()
        message = MQTT_Message(topic='/acks/123', payload=None)

        on_message(client, None, message)
        print_ack_mock.assert_called_with('123')
