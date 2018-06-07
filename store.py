import random
import paho.mqtt.client as mqtt
import json

CONF = {
    'pp': 1,
    'url': '127.0.0.1',
    'deviceID': 'device1'
}


def generate_qr(txid):
    return {
        'pp': CONF['pp'],
        'txid': txid
    }


def generate_txid():
    return random.randint(0, 2 ** 32)


def on_connect(client, userdata, flags, rc):
    print("Connected with result code " + str(rc))

    txid = generate_txid()
    amount = 100
    generate_qr(txid)

    print('TXID:{}'.format(txid))

    client.publish('/rpc/generate_payment_request/request/{deviceID}'.format(deviceID=CONF['deviceID']),
                   json.dumps({'amount': amount, 'txid': txid}))


if __name__ == "__main__":

    c = mqtt.Client()

    c.on_connect = on_connect

    c.connect(CONF['url'])

    c.loop_forever()



