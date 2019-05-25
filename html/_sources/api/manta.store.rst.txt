manta.store
===========

.. automodule:: manta.store

   This module implements a basic Manta :term:`Merchant`. An usage example of
   this class can be found in module ``manta.testing.store``.

   The API is implemented in the :class:`.Store` class and
   specifically by the :meth:`.Store.merchant_order_request` method
   that creates an :class:`~.messages.MerchantOrderRequestMessage` and
   sends it to the :term:`Payment Processor` that is managing the payment
   process.

   In order to work correctly, the class needs to be instantiated and
   connected to the :term:`MQTT` broker. This is implemented using an
   *asyncio* coroutine:

   .. code-block:: python3

     import asyncio

     from manta.store import Store

     store = Store('example_store', host='example.com')

     loop = asyncio.get_event_loop()
     loop.run_until_complete(store.connect())


   Then the a new order needs to be created:

   .. code-block:: python3

     ack = loop.run_until_complete(store.merchant_order_request(amount=10, fiat='eur'))

     ack.url  # contains the Manta URL

   When that is done, the :term:`Manta URL` needs to be transmitted to
   the :term:`Wallet` to pay, but this is out of the scope of this
   code. From the Merchant point of view the progress of the payment
   transaction can be monitored by looking into the
   :class:`~.messages.AckMessage` instances collected by the
   ``store.acks`` queue. The payment is considered complete when a
   received ack has status == ``PAID``:

   .. code-block:: python3

     from manta.messages import Status

     async def wait_for_complete(store):
         while True:
             ack = await store.acks.get()
             if ack.status is Status.PAID:
                 break
         return ack

     final_ack = loop.run_until_complete(wait_for_complete(store))

Reference
---------

.. autoclass:: manta.store.Store
   :members:
