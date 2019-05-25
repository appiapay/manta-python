manta.wallet
============

.. automodule:: manta.wallet

   This module implements a basic Manta :term:`Wallet`. An usage
   example of this class can be found in module
   ``manta.testing.wallet``.

   The API is implemented in the :class:`.Wallet` class and
   specifically by the :meth:`.Wallet.get_payment_request` and
   :meth:`.Wallet.send_payment` methods.  The former requests the
   payment details to the :term:`Payment Processor` while the latter
   creates an :class:`~.messages.PaymentMessage` and sends it to the
   :term:`Payment Processor` that is managing the payment process in
   order to complete the payment process.

   To work as expected, an object of the :class:`.Wallet` is created
   using the :meth:`.Wallet.factory` classmethod from a :term:`Manta
   URL`:

   .. code-block:: python3

     import asyncio

     from manta.wallet import Wallet

     wallet = Wallet.factory("manta://developer.beappia.com/774747")

   All the other operations are implemented as *coroutines* and so
   they need an *asyncio loop* to work correctly. The first operation
   needed is to retrieve the payment details:

   .. code-block:: python3

     loop = asyncio.get_event_loop()

     envelope = loop.run_until_complete(wallet.get_payment_request())
     payment_req = envelope.unpack()

   ...then a concrete wallet implementation is supposed to add the
   transaction on the block chain and then send these informations
   back to the :term:`Payment Processor`. We here simulate it with:

   .. code-block:: python3

     loop.run_until_complete(wallet.send_payment(transaction_hash=block, crypto_currency='NANO'))

   Like what happens with the :class:`~.store.Store` class, the
   progress of the payment session can be monitored by looking into
   the :class:`~.messages.AckMessage` instances collected by the
   ``wallet.acks`` queue. The payment is considered complete when a
   received ack has status == ``PAID``:

   .. code-block:: python3

     from manta.messages import Status

     async def wait_for_complete(wallet):
         while True:
             ack = await wallet.acks.get()
             if ack.status is Status.PAID:
                 break
         return ack

     final_ack = loop.run_until_complete(wait_for_complete(wallet))

Reference
---------

.. autoclass:: manta.wallet.Wallet
   :members:
