==========
 Messages
==========

Messages are object that are use used to store and communicate the
data of the :term:`Merchant` order and the correspondent
:term:`Wallet` payment. They are serialize to/from term:`JSON` for
transmission using :term:`MQTT` protocol.

Ack
===
.. autoclass:: manta.messages.AckMessage
.. autoclass:: manta.messages.Status
    :members:

Merchant Order Request
======================
.. autoclass:: manta.messages.MerchantOrderRequestMessage

Payment Request Message
=======================
.. autoclass:: manta.messages.PaymentRequestMessage
.. autoclass:: manta.messages.Merchant
.. autoclass:: manta.messages.Destination
.. autoclass:: manta.messages.PaymentRequestEnvelope

Payment
=======
.. autoclass:: manta.messages.PaymentMessage
