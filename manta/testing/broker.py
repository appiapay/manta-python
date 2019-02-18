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

from contextlib import contextmanager
import tempfile
from typing import Optional

from . import get_next_free_tcp_port, launch_program, port_can_be_bound
from .config import BrokerConfig

DEFAULT_MQTT_PORT = 1883

MOSQUITTO_CONF = """\
bind_address {}
port {}
persistence false
"""


@contextmanager
def launch_mosquitto(bind_address: str = 'localhost',
                     bind_port: Optional[int] = None,
                     exec_path: Optional[str] = None,
                     allow_port_reallocation: bool = True):
    """Launch mosquitto executable, providing it a minimal configuration useful
    for testing purposes.

    It's intended to be used in a ``with`` statement

    Args:
        bind_address: optional interface address
        bind_port: optional listening port. If none is specified, one will be
          allocated
        exec_path: optional path to the mosquitto executable
    Yields
        A tuple containing four elements::

          (<popen object>, <bind_address>, <listening port>, <process_output>)
    """
    if bind_port is None:
        bind_port = DEFAULT_MQTT_PORT
    if not port_can_be_bound(bind_port, bind_address) and allow_port_reallocation:
        bind_port = get_next_free_tcp_port(bind_address)
    elif (not port_can_be_bound(bind_port, bind_address)
          and not allow_port_reallocation):
        raise RuntimeError(f"Port '{bind_port}' cannot be bound on {bind_address}")
    if exec_path is None:
        exec_path = 'mosquitto'

    with tempfile.NamedTemporaryFile(suffix='.conf') as config:
        config.write(MOSQUITTO_CONF.format(bind_address, bind_port).encode('utf-8'))
        config.flush()

        with launch_program([exec_path, '-c', config.name],
                            b'mosquitto version.*starting') as daemon:
            process, out = daemon
            yield (process, bind_address, bind_port, out)


@contextmanager
def launch_mosquitto_from_config(cfg: BrokerConfig):
    """Given a configuration instance, start a broker process.

    Args:
        cfg: a configuration instance
    Yields
        A tuple containing four elements if :any:`cfg.start` is True::

          (<popen object>, <bind_address>, <listening port>, <process_output>)
    """
    if cfg.start:
        with launch_mosquitto(
                bind_address=cfg.host, bind_port=cfg.port, exec_path=cfg.path,
                allow_port_reallocation=cfg.allow_port_reallocation) as mos:
            yield mos
    else:
        yield (None, cfg.host, cfg.port, None)
