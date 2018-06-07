import paho.mqtt.client as mqtt
import json

CONF = {''
    'url': '127.0.0.1',
}


def on_connect(client, userdata, flags, rc):
    print("Connected with result code " + str(rc))
    client.subscribe('/rpc/get_payment_request/reply/{}'.format(userdata))
    client.publish('/rpc/get_payment_request/request/{}'.format(userdata), json.dumps({'address': '123'}))


def on_message(client, userdata, msg):
    print("Got {} on {}".format(msg.payload, msg.topic))


if __name__ == "__main__":

    qr_code = input("Qr Code?")

    c = mqtt.Client(userdata=qr_code)

    c.on_connect = on_connect
    c.on_message = on_message

    c.connect(CONF['url'])

    c.loop_forever()