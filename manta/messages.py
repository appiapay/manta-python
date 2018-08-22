import base64
from typing import NamedTuple, List, Set

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


@attr.s
class Message:
    def to_json(self) -> str:
        return json.dumps(attr.asdict(self))

    @classmethod
    def from_json(cls, json_str: str):
        return cls(**json.loads(json_str))


@attr.s(auto_attribs=True)
class MerchantOrderRequestMessage(Message):
    amount: float
    session_id: str
    fiat_currency: str
    crypto_currency: str = None


@attr.s(auto_attribs=True)
class MerchantOrderReplyMessage(Message):
    status: int
    session_id: str
    url: str
    amount: float = None


@attr.s(auto_attribs=True)
class AckMessage(Message):
    txid: str
    transaction_hash: str
    status: str


@attr.s(auto_attribs=True)
class Destination(Message):
    amount: float
    destination_address: str
    crypto_currency: str


@attr.s(auto_attribs=True)
class PaymentRequestMessage(Message):
    merchant: str
    amount: float
    fiat_currency: str
    destinations: List[Destination]
    supported_cryptos: Set[str]

    @classmethod
    def from_json(cls, json_str:str):
        return cattr.structure(json.loads(json_str), PaymentRequestMessage)

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
        cert= x509.load_pem_x509_certificate(pem, default_backend())

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
