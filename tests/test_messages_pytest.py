from manta.messages import  MerchantOrderRequestMessage

def test_serialize():
    payload = '{"amount": 10, "session_id": "pXbNKx8YRJ2dsIjJIfEuQA==", "fiat_currency": "eur", "crypto_currency": null}'
    order = MerchantOrderRequestMessage.from_json(payload)