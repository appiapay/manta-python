# -*- coding: utf-8 -*-

from __future__ import annotations

from argparse import ArgumentParser, Namespace
import asyncio
from functools import partial
import logging
from typing import Callable, List, Optional

from .broker import launch_mosquitto_from_config
from .config import get_full_config, read_config_file, IntegrationConfig
from .runner import AppRunner
from .payproc import dummy_payproc
from .store import dummy_store
from .wallet import dummy_wallet

logger = logging.getLogger('dummy-runner')


def parse_cmdline(args: List = None) -> Namespace:
    parser = ArgumentParser(description="Run manta-python dummy services")
    parser.add_argument('-c', '--conf', help='path to the configuration file')
    parser.add_argument('--print-config', action='store_true',
                        help='print default config')
    return parser.parse_args(args)


def check_args(parsed_args: Namespace) -> Optional[IntegrationConfig]:
    if parsed_args.print_config:
        print(get_full_config(enable_web=True).dumps_yaml())
    else:
        if not parsed_args.conf:
            print('A path to a configuration file is mandatory.')
            exit(1)
        cfg = read_config_file(parsed_args.conf)
        if cfg.broker is None:
            print('A "broker" section is mandatory.')
            exit(1)
        return cfg
    return None


def init_logging(level=logging.INFO):
    logging.basicConfig(level=level)


def service(name: str, configurator: Callable, config: IntegrationConfig):
    svc_config = getattr(config, name)
    if svc_config is None:
        return partial(null_starter, name), partial(null_stopper, name)
    else:
        return AppRunner.start_stop(configurator, config, name)


def run_services(config: IntegrationConfig, loop=None):
    if loop is None:
        loop = asyncio.get_event_loop()
    with launch_mosquitto_from_config(config.broker, read_log=True) as broker:
        subproc, host, port, log = broker
        # merge possible port reallocation
        config.broker.port = port
        stoppers = []
        for sname, configurator in (('payproc', dummy_payproc),
                                    ('store', dummy_store),
                                    ('wallet', dummy_wallet)):
            start, stop = service(sname, configurator, config)
            loop.run_until_complete(start())
            stoppers.append(stop())
        logger.info("Configured services are now running.")
        logger.info("==================== Hit CTRL-C to stop "
                    "====================")
        try:
            loop.run_forever()
        except KeyboardInterrupt:
            pass
        finally:
            logger.info("==================== Shutting down "
                        "====================")
            loop.run_until_complete(asyncio.wait(stoppers, loop=loop))
            loop.close()


def main(args=None, log_level=logging.INFO):
    config = check_args(parse_cmdline(args))
    if config is not None:
        init_logging(log_level)
        run_services(config)


async def null_starter(name: str):
    logger.info("Not starting service %r", name)


async def null_stopper(name: str):
    pass

if __name__ == '__main__':
    main()
