Parameters
==========

.. glossary::

 application_id
   Unique :term:`POS` identifier.

 crypto_currency
   Name of the currency used to complete the monetary transaction.

 session_id
   Unique Session Identifier.

 Manta URL
   It's an Uniform Resource Locator of the Session initiated by the
   :term:`POS` and it's shared with the :term:`Wallet` via means like
   QR code or NFC.

   it's encoded as:

   manta://<*broker_host*>[:<*broker_port*>]/<*session_id*>

   where ``broker_host`` and ``broker_port`` are the IP address and
   TCP port where the broker service is listening.
