import logging
from decimal import Decimal

import pytest
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives.serialization import load_pem_private_key

from manta.messages import Destination, PaymentRequestMessage, verify_chain, PaymentMessage, AckMessage, Status, \
    Merchant
from manta.wallet import Wallet

pytest.register_assert_rewrite("tests.utils")
# noinspection PyUnresolvedReferences
from tests.utils import mock_mqtt, JsonEqual

DESTINATIONS = [
    Destination(
        amount=5,
        destination_address="btc_daddress",
        crypto_currency="btc"
    ),
    Destination(
        amount=10,
        destination_address="nano_daddress",
        crypto_currency="nano"
    ),

]

MERCHANT = Merchant(
    name="Merchant 1",
    address="5th Avenue"
)

PRIVATE_KEY = "certificates/root/keys/test.key"
CERTIFICATE = "certificates/root/certs/test.crt"
CA_CERTIFICATE = "certificates/root/certs/AppiaDeveloperCA.crt"


@pytest.fixture
def payment_request():
    with open(PRIVATE_KEY, 'rb') as myfile:
        key_data = myfile.read()

        key = load_pem_private_key(key_data, password=None, backend=default_backend())

        message = PaymentRequestMessage(
            merchant=MERCHANT,
            amount=Decimal(10),
            fiat_currency="euro",
            destinations=DESTINATIONS,
            supported_cryptos={'btc', 'xmr', 'nano'}

        )

        return message.get_envelope(key)


def test_parse_url():
    match = Wallet.parse_url("manta://localhost/JqhCQ64gTYi02xu4GhBzZg==")
    assert "localhost" == match[1]
    assert "JqhCQ64gTYi02xu4GhBzZg==" == match[3]


def test_parse_url_with_port():
    match = Wallet.parse_url("manta://127.0.0.1:8000/123")
    assert "127.0.0.1" == match[1]
    assert "8000" == match[2]
    assert "123" == match[3]


def test_factory(mock_mqtt):
    wallet = Wallet.factory("manta://127.0.0.1/123", "filename")
    assert wallet.host == "127.0.0.1"
    assert wallet.port == 1883
    assert wallet.session_id == "123"


@pytest.mark.timeout(2)
@pytest.mark.asyncio
async def test_get_payment_request(mock_mqtt, payment_request, caplog):
    caplog.set_level(logging.INFO)
    wallet = Wallet.factory("manta://localhost:8000/123", "filename")

    # noinspection PyUnusedLocal
    def se(topic, payload=None):
        nonlocal mock_mqtt, payment_request

        if topic == "payment_requests/123/btc":
            mock_mqtt.push("payment_requests/123", payment_request.to_json())
        else:
            assert True, "Unknown topic"

    mock_mqtt.publish.side_effect = se

    envelope = await wallet.get_payment_request("btc")
    assert envelope.unpack() == payment_request.unpack()
    assert envelope.verify(CERTIFICATE)


def test_send_payment(mock_mqtt):
    wallet = Wallet.factory("manta://localhost:8000/123", "filename")

    wallet.send_payment(transaction_hash="myhash", crypto_currency="nano")

    expected = PaymentMessage(
        transaction_hash="myhash",
        crypto_currency="nano"
    )

    mock_mqtt.subscribe.assert_called_with("acks/123")
    mock_mqtt.publish.assert_called_with("payments/123", JsonEqual(expected))


@pytest.mark.asyncio
async def test_on_ack(mock_mqtt):
    wallet = Wallet.factory("manta://localhost:8000/123", "filename")

    expected = AckMessage(
        txid="0",
        transaction_hash="myhash",
        status=Status.PENDING
    )

    mock_mqtt.push("acks/123", expected.to_json())

    ack_message = await wallet.acks.get()

    assert ack_message == expected


def test_verify_chain():
    path = verify_chain(CERTIFICATE, CA_CERTIFICATE)
    assert path
