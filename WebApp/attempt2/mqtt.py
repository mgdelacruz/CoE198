import paho.mqtt.client as mqtt
import os, tempfile
import sys
#import logging
import signal
import threading
import json
from flask import Flask, render_template, url_for, request, redirect
from datetime import datetime
from flask_sqlalchemy import SQLAlchemy
from queue import Queue

app = Flask(__name__)
# app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///test.db'
# db = SQLAlchemy(app)

# class Nodes(db.Model):
#     dev_no = db.Column(db.Integer, primary_key=True)
#     device = db.Column(db.String(200), nullable=False)
#     ip = db.Column(db.String(15), primary_key=True)
#     cpu_flag = db.Column(db.Float, nullable=True)
#     memory_flag = db.Column(db.Float, nullable=True)
#     status = db.Column(db.String(15), nullable = False)
#     ping = db.Column(db.String(15), nullable = False)
#     current_threshold = (db.Float, nullable=False)
#     old_threshold = (db.Float, nullable=False)

#     def __repr__(self):
#         return '<Task %r>' % self.id


#global variables
hash={}                     #stores ip to device no. mapping
connected_flags = []        #used for uptime monitoring
ping_prompt = None          #fifo file that gets prompt to ping devices
nodes = []                  #array of Node objects
change = False              #flag for changes to database
client = None               #global Client
#value = Queue(1)            #threshold value
#change_var_mes = Queue()    #change var response
class Node ():
    cnt = 0
    def __init__ (self, ip):
        Node.cnt += 1
        self.device = "Raspberry Pi"
        self.dev_no = Node.cnt
        self.ip = ip
        self.cpu_file = None
        self.mem_file = None
        self.cpu_flag = ''
        self.mem_flag = ''
        self.status = ''
        self.ping = ''
        self.current_threshold = Queue()
        self.old_threshold = Queue()
    def __del__(self):
        self.cpu_file.close()
        self.mem_file.close()


def signal_handler(signum, frame):
    global client
    client.connected_flag = False
    client.disconnect_flag = True
    client.loop_stop()    #Stop loop
    sys.exit()

#MQTT Host Client Code:

def ping_sweep():
    print("in fcn")
    global server_to_app
    for i in range(Node.cnt-1):
        print("in for loop")
        response = os.system("sudo ping -c 1 " + nodes[i].ip + " > dump.txt")
        #check the response:
        if (not response):
            nodes[i].ping = 'CONNECTED'
        else:
            nodes[i].ping = 'DISCONNECTED'

#def change_var():
    #while not value.empty():
        #print("changing variables to " + value) #debug
        #client.publish("change_var", value)

# def ping_prompt_loop():
#     global ping_prompt
#     while(True):
#         prompt = input("Ping sweep? y/n:")
#         if prompt == 'y':
#             ping_sweep()

# The callback for when the client receives a CONNACK response from the server.
def on_connect(client, userdata, flags, rc):

    #global server_to_app
    if rc==0:
        client.connected_flag = True
        print("connected OK Returned code=",rc)#debug
        #client.subscribe("self")
        f = open("node_IPs.txt", "r")
        for ip in f:
            print("iterating through ips in node_ip.txt") #debug
            #populate hash table, initialize connected flags and subscribe to node topics
            global hash
            nodes.append(Node(ip.rstrip()))
            hash.update({nodes[-1].ip : Node.cnt})
            client.subscribe(nodes[-1].ip+'/+')

            #performance monitor initialization
            nodes[-1].cpu_file = open("cpu"+str(Node.cnt)+".txt", "a")
            nodes[-1].mem_file = open("mem"+str(Node.cnt)+".txt", "a")
            print("opened cpu and mem files") #debug

        print("done iterating through ips in node_ip.txt") #debug
        f.close()

        #start threshold adjustment thread
        # print("initializing threshold adjustment thread") #debug
        # try:
        #     change_var_thread = threading.Thread(target = change_var,args=())
        # except:
        #     print ("Error: unable to start change var thread")
        #     client.disconnect() # disconnect
        # else:
        #     change_var_thread.daemon = True
        #     change_var_thread.start()

        #start ping prompt thread
        # print("initializing ping prompt thread") #debug
        # try:
        #     ping_prompt_thread = threading.Thread(target = ping_prompt_loop,args=())
        # except:
        #     print ("Error: unable to start change var thread")
        #     client.disconnect() # disconnect
        # else:
        #     ping_prompt_thread.daemon = True
        #     ping_prompt_thread.start()

    else:
        #logging.info("Bad connection Returned code=",str(rc))
        client.bad_connection_flag=True

# The callback for when a PUBLISH message is received from the server.
def on_cpu(client, userdata, msg):
    q = Queue(1)
    q.put(msg)
    while not q.empty():
        message = q.get()
        print("queue: ",message)#debug

        payload=message.payload.decode("utf-8")
        print(payload)
        raw_topic=str(msg.topic)
        #print('raw_topic: ', raw_topic)
        temp = raw_topic.split('/', 1)
        #print('temp: ',temp)
        ip = temp[0]
        topic = temp[1]
        #print(ip)
        #print(topic)

        key = hash[ip]-1
        nodes[key].cpu_file.write(payload+'\n') #debug
        print('wrote to cpu file')

def on_mem(client, userdata, msg):
    q = Queue(1)
    q.put(msg)
    while not q.empty():
        message = q.get()
    #print("queue: ",message)#debug

    payload=message.payload.decode("utf-8")
    raw_topic=str(msg.topic)
    #print('raw_topic: ', raw_topic)
    temp = raw_topic.split('/', 1)
    #print('temp: ',temp)
    ip = temp[0]
    topic = temp[1]
    #print(ip)
    #print(topic)

    key = hash[ip]-1
    nodes[key].mem_file.write(payload+'\n') #debug

