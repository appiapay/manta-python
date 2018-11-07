manta.payproc.PayProc
=====================

This class can be used to create a Manta Payment Processor.

An example using the class is the payprocdummy.py in tests folder.

Initialization of PayProc class:

.. code-block:: python
   :linenos:

    pp = PayProc(KEYFILE, host="localhost")
    pp.get_merchant = lambda x: MERCHANT
    pp.get_destinations = get_destinations
    pp.get_supported_cryptos = lambda device, payment_request: {'btc', 'xmr', 'nano'}

Line 2 to line 4 defines the callbacks you need to implement.

The class will callback to request information about which Merchant information to provide, which is the destination
address, which supported cryptos.

For example this is how get_destinations is defined in Payproc dummy

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

Finally you need to start the main loop (running in another thread):

.. code-block:: python

   pp.run()


Reference
---------
.. currentmodule:: manta.payproc

.. autoclass:: PayProc
   :members:

