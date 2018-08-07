from flask import Flask, request
from flask_mqtt import Mqtt
import logging


HOST= '127.0.0.1'
PORT = 1883
logging.basicConfig(level=logging.INFO)

app = Flask(__name__)
app.config['MQTT_BROKER_URL'] = 'localhost'
app.config['MQTT_BROKER_PORT'] = 1883
app.config['MQTT_USERNAME'] = ''
app.config['MQTT_PASSWORD'] = ''
app.config['MQTT_KEEPALIVE'] = 5
app.config['MQTT_TLS_ENABLED'] = False

mqtt = Mqtt(app)


@app.route('/status-change', methods= ['POST'])
def status_change():
    logging.info(request.form)
    # topic = request.args.get('topic')
    # message = request.args.get('message')
    # mqtt = mq.Client("restMQTT")
    # mqtt.connect(HOST, PORT)
    # mqtt.publish(topic, message)
    return ""


@app.route('/resources/coingate/callback', methods= ['POST'])
def clear():
    logging.info(request.form)
    return ""


@mqtt.on_connect()
def handle_on_connect(client, userdata, flags, rc):
    logging.info("MQTT Connected")




if __name__ == '__main__':
    app.run(debug=True, use_reloader=False)