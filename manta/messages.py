# Manta Python
# Manta Protocol Implementation for Python
# Copyright (C) 2018 Alessandro Viganò
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

import base64
from enum import Enum
from typing import NamedTuple, List, Set, TypeVar, Type, Optional, Union

import attr
import cattr
import simplejson as json
from certvalidator import CertificateValidator, ValidationContext
from cryptography import x509
from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding
from cryptography.hazmat.primitives.asymmetric.rsa import RSAPrivateKey
from decimal import Decimal
from manta import MANTA_VERSION


class Status(Enum):
    """
    Status for ack messages
    """
    NEW = "new"  #: Created after accepting Merchant Order
    INVALID = "invalid"  #: Order invalid - Ex timeout. Additional info can be specified in Ack Memo field
    PENDING = "pending"  #: Created after receiving payment from wallet
    CONFIRMING = "confirming"  #: Paid received by Payment Processor but not yet confirmed
    PAID = "paid"  #: Created after blockchain confirmation
    CANCELED = "canceled"  #: Order has been canceled


T = TypeVar('T', bound='Message')


def drop_nonattrs(d: dict, type_: type) -> dict:
    """gets rid of all members of the dictionary that wouldn't fit in the given 'attrs' Type"""
    attrs_attrs = getattr(type_, '__attrs_attrs__', None)
    if attrs_attrs is None:
        raise ValueError(f'type {type_} is not an attrs class')

    attrs: Set[str] = {attr.name for attr in attrs_attrs}
    # attrs: Set[str] = {attr.name for attr in attrs_attrs if attr.init is True}

    return {key: val for key, val in d.items() if key in attrs}


def structure_ignore_extras(d: dict, Type: type):
    return cattr.structure(drop_nonattrs(d, Type), Type)


@attr.s
class Message:

    def unstructure(self):
        cattr.register_unstructure_hook(Decimal, lambda d: str(d))
        return cattr.unstructure(self)

    def to_json(self) -> str:
        return json.dumps(self.unstructure(), iterable_as_array=True)

    @classmethod
    # def from_json(cls, json_str: str):
    def from_json(cls: Type[T], json_str: str) -> T:
        d = json.loads(json_str)
        cattr.register_structure_hook(Decimal, lambda d, t: Decimal(d))

        if 'version' not in d:
            d['version'] = ''

        return structure_ignore_extras(d, cls)


@attr.s(auto_attribs=True)
class MerchantOrderRequestMessage(Message):
    """
    Merchant Order Request

    Published by Merchant on MERCHANT_ORDER_REQUEST..

    Args:
        amount: amount in fiat currency
        fiat_currency: fiat currency
        session_id: random uuid base64 safe
        crypto_currency: None for manta protocol. Specified for legacy
        version: Manta protocol version

    """

    amount: Decimal
    session_id: str
    fiat_currency: str
    crypto_currency: Optional[str] = None
    version: Optional[str] = MANTA_VERSION


@attr.s(auto_attribs=True)
class AckMessage(Message):
    """
    Ack Message

    Order progress message.

    Published by Merchant on ACKS/{SESSION_ID}

    Args:
        txid: progressive transaction ID generated by Merchant
        status: ack type
        url: url to be used for QR Code or NFC. Used in NEW
        amount: amount in crypto currency. Used in NEW
        transaction_hash: hash of transaction. After PENDING
        memo: extra text field
        version: Manta protocol version
    """
    txid: str
    status: Status
    url: Optional[str] = None
    amount: Optional[Decimal] = None
    transaction_hash: Optional[str] = None
    transaction_currency: Optional[str] = None
    memo: Optional[str] = None
    version: Optional[str] = MANTA_VERSION


@attr.s(auto_attribs=True)
class Destination(Message):
    """
    Destination

    Args:
        amount: amount in crypto currency
        destination_address: destination address for payment
        crypto_currency: crypto_currency (ex. NANO, BTC...)mo
    """
    amount: Decimal
    destination_address: str
    crypto_currency: str


@attr.s(auto_attribs=True)
class Merchant(Message):
    """
    Merchant

    Args:
        name: merchant name
        address: merchant address
    """
    name: str
    address: Optional[str] = None


@attr.s(auto_attribs=True)
class PaymentRequestMessage(Message):
    """
    Payment Request

    Generated after request on payment_requests/[session_id}/crypto

    Published in Envelope to Payment Processor on payment_requests/{session_id}

    Args:
        merchant: merchant data
        amount: amount in fiat currency
        fiat_currency: fiat currency
        destinations: list of destination addresses
        supported_cryptos: list of supported crypto currencies

    """
    merchant: Merchant
    amount: Decimal
    fiat_currency: str
    destinations: List[Destination]
    supported_cryptos: Set[str]

    def get_envelope(self, key: RSAPrivateKey):
        json_message = self.to_json()
        signature = base64.b64encode(key.sign(json_message.encode('utf-8'), padding.PKCS1v15(), hashes.SHA256()))

        return PaymentRequestEnvelope(message=json_message,
                                      signature=signature.decode('utf-8'))


@attr.s(auto_attribs=True)
class PaymentRequestEnvelope(Message):
    """
    Payment Request Envelope

    Envelope with Payment Request message and signature

    Published to Payment Processor on payment_requests/{session_id}

    Args:
        message: message as json string
        signature: PKCS#1 v1.5 signature of the message field
        version: Manta protocol version
    """
    message: str
    signature: str
    version: Optional[str] = MANTA_VERSION

    def unpack(self) -> PaymentRequestMessage:
        pr = PaymentRequestMessage.from_json(self.message)
        return pr

    def verify(self, certificate: Union[str, x509.Certificate]) -> bool:
        if isinstance(certificate, x509.Certificate):
            cert = certificate
        else:
            if certificate.startswith("-----BEGIN CERTIFICATE-----"):
                pem = certificate.encode()
            else:
                with open(certificate, 'rb') as my_file:
                    pem = my_file.read()

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
    """
    Payment Message

    Published by wallet on payments/{session_id}

    Args:
        crypto_currency: crypto currency used for payment
        transaction_hash: hash of transaction
        version: Manta protocol version

    """
    crypto_currency: str
    transaction_hash: str
    version: Optional[str] = MANTA_VERSION


def verify_chain(certificate: Union[str, x509.Certificate], ca: str):
    if isinstance(certificate, x509.Certificate):
        pem = certificate.public_bytes(serialization.Encoding.PEM)
    else:
        if certificate.startswith("-----BEGIN CERTIFICATE-----"):
            pem = certificate.encode()
        else:
            with open(certificate, 'rb') as my_file:
                pem = my_file.read()
        # cert = x509.load_pem_x509_certificate(pem, default_backend())

    with open(ca, 'rb') as my_file:
        pem_ca = my_file.read()
    # ca = x509.load_pem_x509_certificate(pem_ca, default_backend())

    trust_roots = [pem_ca]
    context = ValidationContext(trust_roots=trust_roots)

    validator = CertificateValidator(pem, validation_context=context)
    return validator.validate_usage({"digital_signature"})
