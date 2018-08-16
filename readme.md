# Manta Protocol
Manta Protocol is a protocol to enable crypto transactions between POS (hw POS, vending machines, online), payment processors and wallets

Communications are handled through a MQTT broker.

## FLOW
### POS

Flow is initiated by POS.

1. POS generates a random SESSION_ID
2. POS *subscribe* to **GENERATE_PAYMENT_REQUEST/{DEVICE_ID}/REPLY**
3. POS *subscibe* to **ACKS/{SESSION_ID}**
4. POS create a **GENERATE_PAYMENT_REQUEST_MESSAGE** and *publish* on **GENERATE_PAYMENT_REQUEST/{DEVICE_ID}/REQUEST**

   crypto_currency should be empty if customer wants to pay with Manta 

5. POS receives **GENERATE_PAYMENT_REPLY**
   
   If it's Manta TX address will be empty and wallet should generate QR/NFC in manta format.

   If not Manta address will contain crypto destination address and QR/NFC will be in legacy format

6. POS will receive ACK messages as payment change status. With *paid* status transaction is finished

### Payment Processor

1. Subscribes to **GENERATE_PAYMENT_REQUEST/+/REQUEST**
2. On message **GENERATE_PAYMENT_REQUEST/{DEVICE_ID}/REQUEST**
   
   Creates **PAYMENT_REQUEST_MESSAGE** and publish on **PAYMENT_REQUESTS/{SESSION_ID}** with retention. Message is signed.

   If the payment processor can fill immediately destinations to the wallet or can provide destination address later. In latter case supported_cryptos must be filled

   Subscribes to **PAYMENT_REQUEST_MESSAGE/{SESSION_ID}/+**
   Subscribes to **PAYMENTS/{SESSION_ID}/**

3. On message **PAYMENT_REQUEST_MESSAGE/{SESSION_ID}/{CRYPTO_CURRENCY}
   
   Creates a new **PAYMENT_REQUEST_MESSAGE** and publish on **PAYMENT_REQUESTS/{SESSION_ID}** with retention

   Destination should be specific to {CRYPTO_CURRENCY}

4. On message **PAYMENTS/{SESSION_ID}**

   Starts monitoring blockchain and on progress publish **ACK_MESSAGE** on **ACKS/{SESSION_ID}**

### Manta enabled wallet

1. After receiving QR/NFC manta
   Subscribes to **PAYMENT_REQUESTS/{SESSION_ID}**
   If destinations are empty should publish to **PAYMENT_REQUEST/{SESSION_ID}/{CRYPTO_CURRENCY} where CRYPTO_CURRENCY is chosen crypto
2. Verify PAYMENT_REQUEST_MESSAGE signature
3. After payment on blockchain publish **PAYMENT_MESSAGE** on **PAYMENTS/{SESSION_ID}**
4. Subscribe to **ACKS/{SESSION_ID}**

## MESSAGES
### GENERATE_PAYMENT_REQUEST
``` python
class GeneratePaymentRequestMessage(NamedTuple):
    amount: float
    session_id: str
    fiat_currency: str
    crypto_currency: str
```

| attribute       | type | description                                  |
| --------------- | ---- | -------------------------------------------- |
| amount          | str  | Fiat Amount                                  |
| fiat_currency   | str  | Fiat Currency type (EUR, USD...)             |
| session_id      | str  | Random generated session identifier          |
| crypto_currency | str  | Crypto currency desired. Empty for Manta TXS |

**amount** Fiat Amount

**session_id**

### GENERATE_PAYMENT_REPLY

| attribute       | type | description                                     |
| --------------- | ---- | ----------------------------------------------- |
| status          | int  | Status code                                     |
| session_id      | str  | Random generated session identifier             |
| crypto_currency | str  | Crypto currency                                 |
| address         | str  | Destination crypto address. Empty for Manta TXS |

### ACK_MESSAGE

| attribute        | type | description                                       |
| ---------------- | ---- | ------------------------------------------------- |
| txid             | str  | Progressive Transaction ID                        |
| transaction_hash | str  | Crypto transaction hash                           |
| status           | str  | Status of transaction (pending, confirming, paid) |

### PAYMENT_REQUEST_MESSAGE

**ENVELOPE**

| attribute | type | description                            |
| --------- | ---- | -------------------------------------- |
| message   | str  | JSON string of PAYMENT_REQUEST_MESSAGE |
| signature | str  | RSA signature                          |

**PAYMENT_REQUEST_MESSAGE**

| attribute       | type              | description                                    |
| --------------- | ----------------- | ---------------------------------------------- |
| merchant        | TBD               | Merchant Info (str at the moment)              |
| amount          | float             | Amount in fiat                                 |
| fiat_currency   | str               | Fiat Currency type (EUR, USD...)               |
| support_cryptos | list[str]         | List of supported cryptos by Payment Processor |
| destinations    | list[Destination] | List of destination addresses. Can be empty    |

**DESTINATION**

| attribute           | type  | description                      |
| ------------------- | ----- | -------------------------------- |
| amount              | float | Amount in crypto                 |
| destination_address | str   | Crypto destination address       |
| crypto_currency     | str   | Crypto currency (NANO, BTC, ...) |

### PAYMENT_MESSAGE 

| attribute        | type | description                      |
| ---------------- | ---- | -------------------------------- |
| crypto_currency  | str  | Crypto currency (NANO, BTC, ...) |
| transaction_hash | str  | Crypto transaction hash          |


## TOPICS
### GENERATE_PAYMENT_REQUEST/{DEVICE_ID}/REQUEST
**DEVICE_ID** unique POS identifier

**PUBLISHERS** POS

**SUBSCRIBERS** Payment Processor

### GENERATE_PAYMENT_REQUEST/{DEVICE_ID}/REQUEST

**DEVICE_ID** unique POS identifier

**PUBLISHERS** Payment Processor

**SUBSCRIBERS** POS

### ACKS/{SESSION_ID}

**SESSION_ID** unique Session Identifier

**PUBLISHERS** Payment Processor

**SUBSCRIBERS** POS/ Wallets

### PAYMENT_REQUESTS/{SESSION_ID}

**SESSION_ID** unique Session Identifier

**PUBLISHERS** Payment Processor

**SUBSCRIBERS** Wallets

### PAYMENT_REQUESTS/{SESSION_ID}/{CRYPTO_CURRENCY}

**SESSION_ID** unique Session Identifier

**CRYPTO_CURRENCY** crypto currency

**PUBLISHERS** Wallet

**SUBSCRIBERS** Payment Processor

### PAYMENTS/{SESSION_ID}

**SESSION_ID** unique Session Identifier

**PUBLISHERS** Wallets

**SUBSCRIBERS** Payment Processor


