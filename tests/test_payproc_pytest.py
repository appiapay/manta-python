import pytest
import simplejson as json
from callee import Matcher
from cryptography.hazmat.primitives import serialization

from manta.messages import Destination, MerchantOrderRequestMessage, PaymentRequestMessage, \
    PaymentMessage, AckMessage, Status, Merchant
from manta.payproc import PayProc

pytest.register_assert_rewrite("tests.utils")
from tests.utils import mock_mqtt, JsonEqual
from decimal import Decimal


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

CERTFICATE_FILENAME = "certificates/root/keys/www.brainblocks.com.key"

DESTINATIONS = [
    Destination(
        amount=Decimal("5"),
        destination_address="btc_daddress",
        crypto_currency="btc"
    ),
    Destination(
        amount=Decimal("10"),
        destination_address="nano_daddress",
        crypto_currency="nano"
    ),

]

MERCHANT = Merchant(
    name="Merchant 1",
    address="5th Avenue"
)


@pytest.fixture
def payproc():
    # noinspection PyUnusedLocal
    def get_destinations(device, merchant_order: MerchantOrderRequestMessage):
        if merchant_order.crypto_currency:
            destination = next(x for x in DESTINATIONS if x.crypto_currency == merchant_order.crypto_currency)
            return [destination]
        else:
            return DESTINATIONS

    pp = PayProc(CERTFICATE_FILENAME)
    pp.get_merchant = lambda x: MERCHANT

    pp.get_destinations = get_destinations
    pp.get_supported_cryptos = lambda device, payment_request: {'btc', 'xmr', 'nano'}
    return pp


def test_key_from_keydata():
    key = PayProc.key_from_keydata(PRIV_KEY_DATA)
    assert PRIV_KEY_DATA == key.private_bytes(encoding=serialization.Encoding.PEM,
                                            format=serialization.PrivateFormat.TraditionalOpenSSL,
                                            encryption_algorithm=serialization.NoEncryption())


def test_sign():
    pp = PayProc(CERTFICATE_FILENAME)
    assert HELLO_SIGNED == pp.sign(b"Hello")


def test_generate_payment_request():
    pp = PayProc(CERTFICATE_FILENAME)
    pp.get_merchant = lambda x: MERCHANT
    pp.get_destinations = lambda device, payment_request: [
        Destination(amount=Decimal(5), destination_address="xrb123", crypto_currency="NANO")]
    pp.get_supported_cryptos = lambda device, payment_request: ['BTC', 'XMR', 'NANO']

    payment_request = MerchantOrderRequestMessage(amount=Decimal(10), fiat_currency="EURO", session_id="123",
                                                  crypto_currency="NANO")

    envelope = pp.generate_payment_request("device1", payment_request)

    expected_message = PaymentRequestMessage(merchant=MERCHANT,
                                             amount=Decimal(10),
                                             fiat_currency="EURO",
                                             destinations=[Destination(amount=Decimal(5), destination_address="xrb123",
                                                                       crypto_currency="NANO")],
                                             supported_cryptos={'BTC', 'XMR', 'NANO'}
                                             )

    assert expected_message == envelope.unpack()


def test_on_connect(mock_mqtt, payproc):
    payproc.run()
    mock_mqtt.subscribe.assert_any_call("merchant_order_request/+")


def test_receive_merchant_order_request(mock_mqtt, payproc):
    request = MerchantOrderRequestMessage(
        amount=Decimal("1000"),
        session_id='1423',
        fiat_currency='eur',
    )

    expected = AckMessage(
        txid="0",
        url="manta://localhost/1423",
        status=Status.NEW
    )

    mock_mqtt.push("merchant_order_request/device1", request.to_json())

    mock_mqtt.publish.assert_any_call('acks/1423', JsonEqual(expected))
    mock_mqtt.subscribe.assert_any_call('payments/1423')
    mock_mqtt.subscribe.assert_any_call('payment_requests/1423/+')


def test_receive_merchant_order_request_legacy(mock_mqtt, payproc):
    request = MerchantOrderRequestMessage(
        amount=Decimal("1000"),
        session_id='1423',
        fiat_currency='eur',
        crypto_currency='btc'
    )

    expected = AckMessage(
        txid="0",
        url="bitcoin:btc_daddress?amount=5",
        status=Status.NEW
    )

    mock_mqtt.push("merchant_order_request/device1", request.to_json())
    mock_mqtt.publish.assert_any_call("acks/1423", JsonEqual(expected))


def test_get_payment_request(mock_mqtt, payproc):
    test_receive_merchant_order_request(mock_mqtt, payproc)
    mock_mqtt.push('payment_requests/1423/btc', '')

    destination = Destination(
        amount=Decimal("5"),
        destination_address="btc_daddress",
        crypto_currency="btc"
    )

    expected = PaymentRequestMessage(
        merchant=MERCHANT,
        fiat_currency='eur',
        amount=Decimal("1000"),
        destinations=[destination],
        supported_cryptos={'nano', 'btc', 'xmr'}
    )

    class PMEqual(Matcher):
        payment_request: PaymentRequestMessage

        def __init__(self, payment_request: PaymentRequestMessage):
            self.payment_request = payment_request

        def match(self, value):
            decoded = json.loads(value)
            message = PaymentRequestMessage.from_json(decoded['message'])
            assert self.payment_request == message
            return True

    mock_mqtt.publish.assert_called_with('payment_requests/1423', PMEqual(expected))


def test_get_payment_request_all(mock_mqtt, payproc):
    test_receive_merchant_order_request(mock_mqtt, payproc)
    mock_mqtt.push('payment_requests/1423/all', '')

    expected = PaymentRequestMessage(
        merchant=MERCHANT,
        fiat_currency='eur',
        amount=Decimal("1000"),
        destinations=DESTINATIONS,
        supported_cryptos={'nano', 'btc', 'xmr'}
    )

    class PMEqual(Matcher):
        payment_request: PaymentRequestMessage

        def __init__(self, payment_request: PaymentRequestMessage):
            self.payment_request = payment_request

        def match(self, value):
            decoded = json.loads(value)
            message = PaymentRequestMessage.from_json(decoded['message'])
            assert self.payment_request == message
            return True

    mock_mqtt.publish.assert_called_with('payment_requests/1423', PMEqual(expected))


def test_payment_message(mock_mqtt, payproc):
    test_receive_merchant_order_request(mock_mqtt, payproc)
    message = PaymentMessage(
        crypto_currency="NANO",
        transaction_hash="myhash"
    )

    ack = AckMessage(
        txid='0',
        status=Status.PENDING,
        transaction_hash="myhash",
        transaction_currency="NANO"
    )

    mock_mqtt.push("payments/1423", message.to_json())

    mock_mqtt.publish.assert_called_with('acks/1423', JsonEqual(ack))


def test_confirm(mock_mqtt, payproc):
    test_payment_message(mock_mqtt, payproc)
    payproc.confirm("1423")

    ack = AckMessage(
        txid="0",
        status=Status.PAID,
        transaction_hash="myhash",
        transaction_currency="NANO"
    )

    mock_mqtt.publish.assert_called_with('acks/1423', JsonEqual(ack))
