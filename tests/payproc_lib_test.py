import base64
import json
import unittest
import warnings
from typing import NamedTuple
from unittest.mock import MagicMock, ANY

from cryptography import x509
from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import padding

from payproclib import PayProc, Destination

PRIV_KEY_DATA = b'''\
-----BEGIN RSA PRIVATE KEY-----
MIIEpQIBAAKCAQEA1O+cC40Xtt1F87C7SHSckdEI6PeJKGaNGBfKLI8q+G3tbjFY
e+A83skUkkcQd9yICZQmVZ4Qqd3LaaPhOy+sDxkvytcTMwHj/N3IBq9IpZK1nVAm
1s2pNcvsAGTdKPfB0P8hHtNNrwi3c2G0NOP0UVDe3yDzeAacJMtbIHrMDG7Sb8Ob
ITd1NZd2NNv9Ou/RfmAb/pnigyHITZdzDGPCkP4x3Y3iLLQbdbC8U4nIHKw39HTA
N/+FYkWDFRIz8fdcI3EbksEvcgs3f63OR9uHvUNkqvueAwBTa2bFopzs7Li+oAuV
hA/UgXwgpsFF1pSzZz8WWYkcyDeJG9O3hRPc9QIDAQABAoIBAQCmxC4DQfJDrlK9
wzk6StHgxcTjqBJMiNyR9PfLJCl0PavJNG5nPjyOAw/QbEWyig4k6lmHjm7giqtn
xgh88R4hCQnMI9uOhDmJbizdR2RvAFKqrP5uFs4iKt5fhJ9NGZU62MWYvcbGgd4j
SG75SVqsYNjcCZOE+jBKBNYOvv2V8bppPhNIXs8iS3sUbZYDN5M4jQHo4O0j1MQi
2wDQpwAHg04QSnTERfz8K7yDucY7BBNSFQNHTG2fDq6uJk5Llj5NmLdMol+TSnHM
qnS5viuyHYHPl+WCT+QzUS+0kx5F71N2tLeX8fdMmY2GRmElkzFCOQ5kc5zU95lH
XCdwgoqVAoGBANaC597cyoX73SbBy0pOm7VW+16CUP76F0H1nIeEOTq5HkNf5LKB
grigij0r6wJxN85l4hmxoMX8f4PpG3PY64gR2HpR+GYPtdNuieZnhb3Q+r/DpnkE
0OIjqngQCPlqT1UAkrG1GDYLOEtirkJKAoBPhRx9mi6JLFju3ki7UkLfAoGBAP4e
s8gqYTIxoTnHV8U6jnuleYGhKLk3bI1CJ1JRk9S+tJsvPOErd0lQq545suwhYXUp
j85FDbgSw0eiAZJBz/jwJioSan1QgfcBxahXyMqTLwsDza4U8mV37dhTGKXXgLFe
rAvmlLVHDYWsmHIevKFSeqo77Nlx6Q5+jyR6pw6rAoGAP8A10vkBQ2J/7iXIGfRU
uEb6e7L1CWIgCV1KQMgeDgK4KMPV/usYg3BKxTVJKbemIzQKRyKQKmcJKpXbr8k2
7oCHOosj7Ikcu5Jtb0ky6R+zdcxarDqvLZX18qqpUB61Jwj9j8zHPkCFYXoZWeAO
8D0xzS7S5KOlx2RuMWViZDcCgYEAid9UgWRk6Zu9sqByAWL8zR8BZpBujNcCQT3E
Ich64XE6gfvGFxDDHnbzNdxuM+kEfFG5YRtcDyO26ZV/LsAgOxroSelF94mHieFf
QS+nlCj43AwLOsjInr7Lv5OOCuR6QUFxLN/EjPno3z6+UyRUCV67iMMMhQllfeSy
ewNEwhMCgYEAijETQlQTaEBRj4UD9rH4vUZfNnZO1NOetDBeXaLRLU7NJxTeZ/Tt
chFd+tlGvwi4ynJ4lPsoyMYvD8DFj0nXUUpDD/b07fsPPDrRgnKHiiPJF2rUN0IB
RWBnMUHLYluKopDqkoVAulUZ/QLWhmwvV4CV7G5PtIDpzmT3ycF2hqs=
-----END RSA PRIVATE KEY-----
'''

