import base64
from typing import NamedTuple, List, Set
import simplejson as json
import attr, cattr
from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import padding
from cryptography.hazmat.primitives.asymmetric.rsa import RSAPrivateKey
from cryptography import x509
from cryptography.hazmat.backends import default_backend
from certvalidator import CertificateValidator, ValidationContext


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

    def to_json(self) -> str:
        return json.dumps(self)

    @classmethod
    def from_json(cls, json_str: str):
        return cls(**json.loads(json_str))


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

    def get_envelope(self, key: RSAPrivateKey):
        json_message = self.to_json()
        signature = base64.b64encode(key.sign(json_message.encode('utf-8'), padding.PKCS1v15(), hashes.SHA256()))

        return PaymentRequestEnvelope(json_message, signature.decode('utf-8'))


class PaymentRequestEnvelope(NamedTuple):
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

    @classmethod
    def from_json(cls, json_str: str):
        return cls(**json.loads(json_str))


class PaymentMessage(NamedTuple):
    crypto_currency: str
    transaction_hash: str

    @classmethod
    def from_json(cls, json_str: str):
        return cls(**json.loads(json_str))

    def to_json(self):
        return json.dumps(self)


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
