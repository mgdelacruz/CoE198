from flask import Flask
import paho.mqtt.client as mqtt
import signal
import sys

app = Flask(__name__)

var = 'foo'
topic = 'bar'
port = 5000

def signal_handler(signum, frame):
    client.loop_stop()    #Stop loop
    sys.exit()


def on_connect(client, userdata, flags, rc):
    client.subscribe(topic)
    client.publish(topic, "STARTING SERVER")
    client.publish(topic, "CONNECTED")

def on_message(client, userdata, msg):
    msg.payload = msg.payload.decode("utf-8")
    global var
    var = msg.payload


@app.route('/')
def hello_world():
    return 'Hello World! this is var: ' + var

if __name__ == '__main__':
    signal.signal(signal.SIGINT, signal_handler) #for cleanup upon exit
    client = mqtt.Client()
    #client.username_pw_set(username, password)
    client.on_connect = on_connect
    client.on_message = on_message
    client.connect("10.158.56.21", 1883, 60)
    client.loop_start()
    #flask web app
    app.run(host='0.0.0.0', port=port)