CERT_DATA = b'''\
-----BEGIN CERTIFICATE-----
MIIDQjCCAiqgAwIBAgIRAPr1QV+OmLIjsRH4mOxjy1EwDQYJKoZIhvcNAQELBQAw
KDEmMCQGA1UEAxMdTmFub3JheSBDZXJ0aWZpY2F0ZSBBdXRob3JpdHkwHhcNMTgw
NjEyMDUyMDI5WhcNMTkwNjEyMDUyMDI5WjAeMRwwGgYDVQQDExN3d3cuYnJhaW5i
bG9ja3MuY29tMIIBIjANBgkqhkiG9w0BAQEFAAOCAQ8AMIIBCgKCAQEA1O+cC40X
tt1F87C7SHSckdEI6PeJKGaNGBfKLI8q+G3tbjFYe+A83skUkkcQd9yICZQmVZ4Q
qd3LaaPhOy+sDxkvytcTMwHj/N3IBq9IpZK1nVAm1s2pNcvsAGTdKPfB0P8hHtNN
rwi3c2G0NOP0UVDe3yDzeAacJMtbIHrMDG7Sb8ObITd1NZd2NNv9Ou/RfmAb/pni
gyHITZdzDGPCkP4x3Y3iLLQbdbC8U4nIHKw39HTAN/+FYkWDFRIz8fdcI3EbksEv
cgs3f63OR9uHvUNkqvueAwBTa2bFopzs7Li+oAuVhA/UgXwgpsFF1pSzZz8WWYkc
yDeJG9O3hRPc9QIDAQABo3EwbzAOBgNVHQ8BAf8EBAMCBaAwHQYDVR0lBBYwFAYI
KwYBBQUHAwEGCCsGAQUFBwMCMB0GA1UdDgQWBBTTRDdHAcsOFNpRxBt4RlQbwagO
qjAfBgNVHSMEGDAWgBRwkhWOFhgXtaH1sKfkCQL78Mfy5TANBgkqhkiG9w0BAQsF
AAOCAQEAmJIyiA+m9duBYR+p1IwR/DyEssZ0YtCVaq375c567a6owPZSUEGi+cUj
xsEsxPkl6DrgZzEathvoUVNVlA1YyHwIFXp0n5Qd0OlQ66WnQD16i4CygdGTpAex
8oWK/6mUdXxIIEUHaiv5UYHQhfwCb+c0yNFeN+uQ2SfDwID20NjZNLGKQzYZ+JVI
QED2ofs5p/xm7qe/Ht58u6TqAYjxDO4OqSspzH2e6a2EIjVe81DvrfHnatDUar5m
+XkSTmuqyX0wmxZ2E2hhlJkhyLCadkP3Hor2s3nUpkqKH3bSUJ5U/TuvvxrEEt0I
z4TYl3Vuacma4wEMQGqhJSWv0gjRQg==
-----END CERTIFICATE-----
'''


HELLO_SIGNED = b'''\
ZdTXOalXWhP20r8C/AMOdTReRg3R0moqF/A4n3adX3tO27SAHzZtx60N6Br78QRO2Y0Gmq21Z9mW\
mO+x6Ne1QnkHg0mvm2qkISMHHIW4ej+opO5fmD3RlCcSUXuMMC4uOjfhQVCbksOoAf/tV0Ocy2Ma\
owxKQmUsBCHK1U5NykPpqJ+d6nLHoxVJ5mPrda6tbm7dzL1uUsTThe47haTzDCPzGY+/8SHRcL8v\
wbsqKgzOG2RvOOJDaPn/xhLs/HlUyNwGePFuQh0EOn1uuqWJPjj8HNbQmfd1/W2p5ldE2Xi2TpX1\
/mfiZXFtNhn7Su1EkAJE1Jph780HClldRdA5Dw==\
'''


