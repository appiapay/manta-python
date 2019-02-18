# -*- coding: utf-8 -*-
# Manta Python
# Manta Protocol Implementation for Python
# Copyright (C) 2018 xxx
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

from __future__ import annotations

from contextlib import closing, contextmanager
from decimal import Decimal
import os
import re
import pathlib
import socket
import subprocess
import sys
import time
from typing import (Any, Awaitable, Callable, Iterator, Optional, Sequence,
                    Tuple, Union)

import aiohttp.web
import attr
import file_config


from ..base import MantaComponent


def get_next_free_tcp_port(bind_address: str = 'localhost') -> int:
    """Return the next free TCP port on the ``bind_address`` interface.

    Args:
        bind_address: optional *name* or *IP address* of the interface where
          the free port need to be looked up. If not specified, ``localhost``
          will be used
    Returns:
        The found port number
    """
    with closing(socket.socket()) as sock:
        sock.bind((bind_address, 0))
        return sock.getsockname()[1]


def port_can_be_bound(port: int, bind_address: str = 'localhost') -> bool:
    """Returns true if a given port can be bound for listening.

    Args:
        port: the port to check
        bind_address: optional IP address of the interface where to bind the
          port to. If not specified, ``localhost`` will be used
    Returns
        A boolean that will be ``True`` if the port can be bound
    """
    with closing(socket.socket()) as sock:
        try:
            sock.bind((bind_address, port))
            result = True
        except OSError:
            result = False
    return result


def start_program(args: Sequence[str], sentinel: bytes,
                  log_stream: str = 'stderr',
                  timeout: int = 5) -> Tuple[subprocess.Popen, bytearray]:
    """Start a program and check if it launched as expected.

    Args:
        args: a sequence of the program and its arguments
        sentinel: bytes string to lookup in the ``log_stream``. It can be
          a *regexp*
        log_stream: optional name of the stream where to look for the sentinel.
          Valid values are ``stdout`` and ``stderr``. if not specified
          ``stderr`` will be used
        timeout: optional amount of time to wait for the ``sentinel`` to
          be found in the ``log_stream``
    Returns:
        a tuple with the following elements: ``(<process>, <log_stream>)``
    """
    assert log_stream in ('stdout', 'stderr')
    stream_cfg = {log_stream: subprocess.PIPE}

    process = subprocess.Popen(args, **stream_cfg) # type: ignore

    stream = getattr(process, log_stream)
    if sys.platform in ('linux', 'darwin'):
        # set the O_NONBLOCK flag of p.stdout file descriptor
        # don't know what to do for the Windows platform
        from fcntl import fcntl, F_GETFL, F_SETFL
        flags = fcntl(stream, F_GETFL)
        fcntl(stream, F_SETFL, flags | os.O_NONBLOCK)

    out = bytearray()
    attempts = 0
    seconds = 0.2
    max_attempts = int(timeout) / seconds
    while attempts < max_attempts:
        attempts += 1
        time.sleep(seconds)

        try:
            o = os.read(stream.fileno(), 256)
            if o:
                out += o
        except BlockingIOError:
            pass

        if re.search(sentinel, out):
            break
    else:
        process.kill()
        raise RuntimeError(
            f'{args[0]} failed to start or startup detection'
            f'failed, after {timeout} seconds:\n'
            f'log_stream:\n{out.decode()}\n')
    return (process, out)


@contextmanager
def launch_program(args: Sequence[str], sentinel: bytes,
                   log_stream: str = 'stderr',
                   timeout: int = 5) -> Iterator:
    """Launch a program and check if it launched as expected. To be used in
    **with** statement expressions. Kills the subprocess at the end.

    Arguments are the same of :function:`start_program`

    Yields:
        a tuple with the following elements: ``(<process>, <log_stream>)``
    """
    process, log = start_program(args, sentinel, log_stream, timeout)
    yield (process, log)
    process.kill()


def msg2config(cls: str, suffix: str = 'Config') -> Any:
    """Convert a Message class coming from :module:`manta.messages` module to a
    config class."""
    assert isinstance(cls, type) and hasattr(cls, '__attrs_attrs__'), \
        'Wrong class type'
    aattrs = getattr(cls, '__attrs_attrs__')

    def gen_var(att: attr.Attribute) -> attr.Attribute:
        t = att.type
        added_opts = {}
        # take the first not-None type if t is an Union type
        if getattr(t, '__origin__', None) is Union:
            for type_choice in t.__args__:
                # isinstance() cannot be used with typing.*
                if type_choice is not type(None):
                    t = type_choice
                    break
            else:
                raise ValueError(f'Cannot extrapolate valid type from {t!r}')
        # Setup a special encoder/decoder pair for Decimal type that
        # isn't supported directly by (py)YAML
        if t is Decimal:
            added_opts['encoder'] = lambda v: f'{v!s}'
            added_opts['decoder'] = lambda v: Decimal(v)
        if 'type' not in added_opts:
            added_opts['type'] = t
        return file_config.var(default=att.default, **added_opts)

    ns = {a.name: gen_var(a) for a in aattrs}
    return file_config.config(type(cls.__name__ + suffix, (), ns))


def config2msg(config_inst: Any, msg_cls: Any):
    """Convert a configuration instance to a specific message type."""
    return msg_cls(**{a.name: getattr(config_inst, a.name)
                      for a in msg_cls.__attrs_attrs__})


@attr.s(auto_attribs=True)
class AppRunnerConfig:
    """Configuration exchanged between the configurator and an AppRunner."""

    "callable used to ``start`` the Manta component"
    starter: Callable[[MantaComponent], Union[None, Awaitable]]
    "callable used to ``stop`` the Manta component"
    stopper: Callable[[MantaComponent], Union[None, Awaitable]]
    "the configured Manta component"
    manta: MantaComponent = None
    "``True`` if binding port reallocation is allowed"
    allow_port_reallocation: Optional[bool] = True
    "interface address where the listening port should be bound to"
    web_bind_address: Optional[str] = 'localhost'
    "which port number to bind"
    web_bind_port: Optional[int] = None
    """routes that the web server should allow"""
    web_routes: Optional[aiohttp.web_routedef.RouteTableDef] = None


def get_tests_dir():
    here = pathlib.Path(os.path.dirname(os.path.realpath(__file__)))
    return here / '..' / '..' / 'tests'
