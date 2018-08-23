# from __future__ import annotations

import base64
from enum import Enum
from typing import NamedTuple, List, Set, TypeVar, Type, Optional

import attr
import cattr
import simplejson as json
from certvalidator import CertificateValidator, ValidationContext
from cryptography import x509
from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import padding
from cryptography.hazmat.primitives.asymmetric.rsa import RSAPrivateKey


class Status(Enum):
    NEW = "new"
    PENDING = "pending"
    PAID = "paid"


T = TypeVar('T', bound='Message')


@attr.s
class Message:
    def to_json(self) -> str:
        d = cattr.unstructure(self)
        return json.dumps(d, iterable_as_array=True)

    @classmethod
    # def from_json(cls, json_str: str):
    def from_json(cls: Type[T], json_str: str) -> T:
        d = json.loads(json_str)
        return cattr.structure(d, cls)


@attr.s(auto_attribs=True)
class MerchantOrderRequestMessage(Message):
    amount: float
    session_id: str
    fiat_currency: str
    crypto_currency: Optional[str] = None


@attr.s(auto_attribs=True)
class AckMessage(Message):
    txid: str
    status: Status
    url: Optional[str] = None
    amount: Optional[float] = None
    transaction_hash: Optional[str] = None


@attr.s(auto_attribs=True)
class Destination(Message):
    amount: float
    destination_address: str
    crypto_currency: str


@attr.s(auto_attribs=True)
class Merchant:
    name: str
    address: Optional[str] = None


@attr.s(auto_attribs=True)
class PaymentRequestMessage(Message):
    merchant: Merchant
    amount: float
    fiat_currency: str
    destinations: List[Destination]
    supported_cryptos: Set[str]

    def get_envelope(self, key: RSAPrivateKey):
        json_message = self.to_json()
        signature = base64.b64encode(key.sign(json_message.encode('utf-8'), padding.PKCS1v15(), hashes.SHA256()))

        return PaymentRequestEnvelope(json_message, signature.decode('utf-8'))


@attr.s(auto_attribs=True)
class PaymentRequestEnvelope(Message):
    message: str
    signature: str

    def unpack(self) -> PaymentRequestMessage:
        pr = PaymentRequestMessage.from_json(self.message)
        return pr

    def verify(self, certificate) -> bool:
        with open(certificate, 'rb') as myfile:
            pem = myfile.read()
        cert = x509.load_pem_x509_certificate(pem, default_backend())

        try:
            cert.public_key().verify(
                base64.b64decode(self.signature),
                self.message.encode('utf-8'),
                padding.PKCS1v15(),
                hashes.SHA256()
            )
            return True
        except InvalidSignature:
            return False


@attr.s(auto_attribs=True)
class PaymentMessage(Message):
    crypto_currency: str
    transaction_hash: str


def verify_chain(certificate: str, ca: str):
    with open(certificate, 'rb') as myfile:
        pem = myfile.read()
    cert = x509.load_pem_x509_certificate(pem, default_backend())

    with open(ca, 'rb') as myfile:
        pem_ca = myfile.read()
    ca = x509.load_pem_x509_certificate(pem, default_backend())

    trust_roots = [pem_ca]
    context = ValidationContext(trust_roots=trust_roots)

    validator = CertificateValidator(pem, validation_context=context)
    return validator.validate_usage({"digital_signature"})