class MQTTMessage(NamedTuple):
    topic: any
    payload: any


class TestPayProcLib(unittest.TestCase):
    def setUp(self):
        warnings.simplefilter("ignore")
        pass

    def test_key_from_keydata(self):
        key = PayProc.key_from_keydata(PRIV_KEY_DATA)
        self.assertEqual(PRIV_KEY_DATA, key.private_bytes(encoding=serialization.Encoding.PEM,
                                                          format=serialization.PrivateFormat.TraditionalOpenSSL,
                                                          encryption_algorithm=serialization.NoEncryption()))

    def test_sign(self):
        pp = PayProc("certificates/keys/root.key")
        self.assertEqual(HELLO_SIGNED, pp.sign(b"Hello"))

    def test_generate_payment_request(self):
        pp = PayProc("certificates/keys/root.key")
        pp.get_merchant = lambda x: "merchant1"
        pp.get_destinations = lambda x: [Destination(amount=5, destination_address="xrb123", crypto_currency="nano")]

        pr = pp.generate_payment_request("device1", amount="10", fiat_currency="euro")

        envelope = json.loads(pr)
        message = json.loads(envelope["message"])

        expected_message = {"merchant": "merchant1",
                            "amount": "10",
                            "fiat_currency": "euro",
                            "destinations": [
                                {"amount": 5, "destination_address": "xrb123", "crypto_currency": "nano"}
                            ]
                            }

        self.assertEqual(expected_message, message)


class TestPayProcMQTT(unittest.TestCase):
    def setUp(self):
        self.pp = PayProc("certificates/keys/root.key")
        self.pp.get_merchant = lambda x: "merchant1"
        self.pp.get_destinations = lambda x: [Destination(amount=5, destination_address="xrb123", crypto_currency="nano")]


    def test_generate_payment_request(self):
        client = MagicMock()

        message = MQTTMessage(
            topic="/generate_payment_request/device1/request",
            payload=json.dumps({
                'amount': 1000,
                'session_id': '1423',
                'crypto_currency': 'nanoray'
            }))

        self.pp.on_message(client, None, message)

        client.publish.assert_any_call('/generate_payment_request/device1/reply', ANY)
        client.publish.assert_any_call('/payment_requests/1423', ANY, retain=True)
        client.subscribe.assert_called_once_with('/payments/1423')

    def test_generate_payment_request_legacy(self):
        client = MagicMock()

        message = MQTTMessage(
            topic="/generate_payment_request/device1/request",
            payload=json.dumps({
                'amount': 1000,
                'session_id': '1423',
                'crypto_currency': 'BTC'
            }))

        self.pp.on_message(client, None, message)
        client.publish.assert_called_once_with('/generate_payment_request/device1/reply', ANY)
        client.subscribe.assert_not_called()

    def test_payment_message(self):
        client = MagicMock()

        message = MQTTMessage(
            topic="/payments/123",
            payload=json.dumps({
                'txhash': '1000'
            }))

        self.pp.on_message(client, None, message)

        client.publish.called_with('123')
    #
    # def test_txid_increment(self):
    #     client = MagicMock()
    #
    #     message = MQTTMessage(
    #         topic="/payments/123",
    #         payload=json.dumps({
    #             'txhash': '1000'
    #         }))
    #
    #     self.pp.on_message(client, None, message)
    #
    #     payload = json.loads(client.publish.call_args[0][1])
    #     start = payload['txid']
    #
    #     self.pp.on_message(client, None, message)
    #
    #     payload = json.loads(client.publish.call_args[0][1])
    #     self.assertEqual(1, payload['txid'] - start)


if __name__ == '__main__':
    unittest.main()