def on_status(client, userdata, msg):
    q = Queue(1)
    q.put(msg)
    while not q.empty():
        message = q.get()

    payload=message.payload.decode("utf-8")
    print(payload)
    raw_topic=str(msg.topic)
    print('raw_topic: ', raw_topic)
    temp = raw_topic.split('/', 1)
    print('temp: ',temp)
    ip = temp[0]
    topic = temp[1]
    print(ip)
    print(topic)

    print("recvd disconnect message") #debug
    key = hash[ip]-1
    nodes[key].status = payload
    print("ip: ", ip) #debug
    print("Status: ",payload) #debug

def on_cpu_flag(client, userdata, msg):
    q = Queue(1)
    q.put(msg)
    while not q.empty():
        message = q.get()
        payload=message.payload.decode("utf-8")
        print(payload)
        raw_topic=str(msg.topic)
        print('raw_topic: ', raw_topic)
        temp = raw_topic.split('/', 1)
        print('temp: ',temp)
        ip = temp[0]
        topic = temp[1]
        print(ip)
        print(topic)
        print("recvd disconnect message") #debug
        key = hash[ip]-1
        nodes[key].cpu_flag = payload
        print("ip: ", ip) #debug
        print("CPU_Flag: ",payload) #debug

def on_mem_flag(client, userdata, msg):
    q = Queue(1)
    q.put(msg)
    while not q.empty():
        message = q.get()
        payload=message.payload.decode("utf-8")
        print(payload)
        raw_topic=str(msg.topic)
        print('raw_topic: ', raw_topic)
        temp = raw_topic.split('/', 1)
        print('temp: ',temp)
        ip = temp[0]
        topic = temp[1]
        print(ip)
        print(topic)
        print("recvd disconnect message") #debug
        key = hash[ip]-1
        nodes[key].mem_flag = payload
        print("ip: ", ip) #debug
        print("Mem_Flag: ",payload) #debug

def on_change_var_res(client, userdata, msg):
    q = Queue(1)
    q.put(msg)
    while not q.empty():
        message = q.get()
        payload=message.payload.decode("utf-8")
        print(payload)
        raw_topic=str(msg.topic)
        print('raw_topic: ', raw_topic)
        temp = raw_topic.split('/', 1)
        print('temp: ',temp)
        ip = temp[0]
        topic = temp[1]
        print(ip)
        print(topic)
        print("recvd change var response message") #debug
        key = hash[ip]-1
        message = json.loads(payload)
        nodes[key].old_threshold.put(message["from"])
        nodes[key].current_threshold.put(message["to"])
        print("ip, old threshold, current threshold: ",ip,' ,', nodes[key].old_threshold, ' ,', nodes[key].current_threshold) #debug

def on_disconnect(client, userdata, rc):
    os.kill(os.getpid(), signal.SIGUSR1)

#def on_log(client, userdata, level, buf):
#    print("log: ",buf)

def Initialise_client_object():
    #flags set
    mqtt.Client.bad_connection_flag=False
    mqtt.Client.connected_flag=False
    mqtt.Client.disconnected_flag=False
    mqtt.Client.suback_flag=False


#Flask Web Application

@app.route('/')
def homepage():
    return render_template('homepage.html')

@app.route('/module')
def mgmt_module():
    return render_template('module.html')

@app.route('/module/perf_monitor')
def performance_monitor_module():
    return render_template('perf_monitor.html', nodes = nodes)

@app.route('/module/uptime_monitor')
def uptime_monitor_module():
    return render_template('uptime_monitor.html', nodes = nodes)

@app.route('/module/uptime_monitor/ping_sweep')
def ping_sweep_flask():

    ping_sweep()

    try:
        return redirect('/module/uptime_monitor')
    except:
        return 'There was a problem in executing ping_sweep'


@app.route('/module/thresh_adjust', methods=['POST', 'GET'])
def change_var_module():
    if request.method == 'POST':
        #global value
        #value.put(float(request.form['value']))
        value = float(request.form['value'])
        try:
            client.publish("change_var", value)
            #return redirect('/module/thresh_adjust/<float:value>')
            return render_template('thresh_adjust.html', nodes = nodes)
        except:
            return 'Invalid input'
    else:
        return render_template('thresh_adjust.html', nodes = nodes)

# @app.route('/module/thresh_adjust/<float:value>')
# def pub(value):

#     client.publish("change_var", {{value}})

#     try:
#         return redirect('/module/thresh_adjust')
#     except:
#         return 'There was a problem in executing publish'

if __name__ == '__main__':

    signal.signal(signal.SIGINT, signal_handler) #for cleanup upon exit
    #Bind callbacks
    client = mqtt.Client(client_id="host", clean_session=False)
    client.on_connect = on_connect
    client.on_disconnect = on_disconnect
    #client.on_log=on_log
    client.message_callback_add('+/cpu',on_cpu)
    client.message_callback_add('+/mem',on_mem)
    client.message_callback_add('+/cpu_flag',on_cpu_flag)
    client.message_callback_add('+/mem_flag',on_mem_flag)
    client.message_callback_add('+/status',on_status)
    client.message_callback_add('+/change_var_response',on_change_var_res)
    Initialise_client_object()

    #connect to a broker
    client.connect("10.158.56.21", 1883, 60)
    if client.bad_connection_flag:
        client.loop_stop()    #Stop loop
        sys.exit()
    client.loop_start()
    #flask web app
    app.run(host='0.0.0.0', port=4444)