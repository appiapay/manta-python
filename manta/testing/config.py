# -*- coding: utf-8 -*-
# Manta Python
# Manta Protocol Implementation for Python
# Copyright (C) 2018-2019 Alessandro Viganò

from decimal import Decimal
import io
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
    destinations = var(List[DestinationConfig], min=1)  # type: ignore
    keyfile = var(str)
    certfile = var(str)
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


def get_default_dummypayproc_config():
    return DummyPayProcConfig(
        supported_cryptos=['btc', 'xmr', 'nano'],
        destinations=[DummyPayProcConfig.DestinationConfig(
            destination_address=_nano_dest,
            crypto_currency='NANO',
            amount=Decimal("0.01"))],
        keyfile=str(get_tests_dir() /
                    'certificates/root/keys/'
                    'test.key'),
        certfile=str(get_tests_dir() /
                    'certificates/root/certs/'
                    'test.crt'),
        merchant=DummyPayProcConfig.MerchantConfig(
            name='Merchant 1',
            address='5th Avenue'))


def get_full_config(enable_web=False):
    config = IntegrationConfig(
        broker=BrokerConfig(),
        payproc=get_default_dummypayproc_config(),
        store=DummyStoreConfig(),
        wallet=DummyWalletConfig())
    if enable_web:
        config.payproc.web.enable = True
        config.store.web.enable = True
        config.wallet.web.enable = True
    return config


def read_config_file(path: str) -> IntegrationConfig:
    """Read a file containing a configuration and return a config object."""
    return IntegrationConfig.load_yaml(io.open(path, encoding='utf-8'))  # type: ignore


def read_payproc_config_file(path: str) -> DummyPayProcConfig:
    """Read a file containing a configuration and return a config object."""
    return DummyPayProcConfig.load_yaml(io.open(path, encoding='utf-8'))  # type: ignore


def read_wallet_config_file(path: str) -> DummyWalletConfig:
    """Read a file containing a configuration and return a config object."""
    return DummyWalletConfig.load_yaml(io.open(path, encoding='utf-8'))  # type: ignore
