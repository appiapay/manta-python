from typing import NamedTuple, List, Set
import simplejson as json
import attr, cattr


class MerchantOrderRequestMessage(NamedTuple):
    amount: float
    session_id: str
    fiat_currency: str
    crypto_currency: str = None


class MerchantOrderReplyMessage(NamedTuple):
    status: int
    session_id: str
    url: str
    amount: float = None


class AckMessage(NamedTuple):
    txid: str
    transaction_hash: str
    status: str


@attr.s(auto_attribs=True)
class Destination:
    amount: float
    destination_address: str
    crypto_currency: str


@attr.s(auto_attribs=True)
class PaymentRequestMessage:
    merchant: str
    amount: float
    fiat_currency: str
    destinations: List[Destination]
    supported_cryptos: Set[str]

    def to_json(self) -> str:
        return json.dumps(attr.asdict(self))

    @classmethod
    def from_json(cls, json_str:str):
        return cattr.structure(json.loads(json_str), PaymentRequestMessage)
        # dict = json.loads(json_str)
        # destinations = [Destination(**x) for x in dict['destinations']]
        # dict['destinations'] = destinations
        # return cls(**dict)


class PaymentRequestEnvelope(NamedTuple):
    message: str
    signature: str

    def unpack(self) -> PaymentRequestMessage:
        pr = PaymentRequestMessage.from_json(self.message)
        return pr


class PaymentMessage(NamedTuple):
    crypto_currency: str
    transaction_hash: str
