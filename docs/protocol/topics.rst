Topics
======

.. _acks/{session_id}:

acks/{session_id}
-----------------
:parameters: :term:`session_id`
:publishers: :term:`Payment Processor`
:subscribers: :term:`Merchant`, :term:`Wallet`

Used by the :term:`Payment Processor` to publish
:class:`~manta.messages.AckMessage`: it serves the purpose of
informing the other parties of the :class:`~manta.messages.Status` and
other primary data of the session.

.. _merchant_order_cancel/+:
.. _merchant_order_cancel/{session_id}:

merchant_order_cancel/{session_id}
----------------------------------
:parameters: :term:`session_id`
:publishers: :term:`Merchant`
:subscribers: :term:`Payment Processor`

TBD

.. _merchant_order_request/+:
.. _merchant_order_request/{application_id}:

merchant_order_request/{application_id}
---------------------------------------
:parameters: :term:`application_id`
:publishers: :term:`Merchant`
:subscribers: :term:`Payment Processor`

Used by the :term:`Merchant` to initiate a new session by publishing a
:class:`~manta.messages.MerchantOrderRequestMessage`.

.. _payment_requests/{session_id}:

payment_requests/{session_id}
-----------------------------
:parameters: :term:`session_id`
:publishers: :term:`Payment Processor`
:subscribers: :term:`Wallet`

It's where the :term:`Payment Processor` publishes a
:class:`~manta.messages.PaymentRequestEnvelope` in response to an
event on the topic
:ref:`payment_requests/{session_id}/{crypto_currency}` published by
the :term:`Wallet`.

.. _payment_requests/{session_id}/+:
.. _payment_requests/{session_id}/{crypto_currency}:

payment_requests/{session_id}/{crypto_currency}
-----------------------------------------------
:parameters: :term:`session_id`, :term:`crypto_currency`
:publishers: :term:`Wallet`
:subscribers: :term:`Payment Processor`

Used by the :term:`Wallet` to get informations about the
payment. ``{crypto_currency}`` parameter can be "all" to request
multiple cryptos.

.. _payments/{session_id}:

payments/{session_id}
---------------------
:parameters: :term:`session_id`
:publishers: :term:`Wallet`
:subscribers: :term:`Payment Processor`

It's where the :term:`Wallet` publishes informations about the
successful monetary transaction encoded as a
:class:`~manta.messages.PaymentMessage`.

.. TODO: possibly document ``certificate`` topic and payload
