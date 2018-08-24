TOPICS
======
MERCHANT_ORDER_REQUEST/{DEVICE_ID}
----------------------------------
**DEVICE_ID** unique POS identifier

**PUBLISHERS** POS

**SUBSCRIBERS** Payment Processor

ACKS/{SESSION_ID}
-----------------
**SESSION_ID** unique Session Identifier

**PUBLISHERS** Payment Processor

**SUBSCRIBERS** POS/ Wallets

PAYMENT_REQUESTS/{SESSION_ID}
-----------------------------
**SESSION_ID** unique Session Identifier

**PUBLISHERS** Payment Processor

**SUBSCRIBERS** Wallets

PAYMENT_REQUESTS/{SESSION_ID}/{CRYPTO_CURRENCY}
-----------------------------------------------
**SESSION_ID** unique Session Identifier

**CRYPTO_CURRENCY** crypto currency

**PUBLISHERS** Wallet

**SUBSCRIBERS** Payment Processor

PAYMENTS/{SESSION_ID}
---------------------
**SESSION_ID** unique Session Identifier

**PUBLISHERS** Wallets

**SUBSCRIBERS** Payment Processor


