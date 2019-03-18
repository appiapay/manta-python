# -*- coding: utf-8 -*-

from __future__ import annotations

from argparse import ArgumentParser, Namespace
import asyncio
from functools import partial
import logging
from typing import Callable, List, Optional

from .broker import launch_mosquitto_from_config
from . import config
from .runner import AppRunner
from .payproc import dummy_payproc
from .store import dummy_store
from .wallet import dummy_wallet

logger = logging.getLogger('dummy-runner')


def parse_cmdline(args: List = None) -> Namespace:
    parser = ArgumentParser(description="Run manta-python dummy services")
    parser.add_argument('-c', '--conf', help="path to the configuration file")
    parser.add_argument('--print-config', action='store_true',
                        help="print a sample of the default configuration")
    return parser.parse_args(args)


def config_parser_single(parser: ArgumentParser = None,
                         comp_name: str = 'component') -> ArgumentParser:
    if parser is None:
        parser = ArgumentParser(description=f"Run manta-python dummy {comp_name}")
    parser.add_argument('-b', '--broker', default="localhost",
                        help="MQTT broker hostname (default: 'localhost')")
    parser.add_argument('--broker-port', type=int, default=1883,
                        help="MQTT broker port (default: 1883)")
    parser.add_argument('-p', '--web-port', type=int,
                        help="enable web interface on the specified port")
    return parser


def parse_store_cmdline(args: List = None) -> Namespace:
    parser = config_parser_single(comp_name='store')
    return parser.parse_args(args)


def parse_payproc_cmdline(args: List = None) -> Namespace:
    parser = config_parser_single(comp_name='payment processor')
    parser.add_argument('-c', '--conf',
                        help="path of a config file to load")
    parser.add_argument('--print-config', action='store_true',
                        help="print a sample of the default configuration")
    return parser.parse_args(args)


def parse_wallet_cmdline(args: List = None) -> Namespace:
    parser = config_parser_single(comp_name='wallet')
    parser.add_argument('--url', help="Manta-URL of the payment session to join"
                        " and pay. It will automatically end the session when"
                        " payment is completed")
    parser.add_argument('-i', '--interactive', action='store_true',
                        help="enable interactive payment interface (default: False)")
    parser.add_argument('-w', '--wallet',
                        help="hash of the nano wallet to use")
    parser.add_argument('-a', '--account', help="hash of the nano account")
    parser.add_argument('--cert', help="CA certificate used to validate the "
                        "payment session")
    parser.add_argument('-c', '--conf',
                        help="path of a config file to load")
    parser.add_argument('--print-config', action='store_true',
                        help="print a sample of the default configuration")
    return parser.parse_args(args)


def check_args(parsed_args: Namespace) -> Optional[config.IntegrationConfig]:
    if parsed_args.print_config:
        print(config.get_full_config(enable_web=True).dumps_yaml())
    else:
        if not parsed_args.conf:
            print('A path to a configuration file is mandatory.')
            exit(1)
        cfg = config.read_config_file(parsed_args.conf)
        if cfg.broker is None:
            print('A "broker" section is mandatory.')
            exit(1)
        return cfg
    return None


def check_args_store(parsed_args: Namespace) -> Optional[config.IntegrationConfig]:
    web_enable = parsed_args.web_port is not None
    return config.IntegrationConfig(  # type: ignore
        broker=config.BrokerConfig(  # type: ignore
            allow_port_reallocation=False,
            start=False,
            host=parsed_args.broker,
            port=parsed_args.broker_port),
        store=config.DummyStoreConfig(  # type: ignore
            web=config.DummyStoreConfig.StoreWebConfig(  # type: ignore
                enable=web_enable,
                bind_port=parsed_args.web_port,
                allow_port_reallocation=False
            )
        )
    )


