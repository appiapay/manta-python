# Manta Python
# Manta Protocol Implementation for Python
# Copyright (C) 2018 Alessandro Viganò
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

import inspect
import re
from typing import List, Callable, Tuple


class Dispatcher:
    callbacks: List[Tuple[str, Callable]] = []

    def __init__(self, obj: object= None):
        self.callbacks = []

        if obj is None:
            return

        for cls in inspect.getmro(obj.__class__): #Register all subclasses methods
            for key, value in cls.__dict__.items():
                if inspect.isfunction(value):
                    if hasattr(value, "dispatcher"):
                        self.callbacks.append((value.dispatcher, value.__get__(obj)))

    def dispatch(self, topic: str, **kwargs):
        for callback in self.callbacks:
            result = re.match(callback[0], topic)
            if result:
                groups = result.groups()
                args = list(groups[:-1])
                #To match #
                args = args + groups[-1].split("/")
                callback[1](*args, **kwargs)

    @staticmethod
    def mqtt_to_regex(topic: str):
        # escaped = re.escape(topic)

        return topic.replace("+", "([^/]+)").replace("#", "(.*)")+"$"

    @staticmethod
    def method_topic(topic):
        def decorator(f: Callable):
            f.dispatcher = Dispatcher.mqtt_to_regex(topic)
            return f

        return decorator

    def topic(self, topic):
        def decorator(f: Callable):
            self.callbacks.append((Dispatcher.mqtt_to_regex(topic), f))
            return f

        return decorator


