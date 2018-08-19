from typing import NamedTuple, List
import simplejson as json


class GeneratePaymentRequestMessage(NamedTuple):
    amount: float
    session_id: str
    fiat_currency: str
    crypto_currency: str = None


class GeneratePaymentReplyMessage(NamedTuple):
    status: int
    session_id: str
    url: str
    amount: float = None


class AckMessage(NamedTuple):
    txid: str
    transaction_hash: str
    status: str


class Destination(NamedTuple):
    amount: float
    destination_address: str
    crypto_currency: str


class PaymentRequestMessage(NamedTuple):
    merchant: str
    amount: float
    fiat_currency: str
    destinations: List[Destination]
    supported_cryptos: List[str]

    @classmethod
    def from_json(cls, json_str:str):
        dict = json.loads(json_str)
        destinations = [Destination(**x) for x in dict['destinations']]
        dict['destinations'] = destinations
        return cls(**dict)


class PaymentRequestEnvelope(NamedTuple):
    message: str
    signature: str

    def unpack(self) -> PaymentRequestMessage:
        pr = PaymentRequestMessage.from_json(self.message)
        return pr


class PaymentMessage(NamedTuple):
    crypto_currency: str
    transaction_hash: str
