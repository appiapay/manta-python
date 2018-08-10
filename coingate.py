import requests
import logging
from flask import Flask, request
from payproclib import PayProc, POSPaymentRequestMessage , Destination
from typing import List


TOKEN = "JzxZnyUEqVa5RbyqXE2ErHGdzJcQxsQEy4ykK2gq"


logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(name)s - "%(message)s"')
# logging.getLogger('selenium').setLevel(logging.INFO)
logging.getLogger('urllib3').setLevel(logging.INFO)
logger = logging.getLogger("root")
# logger.setLevel(logging.DEBUG)
# ch = logging.StreamHandler()
# formatter = logging.Formatter('%(levelname)s:%(name)s - [%(asctime)s] - "%(message)s"')
# ch.setFormatter(formatter)
# logger.addHandler(ch)


class Coingate:
    coingate_api_url: str = "https://api-sandbox.coingate.com"
    callback_url: str = "http://167.99.89.97/status-change"
    cert_path: str = "certificates/root/keys/www.brainblocks.com.key"
    app: Flask
    pp: PayProc

    def __init__(self):
        self.app = Flask(__name__)
        self.pp = PayProc("certificates/root/keys/www.brainblocks.com.key")
        self.pp.get_merchant = lambda x: "merchant1"
        self.pp.get_destinations = self.get_destinations

        self.app.add_url_rule('/status-change', 'status-change', self.status_change, methods=['post'])

    def status_change(self):
        logger.info("Order Status Change")
        logger.debug(request.form)

        if request.form['status'] == 'paid':
            self.pp.confirm(request.form['order_id'])

        return ""
        
    def run(self):
        logger.info("Starting MQTT and HTTP")
        self.pp.run()
        self.app.run(debug=True, use_reloader=False)

    def get_destinations (self, device: str, payment_request: POSPaymentRequestMessage) -> List[Destination]:
        amount, address= self.create_order(TOKEN, payment_request.amount, payment_request.fiat_currency, payment_request.session_id)
        return [Destination(amount, address, 'btc')]

    def create_order (self, token: str, amount: float, fiat_currency: str, session_id: str) -> (float, str):
        logger.info("Creating New Order")

        headers = {
            "Authorization": "Token {}".format(token)
        }

        order_request = {
            "price_amount": amount,
            "price_currency": fiat_currency,
            "receive_currency": "DO_NOT_CONVERT",
            "order_id":session_id,
            "callback_url": self.callback_url
        }

        r = requests.post("{}/v2/orders".format(self.coingate_api_url), headers=headers, json=order_request)

        logger.debug ("Response:{}".format(r))

        order = r.json()

        logger.debug ("Order:{}".format(order))

        url = "{}/v2/orders/{}/checkout".format(self.coingate_api_url, order["id"])

        r = requests.post(url, headers=headers, json={"pay_currency":'btc'})

        checkout = r.json()

        logger.debug("Checkout:{}".format(checkout))

        amount = float(checkout['pay_amount'])

        address = checkout['payment_address']

        logger.info("Amount:{} Address:{}".format(amount, address))

        return amount, address

    #driver.close()


if __name__ == "__main__":
    cg = Coingate()
    #cg.create_order(TOKEN, 10)
    cg.run()



