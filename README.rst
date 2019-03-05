.. -*- coding: utf-8 -*-

=========================
 Welcome to manta-python
=========================

This repository contains the Python implementation of the **Manta
Protocol**: it's a protocol to enable crypto coin transaction between
POS (of any kind, hardware, vending machines, online), payment
processors and wallets.

Communication takes advantage of the MQTT_ protocol and needs a
proper configured broker to work.

More documentation can be found at
https://nanoray.github.io/manta-python, what follows are some
instructions for the developer.

.. _MQTT: http://mqtt.org

.. contents::

Installation
============

Primary repository
------------------

To start working on ``manta-python`` you must first checkout a copy of the
main repository::

 $ git git@github.com:NanoRay/manta-python.git
 $ cd manta-python

Requirements
------------

The code in this repository needs an MQTT_ broker to work correctly so
if you plan to run the tests, you will be required of either install
the mosquitto_ broker or use your own and modify the ``broker.start``
entry in the file ``tests/dummyconfig.yaml`` to ``false``.

.. _mosquitto: http://mosquitto.org

Task automation is achieved using `GNU Make`_. It should be easily
installable on every UNIX-like platform.

If you use Nix__ (it can be installed on GNU/Linux systems and
macOS) all you need is to execute a single command::

 $ nix-shell

and that will install mosquitto_ and `GNU Make`_ for you. In such case
you should skip the following section.

.. _GNU Make: https://www.gnu.org/software/make/
__ https://nixos.org/nix/

Creation of the Python virtual environment
------------------------------------------

The next thing to do is the creation of the Python virtual environment
with some required packages. Simply execute::

 $ make

a) that will initialize the environment with a set of required packages
b) print an help on the available targets

You **must** remember to activate the virtual environment **before**
doing anything::

 $ . venv/bin/activate

Running the tests
-----------------

To run the tests simply run the following command::

 $ make tests

That will run the unit tests and the integration tests. Remember to always use
it before committing.
