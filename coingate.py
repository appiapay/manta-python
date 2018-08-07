import requests
import logging
from flask import Flask, request
from selenium import webdriver
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from payproclib import PayProc, POSPaymentRequestMessage , Destination
from typing import List


TOKEN = "JzxZnyUEqVa5RbyqXE2ErHGdzJcQxsQEy4ykK2gq"


logging.basicConfig(level=logging.DEBUG)
logging.getLogger('selenium').setLevel(logging.INFO)
logging.getLogger('urllib3').setLevel(logging.INFO)
logger = logging.getLogger(__name__)


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

    def add_routes(self):
        @self.app.route('/status-change', methods=['POST'])
        def status_change():
            logging.info(request.form)
            self.pp.confirm("123")
            return ""
        
    def run(self):
        self.pp.run()
        self.app.run(debug=True, use_reloader=False)

    def get_destinations (self, device: str, payment_request: POSPaymentRequestMessage) -> List[Destination]:
        amount, address= self.create_order(TOKEN, payment_request.amount, payment_request.fiat_currency, payment_request.session_id)
        return [Destination(amount, address, 'btc')]

    def create_order (self, token: str, amount: float, fiat_currency: str, session_id: str) -> (float, str):
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

        logger.info ("Order:{}".format(order))

        driver = webdriver.Chrome()

        driver.get(order["payment_url"])

        elements = driver.find_elements_by_xpath("//div[@class='currency-card-currency-title' and text()='Bitcoin']")
        assert len(elements) == 1, len(elements)

        elements[0].click() #BTC Button

        #Get Pay Button
        elements = driver.find_elements_by_xpath("//button[@class='ant-btn ant-btn-primary']")
        assert (len(elements) == 1)

        elements[0].click()

        #NEW PAGE

        try:
            element = WebDriverWait(driver, 10).until(
                EC.presence_of_all_elements_located((By.CLASS_NAME, "send-amount"))
            )

        except Exception as e:
            logger.error('Error while loading payment page')
            return

        elements = driver.find_elements_by_class_name('ant-input')
        assert (len(elements) == 2)

        amount = float(elements[0].get_attribute('value'))

        address = elements[1].get_attribute('value')

        logger.info("Amount:{} Address:{}".format(amount, address))

        return amount, address

    #driver.close()


if __name__ == "__main__":
    cg = Coingate()
    #cg.create_order(TOKEN, 10)
    cg.run()



