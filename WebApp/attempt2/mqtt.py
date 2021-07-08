import paho.mqtt.client as mqtt
import os, tempfile
import sys
import logging
import signal
import threading
import json
from flask import Flask, render_template, url_for, request, redirect
from datetime import datetime
from flask_sqlalchemy import SQLAlchemy

#global variables
current_threshold = 37.5    #initial threshold value on pi
old_threshold = None
hash={}                     #stores ip to device no. mapping
filenames = []              #list of filenames of each fifo used for cleanup upon server disconnect
fps =[]                     #file pointers to be closed upon server disconnect
connected_flags = []        #used for uptime monitoring
ping_prompt = None          #fifo file that gets prompt to ping devices
#client = None               #global client object
nodes = []                  #array of Node objects
change = False              #flag for changes to database

# BASE_DIR = os.path.dirname(os.path.abspath(__file__))
# db_path = os.path.join(BASE_DIR, "catifs.db")
# app = Flask(__name__)
# app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + db_path
# app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
# db = SQLAlchemy(app)
# class database(db.Model):
#     id = db.Column(db.Integer, primary_key=True)
#     device = db.Column(db.String(200), nullable=False)
#     ip = db.Column(db.String(15), primary_key=True)
#     cpu = db.Column(db.Float, nullable=True)
#     memory = db.Column(db.Float, nullable=True)
#     status = db.Column(db.String(15), nullable = False)
#     last_disconnect = db.Column(db.DateTime)
#     current_threshold = (db.Float, nullable=False)
#     def __repr__(self):
#         return '<Node %r>' %self.id

class Node ():
    node_cnt = 0
    def __init__ (self, ip):
        Node.cnt += 1
        self.device = "Raspberry Pi"
        self.dev_no = Node.cnt
        self.ip = ip
        self.cpu_file = None
        self.mem_file = None
        self.disconnected = True
        self.last_disconnect = ''
        self.current_threshold = '37.5'
        self.old_threshold = ''
        self.uptime_thread = None
    def __del__(self):
        self.cpu_file.close()
        self.mem_file.close()
        os.remove()

def signal_handler(signum, frame):
    global client
    for fp in fps:
        fp.close()
    for filename in filenames:
        os.remove(filename)
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
            nodes[i].disconnected = False
        else:
            nodes[i].disconnected = True

def uptime_monitor(ip, local_flag):
    global uptime_app
    dev_no = hash[ip]
    if(not local_flag):
                message = {
                        "device no.":hash[ip],
                        "ip":ip,
                        "uptime":"CONNECTED"
                }
    else:
            message = {
                "device no.":hash[ip],
                "ip":ip,
                "uptime":"DISCONNECTED",
            }
    to_write = json.dumps(message)
    #uptime_app.write(to_write)
    print(message)

    while(True):
        if local_flag != connected_flags[dev_no-1]:
            local_flag = connected_flags[dev_no-1]
            if(not local_flag):
                message = {
                        "device no.":hash[ip],
                        "ip":ip,
                        "uptime":"CONNECTED"
                }
            else:
                message = {
                    "device no.":hash[ip],
                    "ip":ip,
                    "uptime":"DISCONNECTED",
                }
            to_write = json.dumps(message)
            #uptime_app.write(to_write)
            print(message)

def change_var(NUM_NODES):
    global change_var_server
    global change_var_app
    global fps
    change_var_app = open('change_var_app', 'r')
    fps.append(change_var_app)

    while (True):
        value = input("Enter a variable: ")
        print("changing variables to " + value) #debug
        client.publish("change_var", value)

def ping_prompt_loop():
    global ping_prompt
    while(True):
        prompt = input("Ping sweep? y/n:")
        if prompt == 'y':
            ping_sweep()

