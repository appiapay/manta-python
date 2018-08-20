from manta.messages import Destination, MerchantOrderRequestMessage
from manta.payproclib import PayProc
import logging

logging.basicConfig(level=logging.INFO)

CERTFICATE_FILENAME = "certificates/root/keys/www.brainblocks.com.key"

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


def get_destinations(device, merchant_order: MerchantOrderRequestMessage):
    if merchant_order.crypto_currency:
        destination = next(x for x in DESTINATIONS if x.crypto_currency == merchant_order.crypto_currency)
        return [destination]
    else:
        return DESTINATIONS


pp = PayProc(CERTFICATE_FILENAME, testing=True)
pp.get_merchant = lambda x: "merchant1"
pp.get_destinations = get_destinations
pp.get_supported_cryptos = lambda device, payment_request: {'btc', 'xmr', 'nano'}
pp.run()

while True:
    pass

