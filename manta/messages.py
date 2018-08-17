from typing import NamedTuple


class GeneratePaymentRequestMessage(NamedTuple):
    amount: float
    session_id: str
    fiat_currency: str
    crypto_currency: str


class GeneratePaymentReplyMessage(NamedTuple):
    status: int
    session_id: str
    url: str


class AckMessage(NamedTuple):
    txid: str
    transaction_hash: str
    status: str
