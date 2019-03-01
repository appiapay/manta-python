# -*- coding: utf-8 -*-

import pytest

from manta.testing import AppRunnerConfig


@pytest.mark.asyncio
async def test_basic_configuration(config):
    from manta.testing.runner import AppRunner

    d = dict(start=False, stop=False)

    def configurator(runner):

        def starter():
            nonlocal d
            d['start'] = True

        def stopper():
            nonlocal d
            d['stop'] = True

        return AppRunnerConfig(starter=starter, stopper=stopper)

    runn = AppRunner(configurator, config)
    assert not d['start']
    assert not d['stop']

    await runn.start()
    assert d['start']

    await runn.stop()
    assert d['stop']


def test_basic_configuration_other_thread(config, event_loop):
    import time
    import _thread
    from manta.testing.runner import AppRunner

    d = dict(start=False, stop=False, ident=_thread.get_ident(),
             start_ident=None, stop_ident=None)

    def configurator(runner):

        def starter():
            nonlocal d
            d['start'] = True
            d['start_ident'] = _thread.get_ident()

        def stopper():
            nonlocal d
            d['stop'] = True
            d['stop_ident'] = _thread.get_ident()

        return AppRunnerConfig(starter=starter, stopper=stopper)

    runn = AppRunner(configurator, config)
    assert not d['start']
    assert not d['stop']

    async def run():
        await runn.start()
        await runn.stop()

    event_loop.run_until_complete(run())

    assert d['start']
    assert d['stop']

    assert d['ident'] == d['start_ident'] and d['start_ident'] == d['stop_ident']

    d = dict(start=False, stop=False, ident=_thread.get_ident(),
             start_ident=None, stop_ident=None)
    assert not d['start']
    assert not d['stop']

    runn.start(new_thread=True)
    time.sleep(0.2)
    runn.stop()
    assert d['start']
    assert d['stop']

    assert d['ident'] != d['start_ident'] and d['start_ident'] == d['stop_ident']


def test_basic_configuration_coro(config, event_loop):
    from manta.testing.runner import AppRunner

    d = dict(start=False, stop=False)

    def configurator(runner):

        def starter():
            nonlocal d

            async def start_coro():
                nonlocal d
                d['start'] = True

            return start_coro()

        def stopper():
            nonlocal d
            d['stop'] = True

            async def stop_coro():
                nonlocal d
                d['stop'] = True

            return stop_coro()

        return AppRunnerConfig(starter=starter, stopper=stopper)

    runn = AppRunner(configurator, config)
    assert not d['start']
    assert not d['stop']

    event_loop.run_until_complete(runn.start())
    assert d['start']

    event_loop.run_until_complete(runn.stop())
    assert d['stop']


@pytest.mark.asyncio
async def test_web_responsiveness(config, web_get):
    import aiohttp
    import requests

    from manta.testing.runner import AppRunner

    def configurator(runner):

        routes = aiohttp.web.RouteTableDef()
        d = dict(web_get=False)

        @routes.get('/test')
        async def web_test(request):
            nonlocal d
            d['web_get'] = True
            return aiohttp.web.json_response("ok")

        def starter():
            pass

        def stopper():
            pass

        return AppRunnerConfig(starter=starter, stopper=stopper,
                               web_routes=routes,
                               allow_port_reallocation=True,
                               web_bind_address='localhost',
                               web_bind_port=9000)

    runn = AppRunner(configurator, config)

    await runn.start()

    resp = await web_get(runn.url + '/test')
    assert 'ok' in resp.text

    await runn.stop()
