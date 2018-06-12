import base64
import json
import unittest
from typing import NamedTuple
from unittest.mock import MagicMock

from cryptography import x509
from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import padding

from payproc import sign, key_from_keydata, generate_payment_request, on_message

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


class MQTT_Message(NamedTuple):
    topic: any
    payload: any


class TestPayProc(unittest.TestCase):
    def setUp(self):
        self.cert = x509.load_pem_x509_certificate(CERT_DATA, default_backend())

    def test_key_from_keydata(self):
        key = key_from_keydata(PRIV_KEY_DATA)
        self.assertEqual(PRIV_KEY_DATA, key.private_bytes(encoding=serialization.Encoding.PEM,
                                                          format=serialization.PrivateFormat.TraditionalOpenSSL,
                                                          encryption_algorithm=serialization.NoEncryption()))

    def test_sign(self):
        key = key_from_keydata(PRIV_KEY_DATA)

        message = b'Hello World!'
        signature = sign(message, key)
        try:
            self.cert.public_key().verify(
                base64.b64decode(signature),
                message,
                padding.PSS(
                    mgf=padding.MGF1(hashes.SHA256()),
                    salt_length=padding.PSS.MAX_LENGTH
                ),
                hashes.SHA256()
            )
        except InvalidSignature:
            self.fail("Not valid signature")

    def test_generate_payment_request(self):
        payment_request = generate_payment_request('device1', 100, 123)

        # print(payment_request)

        # Verify signature of message
        j_payment_request = json.loads(payment_request)
        signature = j_payment_request['signature']
        message = j_payment_request['message']

        key = key_from_keydata(PRIV_KEY_DATA)

        try:
            self.cert.public_key().verify(
                base64.b64decode(signature),
                message.encode('utf-8'),
                padding.PSS(
                    mgf=padding.MGF1(hashes.SHA256()),
                    salt_length=padding.PSS.MAX_LENGTH
                ),
                hashes.SHA256()
            )
        except InvalidSignature:
            self.fail("Not valid signature")

        # Verify address signature
        j_message = json.loads(message)

        signature = j_message['address_sig']
        message = j_message['dest_address']

        try:
            self.cert.public_key().verify(
                base64.b64decode(signature),
                message.encode('utf-8'),
                padding.PSS(
                    mgf=padding.MGF1(hashes.SHA256()),
                    salt_length=padding.PSS.MAX_LENGTH
                ),
                hashes.SHA256()
            )
        except InvalidSignature:
            self.fail("Not valid signature")


class TestPayProcMQTT(unittest.TestCase):
    def test_generate_payment_request(self):
        client = MagicMock()

        message = MQTT_Message(
            topic="/generate_payment_request/device1",
            payload=json.dumps({
                'amount': '1000',
                'txid': '1423',
            }))

        on_message(client, None, message)
        client.publish.assert_called_once()
        self.assertEqual('/payment_requests/1423', client.publish.call_args[0][0])

    def test_payment_message(self):
        client = MagicMock()

        message = MQTT_Message(
            topic="/payments/123",
            payload=json.dumps({
                'txhash': '1000',
                'address_sig': "E46LrE9vGUUmxfnWkTAc8KOglpAjsiN8b6ATAnqXQYKreW4fbC2paFuS4hWHWuqlK5o48l5JXNMOiW"
                               "+yzNYsJrVTtSzL5eGsNm/+UadodRAMjRXSkzlLqo3IYx6KUp"
                               "+OSbnksjrJ9nDM5LY1lKoGtb7da8aIAyl66NGjOs9gQU4LCi0W4hi1/Vjle1ZLVvxDLGj8OAwY6dUQ/4wteh7"
                               "/35njbw5rUJ6oPSOMI9OYYamPW+fZBrjH9jftiYZvJN8b0ZvHnbIFc1oX5E"
                               "+9fujp7rapioHfSfQC5xBnF8X29fHzHpArn9Yo4hKbnr3VqpitF51W+Eb2u4s8WEJ/+fUSOQ==",
                'txid': '123',
        }))

        on_message(client, None, message)

        client.publish.called_with('123')

    if __name__ == '__main__':
        unittest.main()
