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

.. _github repository: https://github.com/NanoRay/manta-python

Tests
=====

To run the tests you have to run the following commands::

 $ git git@github.com:NanoRay/manta-python.git
 $ cd manta-python
 $ pip install -r requirements-dev.txt

Be aware that the same requirements specified for the `Testing
Infrastructure`_ apply here too. If you want to use your own
:term:`MQTT` broker you will have to modify the ``broker.start`` entry
in the file ``tests/dummyconfig.yaml`` to ``false``.

Then simply run::

 $ make tests

or, if ``make`` isn't available on your platform::

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
