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

from unittest.mock import MagicMock

from manta.dispatcher import Dispatcher


# def test_dispatcher():
#     d = Dispatcher()
#     m = MagicMock()
#     d.callbacks.append(("^payment_requests/(.*)", m))
#     d.dispatch("payment_requests/leonardo")
#
#     m.assert_called_with("leonardo")


def test_mqtt_to_regex():
    r = Dispatcher.mqtt_to_regex("payment_requests/+")
    assert "payment_requests/([^/]+)$" == r


def test_register_topic():
    d = Dispatcher()
    m = MagicMock()

    @d.topic("payment_requests/+")
    def my_callback(arg1):
        m(arg1)

    d.dispatch("payment_requests/leonardo")
    m.assert_called_with("leonardo")


def test_register_topic_b():
    d = Dispatcher()
    m = MagicMock()

    @d.topic("merchant_order_request/+")
    def my_callback(arg1):
        m(arg1)

    d.dispatch("merchant_order_request/leonardo/123")
    m.assert_not_called()


def test_register_topic_multiple_args():
    d = Dispatcher()
    m = MagicMock()

    assert d.callbacks == []

    @d.topic("payment_requests/+/subtopic/+")
    def my_callback2(*args):
        m(*args)

    d.dispatch("payment_requests/arg1/subtopic/arg2")
    m.assert_called_with("arg1", "arg2")


def test_register_topic_multiple_args_kwargs():
    d = Dispatcher()
    m = MagicMock()

    assert d.callbacks == []

    @d.topic("payment_requests/+/subtopic/+")
    def my_callback2(arg1, arg2, payload):
        m(arg1, arg2, payload)

    d.dispatch("payment_requests/arg1/subtopic/arg2", payload= "my_payload")
    m.assert_called_with("arg1", "arg2", "my_payload")


def test_register_topic_multiple_args_pound():
    d = Dispatcher()
    m = MagicMock()

    assert d.callbacks == []

    @d.topic("payment_requests/+/subtopic/+/subtopic2/#")
    def my_callback3(*args):
        m(*args)

    d.dispatch("payment_requests/arg1/subtopic/arg2/subtopic2/arg3/arg4")
    m.assert_called_with("arg1", "arg2", "arg3", "arg4")


def test_register_in_class():
    m = MagicMock()

    class MyClass():
        def __init__(self):
            self.d = Dispatcher(self)

        @Dispatcher.method_topic("payment_requests/+/subtopic/+")
        def my_method(self, *args):
            m(*args)

    c = MyClass()
    c.d.dispatch("payment_requests/arg1/subtopic/arg2")
    m.assert_called_with("arg1", "arg2")


def test_register_in_class_with_kwargs():
    m = MagicMock()

    class MyClass():
        def __init__(self):
            self.d = Dispatcher(self)

        @Dispatcher.method_topic("payment_requests/+/subtopic/+")
        def my_method(self, arg1, arg2, payload):
            m(arg1, arg2, payload)

    c = MyClass()
    c.d.dispatch("payment_requests/arg1/subtopic/arg2", payload="mypayload")
    m.assert_called_with("arg1", "arg2", "mypayload")
