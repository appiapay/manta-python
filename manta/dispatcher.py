from __future__ import annotations
import re
from dataclasses import dataclass, field
from typing import List, Callable, Tuple, Dict, Type
import inspect


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