def check_args_payproc(parsed_args: Namespace) -> Optional[config.IntegrationConfig]:
    web_enable = parsed_args.web_port is not None
    if parsed_args.print_config:
        print(config.get_default_dummypayproc_config().dumps_yaml())
        return None
    if parsed_args.conf is None:
        pp_conf = config.get_default_dummypayproc_config()
    else:
        pp_conf = config.read_payproc_config_file(parsed_args.conf)
    pp_conf.web = config.DummyPayProcConfig.PayProcWebConfig(  # type: ignore
        enable=web_enable,
        bind_port=parsed_args.web_port,
        allow_port_reallocation=False
    )
    return config.IntegrationConfig(  # type: ignore
        broker=config.BrokerConfig(  # type: ignore
            allow_port_reallocation=False,
            start=False,
            host=parsed_args.broker,
            port=parsed_args.broker_port),
        payproc=pp_conf
    )


def check_args_wallet(parsed_args: Namespace) -> Optional[config.IntegrationConfig]:
    web_enable = parsed_args.web_port is not None
    if parsed_args.print_config:
        print(config.DummyWalletConfig(  # type: ignore
            account="changeme", certificate="changeme",
            wallet="changeme").dumps_yaml())
        return None
    if parsed_args.conf is None:
        wall_conf = config.DummyWalletConfig()
    else:
        wall_conf = config.read_wallet_config_file(parsed_args.conf)
    wall_conf.web = config.DummyWalletConfig.WalletWebConfig(  # type: ignore
        enable=web_enable,
        bind_port=parsed_args.web_port,
        allow_port_reallocation=False
    )
    if parsed_args.account:
        wall_conf.account = parsed_args.account
    if parsed_args.cert:
        wall_conf.certificate = parsed_args.cert
    if parsed_args.wallet:
        wall_conf.wallet = parsed_args.wallet
    if parsed_args.interactive:
        wall_conf.interactive = parsed_args.interactive
    if parsed_args.url:
        wall_conf.url = parsed_args.url
    return config.IntegrationConfig(  # type: ignore
        broker=config.BrokerConfig(  # type: ignore
            allow_port_reallocation=False,
            start=False,
            host=parsed_args.broker,
            port=parsed_args.broker_port),
        wallet=wall_conf
    )


def init_logging(level=logging.INFO):
    logging.basicConfig(level=level)


def service(name: str, configurator: Callable, config: config.IntegrationConfig):
    svc_config = getattr(config, name)
    if svc_config is None:
        return partial(null_starter, name), partial(null_stopper, name)
    else:
        return AppRunner.start_stop(configurator, config, name)


def run_services(config: config.IntegrationConfig, loop=None):
    if loop is None:
        loop = asyncio.get_event_loop()
    with launch_mosquitto_from_config(config.broker, read_log=True) as broker:
        subproc, host, port, log = broker
        # merge possible port reallocation
        config.broker.port = port
        stoppers = []
        started: List[bool] = []
        for sname, configurator in (('payproc', dummy_payproc),
                                    ('store', dummy_store),
                                    ('wallet', dummy_wallet)):
            start, stop = service(sname, configurator, config)
            res = loop.run_until_complete(start())
            # real (non null_*) starters always return a boolean
            if isinstance(res, bool):
                started += [res]
            stoppers.append(stop())
        logger.info("Configured services are now running.")
        logger.info("==================== Hit CTRL-C to stop "
                    "====================")
        try:
            # if res is True the service requested exit after single
            # operation
            if not (len(started) == 1 and started[0] is True):
                loop.run_forever()
        except KeyboardInterrupt:
            pass
        finally:
            logger.info("==================== Shutting down "
                        "====================")
            loop.run_until_complete(asyncio.wait(stoppers, loop=loop))
            loop.close()


def main(args=None, log_level=logging.INFO, check_function: Callable = None,
         parse_function: Callable = None):
    if check_function is None:
        check_function = check_args
    if parse_function is None:
        parse_function = parse_cmdline
    config = check_function(parse_function(args))
    if config is not None:
        init_logging(log_level)
        run_services(config)


store_main = partial(main, check_function=check_args_store,
                     parse_function=parse_store_cmdline)
payproc_main = partial(main, check_function=check_args_payproc,
                       parse_function=parse_payproc_cmdline)
wallet_main = partial(main, check_function=check_args_wallet,
                      parse_function=parse_wallet_cmdline)


async def null_starter(name: str):
    logger.info("Not starting service %r", name)


async def null_stopper(name: str):
    pass

if __name__ == '__main__':
    main()
