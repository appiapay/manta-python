from collections import namedtuple

from pycoin.key import Key

import paho.mqtt.client as mqtt
import json
import random
import re

CONF = {''
        'url': '127.0.0.1',
        'pubkey': 'xpub6DLJbt93Rui7cdCWApb6C6kbs9kSKfZWgqrc61EVwTttxytgaMEbBbPpfH85AtjmWDyizqxMk5xFPsjnxTwX7LsEFtMcbYwEsNacoKS5xZe',
        'keypath': '0/0/0'
        }

Method = namedtuple('Method', ['name', 'args'])


def parse(topic):
    m = re.search("^\/rpc\/(\w+)\/reply(?:$|\/(.*))", topic)

    return (None if m is None else Method(
        name=m.group(1),
        args=None if len(m.groups()) == 1 else m.group(2).split('/')
    ))


def on_connect(client, userdata, flags, rc):
    print("Connected with result code " + str(rc))
    client.subscribe('/rpc/get_payment_request/reply/{}'.format(userdata))
    request = {
        'key': Key.from_text(CONF['pubkey']).subkey(index).wallet_key(),
        'path': CONF['keypath'] + '/' + str(index)
    }
    client.publish('/rpc/get_payment_request/request/{}'.format(userdata), json.dumps(request))


def on_message(client, userdata, msg):
    print("Got {} on {}".format(msg.payload, msg.topic))

    parsed = parse(msg.topic)

    if parsed.name == 'get_payment_request':
        payment_request = json.loads(msg.payload)
        print("\n### PAYMENT REQUEST ###\n{}".format(json.dumps(payment_request, indent=4, sort_keys=True)))
        input("Do you confirm?")
        tx_hash = send_money()


def send_money(address, amount):
    return random.randint(0, 2 ** 32)


if __name__ == "__main__":
    # qr_code = input("Qr Code?")

    qr_code = 1234

    index = 0

    c = mqtt.Client(userdata=qr_code)

    c.on_connect = on_connect
    c.on_message = on_message

    c.connect(CONF['url'])

    c.loop_forever()
