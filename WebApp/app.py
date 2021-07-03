from enum import unique
from flask import Flask, render_template, url_for, request, redirect
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
from flask_mqtt import Mqtt
import os

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///catifs.db'
db = SQLAlchemy(app)
app.config['MQTT_BROKER_URL'] = 'http://10.158.56.21' #<- i haz my own broker how this oh noes
#app.config['MQTT_BROKER_PORT'] = 1883 <-default
#app.config['MQTT_USERNAME'] = 'user' <-uhh authentication is out of scope so no need
#app.config['MQTT_PASSWORD'] = 'secret' <- only needed when username is provided
#app.config['MQTT_REFRESH_TIME'] = 1.0  # not sure if i need this: refresh time in seconds, sets the time interval for sending a ping to the broker to 5 seconds
app.config['MQTT_TLS_ENABLED'] = False  # set TLS to disabled for testing purposes
mqtt = Mqtt(app)

class Nodes(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    device = db.Column(db.String(200), nullable=False)
    ip = db.Column(db.String(15), primary_key=True)
#class Performance(db.Model):
    cpu = db.Column(db.Float, nullable=True)
    memory = db.Column(db.Float, nullable=True)
#class Uptime(db.Model):
#    status = db.Column(db.String(15), nullable = False)
#    last_disconnect = db.Column(db.DateTime)
#    disconnection_details = db.Column(db.Text)
#class Threshold(db.Model):
#    current_threshold = (db.Float, nullable=False)

f = open("node_IPs.txt", "r")
IPs = []

for ip in f:
    IPs.append(ip.rstrip())

print(IPs)

def ping_sweep():
    print("in fcn")
    for ip in IPs:
        print("in for loop")
        print(ip)
        response = os.system("sudo ping -c 1 " + ip + " > dump.txt")
        #check the response:
        if (not response):
            print(ip + ' is CONNECTED')
        else:
            print(ip + 'is DISCONNECTED')

@mqtt.on_connect()
def handle_connect(client, userdata, flags, rc):
    for ip in IPs:
        topic = ip + '/+'
        print(topic)
        mqtt.subscribe(topic)

@mqtt.on_message()
def handle_mqtt_message(client, userdata, message):

    raw_topic=message.topic,
    payload=message.payload.decode()
    temp = raw_topic.split('/', 1)
    device_ip = temp[1]
    print(device_ip)
    topic = temp[2]
    print(topic)

    if (topic == 'cpu'):
        node = Nodes(
            device = 'Raspberry Pi',
            ip = device_ip,
            cpu = float(payload)
        )

        try:
            db.session.add(node)
            db.session.commit()

        except:
            return 'There was an issue adding your task'
    elif (topic == 'mem'):
        node = Nodes(
            device = 'Raspberry PI',
            ip = device_ip,
            memory = float(payload)
        )

        try:
            db.session.add(node)
            db.session.commit()

        except:
            return 'There was an issue adding your task'
    #elif (topic == 'uptime'):
    #else:


@app.route('/')
def homepage():
    return render_template('homepage.html')

@app.route('/module')
def mgmt_module():
    return render_template('module.html')

@app.route('/module/perf_monitor')
def performance_monitor():
    mqtt.publish('flags', 'performance')
    devices = Nodes.query.order_by(Nodes.id).all()
    #return render_template('product-page.html', tasks = tasks)
    return render_template('perf_monitor.html', devices = devices)

#@app.route('/module/uptime_monitor')
#def uptime_monitor():
#    mqtt.publish('flags', 'uptime')
#    return render_template('uptime_monitor.html')

#@app.route('/module/thresh_adjust', methods=['POST', 'GET'])
#def performance_monitor():
#    mqtt.publish('flag', '36.5')
#    return render_template('thresh_adjust.html')

if __name__=="__main__":
    app.run(debug=True)