from pycoin.key import Key

import paho.mqtt.client as mqtt
import json
import re

CONF = {
    'url': '127.0.0.1',
    'masterkey': 'xpub661MyMwAqRbcFVF9ULcqLdsEa5WnCCugQAcgNd9iEMQ31tgH6u4DLQWoQayvtSVYFvXz2vPPpbXE1qpjoUFidhjFj82pVShWu9curWmb2zy'
}

DB = {
    'device1': {
        'name': 'Nano Coffee Shop',
        'address': 'Milano',
    }
}

PAYMENT_REQUESTS = {}


def parse(topic):
    m = re.search("^\/rpc\/(\w+)\/request(?:$|\/(.*))", topic)

    return (None if m is None else {
        'method': m.group(1),
        'args': None if len(m.groups()) == 1 else m.group(2).split('/')
    })


def generate_payment_request(device, amount, txid, key_index='0'):
    merchant = DB[device]
    return {
        'name': merchant['name'],
        'address': merchant['address'],
        'amount': amount,
        'keyindex': key_index,
        'txid': txid,

    }


def on_connect(client, userdata, flags, rc):
    print("Connected with result code " + str(rc))

    client.subscribe('/rpc/+/request/#')


def check_key(key, path):
    kd = Key.from_text(CONF['masterkey']).subkey_for_path(path)

    print('Got key:{} and path:{}. Derivation:{}'.format(key, path, kd.wallet_key()))

    return kd.wallet_key() == key


def on_message(client: mqtt.Client, userdata, msg):
    print("Got {} on {}".format(msg.payload, msg.topic))

    parsed = parse(msg.topic)

    if parsed is not None:
        if parsed['method'] == 'generate_payment_request':
            p = json.loads(msg.payload)
            PAYMENT_REQUESTS[p['txid']] = generate_payment_request(parsed['args'][0], p['amount'], p['txid'])
            print(PAYMENT_REQUESTS[p['txid']])

        if parsed['method'] == 'get_payment_request':
            print("Replying to Payment Request")
            txid = int(parsed['args'][0])
            p = json.loads(msg.payload)
            # TODO check if valid p.address
            if check_key(p['key'], p['path']):
                client.publish("/rpc/get_payment_request/reply/{}".format(txid), json.dumps(PAYMENT_REQUESTS[txid]))


if __name__ == "__main__":
    c = mqtt.Client()

    c.on_connect = on_connect
    c.on_message = on_message

    c.connect(CONF['url'])

    c.loop_forever()
