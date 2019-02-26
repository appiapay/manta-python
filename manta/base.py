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

from abc import ABC, abstractmethod

import paho.mqtt.client as mqtt


class MantaComponent(ABC):
    """A base class where the common properties of PayProc, Store and Wallet are
    specified."""

    "The Manta protocol broker host"
    host: str
    "The mqtt client instance used for communication"
    mqtt_client: mqtt.Client
    "The Manta protocol broker port"
    port: int

    @abstractmethod
    def on_connect(self, client: mqtt.Client, userdata, flags, rc):
        pass

    @abstractmethod
    def on_message(self, client: mqtt.Client, userdata, msg):
        pass