# The callback for when the client receives a CONNACK response from the server.
def on_connect(client, userdata, flags, rc):

    #global server_to_app
    if rc==0:
        client.connected_flag = True
        print("connected OK Returned code=",rc)#debug

        signal.signal(signal.SIGINT, signal_handler) #for cleanup upon exit
        #client.subscribe("self")

        f = open("node_IPs.txt", "r")
        for ip in f:
            print("iterating through ips in node_ip.txt") #debug
            #populate hash table, initialize connected flags and subscribe to node topics
            global hash
            nodes.append(Node(ip.rstrip()))
            hash.update({nodes[-1] : Node.cnt})
            client.subscribe(nodes[-1].ip+'/+')

            #performance monitor initialization
            nodes[-1].cpu_file = open("cpu"+str(Node.cnt)+".txt", "a")
            nodes[-1].mem_file = open("mem"+str(Node.cnt)+".txt", "a")
            print("opened cpu and mem files") #debug

        print("done iterating through ips in node_ip.txt") #debug
        f.close()

        #uptime monitor initialization
        uptime_threads = []
        ping_sweep()
        print("ping sweeped") #debug
        print("initializing uptime monitor threads") #debug
        for i in range(Node.cnt-1):
            try:
                nodes[i].uptime_thread = threading.Thread(target = uptime_monitor,args=(nodes[i].ip,nodes[i].disconnected))
            except:
                print ("Error: unable to start uptime thread")
                client.disconnect() # disconnect
            else:
                uptime_threads[-1].daemon = True
                uptime_threads[-1].start()

        #start threshold adjustment thread
        print("initializing threshold adjustment thread") #debug
        try:
            change_var_thread = threading.Thread(target = change_var,args=Node.cnt)
        except:
            print ("Error: unable to start change var thread")
            client.disconnect() # disconnect
        else:
            change_var_thread.daemon = True
            change_var_thread.start()

        #start ping prompt thread
        print("initializing ping prompt thread") #debug
        global ping_prompt
        ping_prompt = open("ping_prompt","r")
        fps.append(ping_prompt)
        try:
            ping_prompt_thread = threading.Thread(target = ping_prompt_loop,args=())
        except:
            print ("Error: unable to start change var thread")
            client.disconnect() # disconnect
        else:
            ping_prompt_thread.daemon = True
            ping_prompt_thread.start()

    else:
        logging.info("Bad connection Returned code=",str(rc))
        client.bad_connection_flag=True

# The callback for when a PUBLISH message is received from the server.
def on_message(client, userdata, msg):
    print("a message was received") #debug
    global server_to_app
    raw_topic=msg.topic,
    payload=msg.payload.decode("utf-8")
    temp = raw_topic.split('/', 1)
    ip = temp[1]
    print(ip)
    topic = temp[2]
    print(topic)

    if(topic == "cpu"):

        key = hash[ip]-1
        #global cpu_usage
        #cpu_usage[key-1].write(payload)
        nodes[key].cpu_file.write(payload) #debug

    elif(topic == "mem"):

        key = hash[ip]-1
        #global mem_usage
        #mem_usage[key-1].write(payload)
        nodes[key].mem_file.write(payload) #debug

    elif(topic == "disconnection"):
        print("recvd disconnect message") #debug
        #global connected_flags
        #connected_flags[hash[ip]] = 0
        key = hash[ip]-1
        nodes[key].disconnected = 1
        nodes[key].last_disconnect = payload
        print("ip: ", ip) #debug
        print("Last Disconnection: ",payload) #debug

    elif(topic == "change_var_response"):
        print("recvd change var response message") #debug
        key = hash[ip]-1
        message = json.loads(payload)
        nodes[key].old_threshold = message["from"]
        nodes[key].current_threshold = message["to"]
        print("ip, old threshold, current threshold: ",ip,' ,', nodes[key].old_threshold, ' ,', nodes[key.current_threshold]) #debug

def on_disconnect(client, userdata, rc):
    os.kill(os.getpid(), signal.SIGUSR1)

def on_log(client, userdata, level, buf):
    print("log: ",buf)

def Initialise_client_object():
    #flags set
    mqtt.Client.bad_connection_flag=False
    mqtt.Client.connected_flag=False
    mqtt.Client.disconnected_flag=False
    mqtt.Client.suback_flag=False


#Flask Web Application

# @app.route('/')
# def homepage():
#     return render_template('homepage.html')

# @app.route('/module')
# def mgmt_module():
#     return render_template('module.html')

# @app.route('/module/perf_monitor')
# def performance_monitor_module():

#     return render_template('perf_monitor.html', devices = devices)

# @app.route('/module/uptime_monitor')
# def uptime_monitor_module():
#     return render_template('uptime_monitor.html', database)

# @app.route('/module/thresh_adjust', methods=['POST', 'GET'])
# def change_var_module():

#     change_var_server = []
#     for i in range(NUM_NODES-1):
#     change_var_server.append(open("change_var_server"+str(i+1),"r"))

#     #makes fifo file that sends the data to the server
#     tmpdir = tempfile.mkdtemp()
#     filename = os.path.join(tmpdir, 'change_var_app')
#     try:
#         os.mkfifo(filename)
#     except OSError as e:
#         print ("Failed to create FIFO: %s") % e
#     else:
#         global change_var_app
#         change_var_app = open(filename, 'w')

#     return render_template('thresh_adjust.html')

#Bind callbacks
client = mqtt.Client(client_id="host", clean_session=False)
client.on_connect = on_connect
client.on_message = on_message
client.on_disconnect = on_disconnect
client.on_log=on_log
Initialise_client_object()

#connect to a broker
client.connect("10.158.56.21", 1883, 60)
if client.bad_connection_flag:
    client.loop_stop()    #Stop loop
    sys.exit()
client.loop_forever()

    #flask web app
    #app.run(host='0.0.0.0', port=port)