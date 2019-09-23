# -*- coding: utf-8 -*-
# Manta Python
# Manta Protocol Implementation for Python
# Copyright (C) 2018-2019 Alessandro Viganò

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
