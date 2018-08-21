from manta.messages import Destination, PaymentRequestMessage, verify_chain, PaymentMessage, AckMessage
from manta.payproclib import PayProc
from manta.walletlib import Wallet
import pytest
from tests.utils import MQTTMessage, mock_mqtt
from cryptography.hazmat.primitives.serialization import load_pem_private_key
from cryptography.hazmat.backends import default_backend
import simplejson as json
import logging
from tests.utils import JsonEqual

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

PRIVATE_KEY = "certificates/root/keys/www.brainblocks.com.key"
CERTIFICATE = "certificates/root/certs/www.brainblocks.com.crt"
CA_CERTIFICATE = "certificates/root/certs/root.crt"


@pytest.fixture
def payment_request():
    with open(PRIVATE_KEY, 'rb') as myfile:
        key_data = myfile.read()

        key = load_pem_private_key(key_data, password=None, backend=default_backend())

        message = PaymentRequestMessage(
            merchant="merchant1",
            amount=10,
            fiat_currency="euro",
            destinations=DESTINATIONS,
            supported_cryptos={'btc', 'xmr', 'nano'}

        )

        return message.get_envelope(key)


def test_parse_url():
    match = Wallet.parse_url("manta://127.0.0.1/123")
    assert "127.0.0.1" == match[1]
    assert "123" == match[3]


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


def test_factory(mock_mqtt):
    wallet = Wallet.factory("manta://localhost:8000/123", "filename")
    assert wallet.host == "localhost"
    assert wallet.port == 8000
    assert wallet.session_id == "123"


@pytest.mark.timeout(2)
@pytest.mark.asyncio
async def test_get_payment_request(mock_mqtt, payment_request, caplog):
    caplog.set_level(logging.INFO)
    wallet = Wallet.factory("manta://localhost:8000/123", "filename")

    def se(topic, payload=None):
        nonlocal mock_mqtt, payment_request

        if topic == "payment_requests/123/btc":
            mock_mqtt.push("payment_requests/123", json.dumps(payment_request))
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
        status="pending"
    )

    mock_mqtt.push("acks/123", expected.to_json())

    ack_message = await wallet.acks.get()

    assert ack_message == expected


def test_verify_chain():
    path = verify_chain(CERTIFICATE, CA_CERTIFICATE)
    assert path
