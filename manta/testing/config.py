# -*- coding: utf-8 -*-
# Manta Python
# Manta Protocol Implementation for Python
# Copyright (C) 2019 xxx
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

from decimal import Decimal
from typing import List

from file_config import config, var

from ..messages import Destination, Merchant
from . import msg2config, get_tests_dir


@config
class BrokerConfig:
    """Basic broker configuration."""

    "allow listening port reallocation"
    allow_port_reallocation = var(bool, default=True, required=False)
    "start a new broker if true"
    start = var(bool, default=True)
    "broker listening host/interface"
    host = var(str, default='localhost', required=False)
    path = var(str, default=None, required=False)
    "broker listening port"
    port = var(int, default=1883, required=False)


@config
class WebConfig:

    enable = var(bool, default=False)
    allow_port_reallocation = var(bool, default=True,
                                  required=False)
    bind_address = var(str, default='localhost', required=False)
    bind_port = var(int, default=None, required=False)


_nano_dest = ("xrb_3d1ab61eswzsgx5arwqc3gw8xjcsxd7a5egtr69jixa5i"
              "t9yu9fzct9nyjyx")


@config
class DummyPayProcConfig:
    """Configuration Type for the dummy PayProc component."""

    DestinationConfig = msg2config(Destination)
    MerchantConfig = msg2config(Merchant)

    @config
    class PayProcWebConfig(WebConfig):

        bind_port = var(int, default=8081, required=False)

    supported_cryptos = var(List[str], unique=True, min=1)
    destinations = var(List[DestinationConfig], min=1)
    keyfile = var(str)
    merchant = var(MerchantConfig)
    web = var(PayProcWebConfig, default=PayProcWebConfig(), required=False)


@config
class DummyStoreConfig:
    """Configuration type for the dummy Store component."""

    @config
    class StoreWebConfig(WebConfig):

        bind_port = var(int, default=8080, required=False)

    web = var(StoreWebConfig, default=StoreWebConfig(), required=False)


@config
class DummyWalletConfig:

    @config
    class WalletWebConfig(WebConfig):

        bind_port = var(int, default=8082, required=False)

    account = var(str, required=False)
    wallet = var(str, required=False)
    certificate = var(str, required=False)
    interactive = var(bool, default=False, required=False)
    url = var(str, required=False)
    web = var(WalletWebConfig, default=WalletWebConfig(), required=False)


@config
class IntegrationConfig:
    """Config type for the integration utilities."""

    broker = var(BrokerConfig)
    payproc = var(DummyPayProcConfig, required=False)
    store = var(DummyStoreConfig, required=False)
    wallet = var(DummyWalletConfig, required=False)


def get_full_config(enable_web=False):
    config = IntegrationConfig(
        broker=BrokerConfig(),
        payproc=DummyPayProcConfig(
            supported_cryptos=['btc', 'xmr', 'nano'],
            destinations=[DummyPayProcConfig.DestinationConfig(
                destination_address=_nano_dest,
                crypto_currency='NANO',
                amount=Decimal("0.01"))],
            keyfile=str(get_tests_dir() /
                        'certificates/root/keys/'
                        'www.brainblocks.com.key'),
            merchant=DummyPayProcConfig.MerchantConfig(
                name='Merchant 1',
                address='5th Avenue')),
        store=DummyStoreConfig(),
        wallet=DummyWalletConfig())
    if enable_web:
        config.payproc.web.enable = True
        config.store.web.enable = True
        config.wallet.web.enable = True
    return config
