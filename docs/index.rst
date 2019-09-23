========================================
 Welcome to Manta Python Documentation!
========================================

This is an implementation of the Manta payment protocol for
Python 3. If you want to dive in you may choose to learn first of the
:doc:`protocol` or if you want to try some code, head over to the API
entries for the :doc:`Store <api/manta.store>`, :doc:`Wallet
<api/manta.wallet>` and :doc:`Payment Processor
<api/manta.payproc.PayProc>`.


Requirements
============

This library is compatible only with Python 3.7+. If you want to use
the available testing infrastructure to test your own components you
will need to have mosquitto_ broker (or another :term:`MQTT` broker)
installed.

.. _mosquitto: http://mosquitto.org


Installation
============

To install this library, just type the following commands::

 $ pip install manta-python

or, if you want to use the testing infrastructure, execute instead::

 $ pip install manta-python[runner]


Testing infrastructure
======================

When installed with the testing infrastructure enable, you will find
the command ``manta-runner`` in you execution path. If you have any
problem finding it, you can run the equivalent ``python3 -m
manta.testing``.

The command is meant to take in a configuration file and run the
specified services. A default configuration with all the services
enabled can be obtained running the following command::

 $ manta-runner --print-config

By default this configuration will start the mosquitto_ :term:`MQTT`
broker and all the example components that are used also in the tests,
with their web port enabled:

To setup the services with this configuration, simply execute the
following commands::

  $ manta-runner --print-config > /tmp/demo.yaml
  $ manta-runner -c /tmp/demo.yaml

You will obtain a log like the following::

 INFO:manta.testing.broker:Started Mosquitto broker on interface 'localhost' and port 41627.
 INFO:manta.payproc:Connected with result code 0
 INFO:manta.payproc:Subscribed to 'merchant_order_request/+'
 INFO:manta.payproc:Subscribed to 'merchant_order_cancel/+'
 INFO:manta.testing.runner:Started service payproc on address 'localhost' and port 8081
 INFO:manta.store:Connected
 INFO:manta.testing.runner:Started service store on address 'localhost' and port 8080
 INFO:manta.testing.runner:Started service wallet on address 'localhost' and port 8082
 INFO:dummy-runner:Configured services are now running.
 INFO:dummy-runner:==================== Hit CTRL-C to stop ====================
 INFO:mosquitto:1551282335: New connection from ::1 on port 41627.
 INFO:mosquitto:1551282335: New client connected from ::1 as b9109520-b7af-41bf-99d0-bf2425008bc6 (c1, k60).
 INFO:mosquitto:1551282335: New connection from ::1 on port 41627.
 INFO:mosquitto:1551282335: New client connected from ::1 as 066284b2-e8c7-41aa-9595-3432b12665a2 (c1, k60).

Like specified in the log, hit *CTRL-C* (or the equivalent keyboard
combination that generates a ``KeyboardInterrupt`` exception on your
OS) to teardown the services.

The configured services are automatically started and connected to the
port exposed by the broker. If enabled (as it is by default) each
configured service exposes a web service that can be used to execute
key APIs of each. To know what the entrypoints are you have (for now)
to look into the files in the ``manta.testing`` subpackage or to look
into the tests in the `github repository`_.

.. _github repository: https://github.com/appiapay/manta-python

Single component runners
~~~~~~~~~~~~~~~~~~~~~~~~

To ease the development of new components this library installs in
your path executables to run the individual components, they are named
``manta-store``, ``manta-payproc`` and ``manta-wallet``. They are
implemented by the same code of the collective runner but they offer a
different user interface with more commandline arguments, e.g.::

 $ manta-wallet --help
 usage: manta-wallet [-h] [-b BROKER] [--broker-port BROKER_PORT] [-p WEB_PORT]
                     [--url URL] [-i] [-w WALLET] [-a ACCOUNT] [--cert CERT]
                     [-c CONF] [--print-config]

 Run manta-python dummy wallet

 optional arguments:
   -h, --help            show this help message and exit
   -b BROKER, --broker BROKER
                         MQTT broker hostname (default: 'localhost')
   --broker-port BROKER_PORT
                         MQTT broker port (default: 1883)
   -p WEB_PORT, --web-port WEB_PORT
                         enable web interface on the specified port
   --url URL             Manta-URL of the payment session to join and pay. It
                         will automatically end the session when payment is
                         completed
   -i, --interactive     enable interactive payment interface (default: False)
   -w WALLET, --wallet WALLET
                         hash of the nano wallet to use
   -a ACCOUNT, --account ACCOUNT
                         hash of the nano account
   --cert CERT           CA certificate used to validate the payment session
   -c CONF, --conf CONF  path of a config file to load
   --print-config        print a sample of the default configuration

All three expect for the broker to be up and running
already. ``manta-payproc`` and ``manta-wallet`` accept also a specific
configuration file, please use the ``--print-config`` option to get a
sample of that file.

Tests
=====

To run the tests you have to run the following commands::

 $ git git@github.com:appiapay/manta-python.git
 $ cd manta-python
 $ pip install -r requirements-dev.txt

Be aware that the same requirements specified for the `Testing
Infrastructure`_ apply here too. If you want to use your own
:term:`MQTT` broker you will have to modify the ``broker.start`` entry
in the file ``tests/dummyconfig.yaml`` to ``false``.

Then simply run::

 $ make tests

or, if ``make`` isn't available on your platform, just run::

 $ pytest

..  toctree::
    :maxdepth: 3
    :caption: Contents:

    protocol
    api

Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`
