# -*- coding: utf-8 -*-
# Manta Python
# Manta Protocol Implementation for Python
# Copyright (C) 2018-2019 Alessandro Viganò

from __future__ import annotations

import asyncio
import inspect
import logging
import threading
from typing import Awaitable, Callable, Dict, Optional, Tuple, Union

import aiohttp.web

from ..base import MantaComponent
from . import AppRunnerConfig, get_next_free_tcp_port, port_can_be_bound
from .config import IntegrationConfig

logger = logging.getLogger(__name__)


class AppRunner:
    """A tool for running the testing/demo components."""

    "configuration for all the componentss"
    app_config: IntegrationConfig
    loop: asyncio.AbstractEventLoop
    "manta component returned by the configurator"
    manta: Optional[MantaComponent] = None
    thread: Optional[threading.Thread] = None
    "AIOHTTP instance"
    web: Optional[aiohttp.web.Application] = None
    "IP address of the interface of the listening HTTP port"
    web_bind_address: Optional[str] = None
    "port of HTTP listening socket"
    web_bind_port: Optional[int] = None
    url: Optional[str] = None

    @classmethod
    def start_stop(cls, configurator: Callable[[AppRunner],
                                            AppRunnerConfig],
                   app_config: IntegrationConfig,
                   name: str = 'unknown'):
        runner = cls(configurator, app_config)

        async def start():
            res = await runner.start()
            if runner.web is None:
                logger.info("Started service %s", name)
            else:
                logger.info("Started service %s on address %r and port %r",
                            name, runner.web_bind_address,
                            runner.web_bind_port)
            return res

        async def stop():
            res = await runner.stop()
            logger.info("Stopped service %s", name)
            return res

        return start, stop

    def __init__(self, configurator: Callable[[AppRunner],
                                              AppRunnerConfig],
                 app_config: IntegrationConfig):

        "callable used to configure the application"
        self.configurator: Callable[[AppRunner], AppRunnerConfig] = configurator
        self.app_config = app_config

        "the callable used to start the manta app"
        self.starter: Optional[Callable[[], Union[None, Awaitable, bool]]] = None
        "the callable used to stop the manta app"
        self.stopper: Optional[Callable[[], Union[None, Awaitable]]] = None

    def _init_app(self) -> None:
        run_config = self.configurator(self)
        self.manta = run_config.manta
        self.starter = run_config.starter
        self.stopper = run_config.stopper
        if run_config.web_routes is not None:
            assert isinstance(run_config.web_bind_address, str)
            if run_config.web_bind_port is not None \
               and not port_can_be_bound(run_config.web_bind_port,
                                         run_config.web_bind_address) \
               and run_config.allow_port_reallocation:
                run_config.web_bind_port = None
            if run_config.web_bind_port is None:
                if run_config.allow_port_reallocation:
                    run_config.web_bind_port = get_next_free_tcp_port(
                        run_config.web_bind_address)
                else:
                    RuntimeError(f'Cannot bind port {run_config.web_bind_port}')
            web = aiohttp.web.Application()
            web.add_routes(run_config.web_routes)
            self.web = web
            self.web_bind_address = run_config.web_bind_address
            self.web_bind_port = run_config.web_bind_port
            self.url = f'http://{self.web_bind_address}:{self.web_bind_port}'
        else:
            self.web = None
            self.web_bind_address = None
            self.web_bind_port = None
            self.url = None

    def _run(self, *args, **kwargs) -> None:
        started = False
        try:
            loop = self.loop = _get_event_loop()
            self.loop.run_until_complete(self._start(args=args, kwargs=kwargs))
            started = True
            self.loop.run_forever()
            self.loop.stop()
        finally:
            if started:
                self.loop.run_until_complete(self._stop())
            loop.close()

    async def _start(self, *, new_thread: bool = False, args: Tuple = None,
                     kwargs: Dict = None):
        if args is None:
            args = ()
        if kwargs is None:
            kwargs = {}
        self._init_app()
        # setup manta/mqtt
        assert callable(self.starter)
        # TODO: fix the type for proxy invocation
        start_res = self.starter(*args, **kwargs)  # type: ignore
        if inspect.isawaitable(start_res):
            assert start_res is not None  # help mypy
            assert not isinstance(start_res, bool)  # help mypy
            start_res = await start_res
        # setup aiohttp
        if self.web is not None:
            assert isinstance(self.web, aiohttp.web.Application)
            self._runner = aiohttp.web.AppRunner(self.web,
                                                 handle_signals=not new_thread)
            await self._runner.setup()
            self._site = aiohttp.web.TCPSite(self._runner,
                                             self.web_bind_address,
                                             self.web_bind_port)
            await self._site.start()
        return start_res

    async def _stop(self):
        # tear down aiohttp
        if self.web is not None:
            await self._site.stop()
            await self._runner.cleanup()
        # tear down manta/mqtt
        assert callable(self.stopper)
        stop_res = self.stopper()
        if inspect.isawaitable(stop_res):
            await stop_res

    def _stop_thread(self) -> None:
        self.loop.stop()

    def start(self, *args, new_thread: bool = False,
              **kwargs) -> Union[None, Awaitable]:
        "Start the manta application."
        if self.thread is None:
            if new_thread:
                self.thread = threading.Thread(target=self._run, args=args,
                                               kwargs=kwargs)
                self.thread.start()
            else:
                return self._start(args=args, kwargs=kwargs)
        return None

    def stop(self) -> None:
        if self.thread is None:
            return self._stop()
        else:
            self.loop.call_soon_threadsafe(self._stop_thread)
            self.thread.join()
            self.thread = None


def _get_event_loop():
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    return loop


def run_event_loop():
    loop = _get_event_loop()

    async def noop():
        print("======== Running on ========\n"
              "(Press CTRL+C to quit)")
        while True:
            await asyncio.sleep(3600)

    loop.run_until_complete(noop)
