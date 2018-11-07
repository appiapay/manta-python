FLOW
====
Flow is initiated by Merchant.

.. figure:: ../images/manta-protocol-full.svg

   Detailed Manta Protocol flow

You can |location_link|.

.. |location_link| raw:: html

   <a href="../_images/manta-protocol-full.svg" target="_blank">Open diagram in new window</a>

Merchant
--------
1.  Merchant generates a random SESSION_ID

2.  Merchant *subscribe* to **ACKS/{SESSION_ID}**

3.  Merchant create a **MERCHANT_ORDER_REQUEST_MESSAGE** and *publish* on **MERCHANT_ORDER_REQUEST/{APPLICATION_ID}**

    crypto_currency should be empty if customer wants to pay with Manta

4.  Merchant receives **ACK_MESSAGE** with status == "new"

    Merchant can create QR/NDEF Message with URL data

5.  Merchant will receive ACK messages as payment change status. With *paid* status transaction is finished

Payment Processor
-----------------

1.  Subscribes to **MERCHANT_ORDER_REQUEST/+**

2.  On message **MERCHANT_ORDER_REQUEST/{APPLICATION_ID}**

    Generate **ACK_MESSAGE** with "new" status.
    URL is manta format if crypto_currency is null (manta protocol), otherwise URL will be crypto_currency legacy format

    *publish* on **ACKS/{SESSION_ID}**

    If manta protocol:

    Subscribes to **PAYMENTS/{SESSION_ID}/+**

3.  On message **PAYMENT_REQUEST_MESSAGE/{SESSION_ID}/{CRYPTO_CURRENCY}**

    Creates a new **PAYMENT_REQUEST_MESSAGE** and publish on **PAYMENT_REQUESTS/{SESSION_ID}** with retention

    CRYPTO_CURRENCY can be "all" to request multiple cryptos

    Destination should be specific to {CRYPTO_CURRENCY}

4.  On message **PAYMENTS/{SESSION_ID}**

    Starts monitoring blockchain and on progress publish **ACK_MESSAGE** on **ACKS/{SESSION_ID}**

Manta enabled wallet
--------------------

1.  After receiving QR/NFC manta

    *Subscribe* to **PAYMENT_REQUESTS/{SESSION_ID}**

2.  *Publish* on **PAYMENT_REQUEST/{SESSION_ID}/{CRYPTO_CURRENCY}**

    CRYPTO_CURRENCY can be "all" to request multiple cryptos

3.  On **PAYMENT_REQUEST_MESSAGE**
    If *destinations* does not contain desired crypto, check *supported_cryptos* and eventually go back to 2)

4.  Verify PAYMENT_REQUEST_MESSAGE signature

5.  After payment on blockchain *publish* **PAYMENT_MESSAGE** on **PAYMENTS/{SESSION_ID}**

6.  Subscribe to **ACKS/{SESSION_ID}**