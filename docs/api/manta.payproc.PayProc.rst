manta.payproc.PayProc
=====================

This class can be used to create a Manta Payment Processor.

An example using the class is the ``manta.testing.payproc`` module.

Here is an example of the initialization of the :class:`PayProc` class:

.. code-block:: python
   :linenos:

    pp = PayProc(KEYFILE, host="localhost")
    pp.get_merchant = lambda x: MERCHANT
    pp.get_destinations = get_destinations
    pp.get_supported_cryptos = lambda device, payment_request: {'btc', 'xmr', 'nano'}

The lines from 2 to 4 define the callbacks you need to implement.

The class will callback to request information about which Merchant
information to provide, which is the destination address, which
supported crypto currencies.

For example this is how get_destinations can be defined:

.. code-block:: python

   DESTINATIONS = [
       Destination(
           amount=Decimal("0.01"),
           destination_address="xrb_3d1ab61eswzsgx5arwqc3gw8xjcsxd7a5egtr69jixa5it9yu9fzct9nyjyx",
           crypto_currency="NANO"
       ),
   ]

   def get_destinations(application_id, merchant_order: MerchantOrderRequestMessage):
    if merchant_order.crypto_currency:
        destination = next(x for x in DESTINATIONS if x.crypto_currency == merchant_order.crypto_currency)
        return [destination]
    else:
        return DESTINATIONS


Finally you need to start the :term:`MQTT` processing loop which is
started in another thread. To activate it just execute:

.. code-block:: python

   pp.run()


Reference
---------
.. currentmodule:: manta.payproc

.. autoclass:: PayProc
   :members:

