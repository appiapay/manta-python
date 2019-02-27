======
 Flow
======

Flow is initiated by Merchant.

Merchant
========

The payment process from the :term:`Merchant`'s point of view:

.. seqdiag::
 :scale: 70

 activation = none;
 Merchant; "Payment Processor"; "MQTT Broker";

 Merchant --> "MQTT Broker" [leftnote="(2) SUBSCRIBE to\n\"acks/{session_id}\""];
 Merchant ->>  "Payment Processor" [leftnote="PUBLISH on\n\"merchant_order_request/{application_id}\"",
                                    label="(3) MerchantOrderRequest"];
 Merchant <<-  "Payment Processor" [rightnote="PUBLISH on\n\"acks/{session_id}\"",
                                    label="(4) Ack[status = new]"];
 Merchant <<-  "Payment Processor" [rightnote="PUBLISH on\n\"acks/{session_id}\"",
                                    label="(5) Ack[status = paid]"];
 Merchant --> "MQTT Broker" [leftnote="(6) UNSUBSCRIBE to\n\"acks/{session_id}\""];

1. :term:`Merchant` generates a random :term:`session_id`.

2. :term:`Merchant` *subscribes* to the topic :ref:`acks/{session_id}`.

3. :term:`Merchant` create a
   `~manta.messages.MerchantOrderRequestMessage`:class: and *publishes* on
   topic `merchant_order_request/{application_id}`:ref:.

   `~manta.messages.MerchantOrderRequestMessage.crypto_currency`:obj:
   field should be empty if customer wants to pay with Manta.

4. :term:`Merchant` *receives* an :class:`~manta.messages.AckMessage` with
   status == "new" on topic :ref:`acks/{session_id}`.

   :term:`Merchant` can create QR code/NDEF Message with URL data

5. :term:`Merchant` *will receive* an
   :class:`~manta.messages.AckMessage` messages as payment changes
   state. With status == "paid" the transaction is completed.

6. :term:`Merchant` *unsubscribes* from the topic
   :ref:`acks/{session_id}`.

Payment Processor
=================

The payment process from the :term:`Payment Processor`'s side:


.. seqdiag::
 :scale: 70

 activation = none;
 Merchant; "Payment Processor"; Wallet; "MQTT Broker";

 "Payment Processor" --> "MQTT Broker" [rightnote="(1a) SUBSCRIBE to\n\"merchant_order_request/+\""]
 "Payment Processor" --> "MQTT Broker" [rightnote="(1a) SUBSCRIBE to\n\"merchant_order_cancel/+\""]
 "Payment Processor" --> "MQTT Broker" [rightnote="PUBLISH on\n\"certificate\"",
                                        label="(1b) Manta CA certificate"]

 === initialization complete ===

 Merchant ->>  "Payment Processor" [leftnote="PUBLISH on\n\"merchant_order_request/{application_id}\"",
                                    label="(2) MerchantOrderRequest"];
 Merchant <<-  "Payment Processor" [rightnote="PUBLISH on\n\"acks/{session_id}\"",
                                    label="(2b) Ack[status = new]"];
 ... crypto_currency == null ...

 "Payment Processor" --> "MQTT Broker" [rightnote="(2c) SUBSCRIBE to\n\"payments/{session_id}\""];
 "Payment Processor" --> "MQTT Broker" [rightnote="(2c) SUBSCRIBE to\n\"payment_requests/{session_id}/+\""];

 "Payment Processor" <<- Wallet [rightnote="(3) PUBLISH on\n\"payment_requests/{session_id}/{crypto_currency}\""];
 "Payment Processor" ->> Wallet [leftnote="PUBLISH on\n\"payment_requests/{session_id}\"",
                                 label="(3a) PaymentRequestEnvelope"];
 "Payment Processor" <<- Wallet [rightnote="PUBLISH on\n\"payments/{session_id}\"",
                                 label="(4a) PaymentMessage"];
 Merchant <<- "Payment Processor" ->> Wallet [rightnote="PUBLISH on\n\"acks/{session_id}\"",
                                              label="(4b) Ack[status = paid]"];

1. When it starts:

   a. it *subscribes* to :ref:`merchant_order_request/+`
      and :ref:`merchant_order_cancel/+` topics;

   b. it *publishes* the Manta CA certificate to :ref:`certificate`
      topic, with retention.

2. On message :class:`~manta.messages.MerchantOrderRequestMessage` on
   a specific :ref:`merchant_order_request/{application_id}` topic:

   a. generates an :class:`~manta.messages.AckMessage` with status ==
      "new". The :attr:`~manta.messages.AckMessage.url` field is in
      manta format if field
      :attr:`~manta.messages.AckMessage.crypto_currency` is null
      (manta protocol), otherwise
      :attr:`~manta.messages.AckMessage.url` format will depend on the
      :attr:`~manta.messages.AckMessage.crypto_currency`;

   b. *publishes* this the :class:`~manta.messages.AckMessage` on the
      :ref:`acks/{session_id}` topic;

   If manta protocol is used:

   c. It *subscribes* to :ref:`payments/{session_id}` and
      :ref:`payment_requests/{session_id}/+` topics.

3. On an event on
   :ref:`payment_requests/{session_id}/{crypto_currency}` without any
   payload:

   a. creates a new
      :class:`~manta.messages.PaymentRequestMessage` and *publishes* it on
      :ref:`payment_requests/{session_id}` wrapped into a
      :class:`~manta.messages.PaymentRequestEnvelope` with retention.

   ``{crypto_currency}`` parameter can be "all" to request multiple
   cryptos.

   Destination should be specific to ``{crypto_currency}`` field.

4. On message (a) :class:`~manta.messages.PaymentMessage` on
   :ref:`payments/{session_id}` it starts monitoring blockchain and on
   progress *publishes* (b) :class:`~manta.messages.AckMessage` on
   :ref:`acks/{session_id}`.


Manta enabled wallet
====================

The payment process from the :term:`Wallet` point of view:

.. seqdiag::
 :scale: 70

 activation = none;
 Wallet; "Payment Processor"; "MQTT Broker";

 Wallet -> Wallet [rightnote="read manta URL"]
 Wallet --> "MQTT Broker" [leftnote="(1) SUBSCRIBE to\n\"payment_requests/{session_id}\""];
 Wallet ->> "Payment Processor" [leftnote="(2) PUBLISH on\n\"payment_request_message/{session_id}/{crypto_currency}\""];
 Wallet <<- "Payment Processor" [leftnote="PUBLISH on\n\"payment_requests/{session_id}\"",
                                 label="(3) PaymentRequest"];
 Wallet ->> "Payment Processor" [leftnote="PUBLISH on\n\"payments/{session_id}\"",
                                 label="(5) Payment"];
 Wallet --> "MQTT Broker" [leftnote="(6) SUBSCRIBE to\n\"acks/{session_id}\""];
 Wallet <<-  "Payment Processor" [rightnote="PUBLISH on\n\"acks/{session_id}\"",
                                  label="(7) Ack[status = paid]"];


1. After receiving a :term:`Manta URL` via QR code or NFC it
   *subscribes* to :ref:`payment_requests/{session_id}`.

2. *Publishes* on :ref:`payment_requests/{session_id}/{crypto_currency}`.

   ``{crypto_currency}`` can be "all" to request multiple cryptos.

3. On :class:`~manta.messages.PaymentRequestMessage` on topic
   :ref:`payment_requests/{session_id}` if
   :attr:`~manta.messages.PaymentRequestMessage.destinations` field does
   not contain desired crypto, check *supported_cryptos* and eventually
   go back to 2).

4. *Verifies* :class:`~manta.messages.PaymentRequestMessage` signature.

5. After payment on blockchain *publishes* a
   :class:`~manta.messages.PaymentMessage` on
   :ref:`payments/{session_id}` topic.

6. *Subscribes* to the topic named :ref:`acks/{session_id}`

7. :term:`Wallet` *will receive* an
   :class:`~manta.messages.AckMessage` messages as payment changes
   state. With status == "paid" the transaction is completed.

Complete Manta flow diagram
===========================

.. figure:: ../images/manta-protocol-full.svg

   Detailed Manta Protocol flow

You can |location_link|.

.. |location_link| raw:: html

   <a href="../_images/manta-protocol-full.svg" target="_blank">Open diagram in new window</a>
