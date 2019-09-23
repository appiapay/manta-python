# Manta Python
# Manta Protocol Implementation for Python
# Copyright (C) 2018-2019 Alessandro Viganò

import os
import pathlib
import pytest

pytest.register_assert_rewrite("tests.utils")

# it's a fixture used in the tests
from .utils import mock_mqtt # noqa E402


@pytest.fixture(scope='session')
def tests_dir():
    return pathlib.Path(os.path.dirname(os.path.realpath(__file__)))


@pytest.fixture(scope='session')
def config_str(tests_dir):
    config_file = open(tests_dir / 'dummyconfig.yaml')
    return config_file.read()


@pytest.fixture(scope='session',
                params=[pytest.param(False, id='direct'),
                        pytest.param(True, id='web')])
def config(request, config_str):
    from manta.testing.config import IntegrationConfig

    config = IntegrationConfig.loads_yaml(config_str)
    enable_web = request.param
    if enable_web:
        config.payproc.web.enable = True
        config.store.web.enable = True
        config.wallet.web.enable = True
    return config


@pytest.fixture(scope='session')
def broker(config):
    from manta.testing.broker import launch_mosquitto_from_config

    with launch_mosquitto_from_config(config.broker) as connection_data:
        # listening config may have changed due to automatic
        # reallocation in case some other process is listening already
        _, host, port, _ = connection_data
        config.broker.host = host
        config.broker.port = port
        yield connection_data


@pytest.fixture(scope='function')
async def dummy_store(config, broker):
    from manta.testing.runner import AppRunner
    from manta.testing.store import dummy_store

    runner = AppRunner(dummy_store, config)
    await runner.start()
    yield runner
    await runner.stop()


@pytest.fixture(scope='function')
async def dummy_wallet(config, broker):
    from manta.testing.runner import AppRunner
    from manta.testing.wallet import dummy_wallet

    runner = AppRunner(dummy_wallet, config)
    await runner.start()
    # wallet start() adds pay() method to  the runner
    yield runner
    await runner.stop()


@pytest.fixture(scope='function')
async def dummy_payproc(config, broker):
    from manta.testing.runner import AppRunner
    from manta.testing.payproc import dummy_payproc

    runner = AppRunner(dummy_payproc, config)
    await runner.start()
    yield runner
    await runner.stop()


@pytest.fixture()
def web_get(event_loop):
    import functools
    import requests

    def get(*args, **kwargs):
        return event_loop.run_in_executor(
            None, functools.partial(requests.get, **kwargs), *args)
    return get

@pytest.fixture()
def web_post(event_loop):
    import functools
    import requests

    def post(*args, **kwargs):
        return event_loop.run_in_executor(
            None, functools.partial(requests.post, **kwargs), *args)
    return post
