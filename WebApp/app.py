from flask import Flask, render_template, url_for, request, redirect
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
from flask_mqtt import Mqtt
import os

app = Flask(__name__)
#app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///catifs.db'
#db = SQLAlchemy(app)
app.config['MQTT_BROKER_URL'] = 'http://10.158.56.21' <- i haz my own broker how this oh noes
#app.config['MQTT_BROKER_PORT'] = 1883 <-default
#app.config['MQTT_USERNAME'] = 'user' <-uhh authentication is out of scope so no need
#app.config['MQTT_PASSWORD'] = 'secret' <- only needed when username is provided
#app.config['MQTT_REFRESH_TIME'] = 1.0  # not sure if i need this: refresh time in seconds, sets the time interval for sending a ping to the broker to 5 seconds
app.config['MQTT_TLS_ENABLED'] = False  # set TLS to disabled for testing purposes
mqtt = Mqtt(app)

f = open("node_IPs.txt", "r")
topics = []

def ping_sweep():
    print("in fcn")
    f.seek(0)
    for ip in f:
        print("in for loop")
        ip = ip.rstrip()
        print(ip)
        response = os.system("sudo ping -c 1 " + ip + " > dump.txt")
        #check the response:
        if (not response):
            print(ip+" is CONNECTED")
        else:
            print(ip+" is DISCONNECTED")
    f.seek(0)

@mqtt.on_connect()
def handle_connect(client, userdata, flags, rc):
    f.seek(0)
    for ip in f:
        ip = ip.replace('\n','/+')
        print(ip)
        mqtt.subscribe(ip)
    f.seek(0)

@mqtt.on_message()
def handle_mqtt_message(client, userdata, message):
    data = dict(
        topic=message.topic,
        payload=message.payload.decode()
    )
    if

@app.route('/')
def homepage():
    return render_template('homepage.html')

@app.route('/module')
def mgmt_module():
    return render_template('module.html')

@app.route('/module/perf_monitor')
def performance_monitor():
    return render_template('perf_monitor.html')

if __name__=="__main__":
    app.run(debug=True)