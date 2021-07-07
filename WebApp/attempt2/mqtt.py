import paho.mqtt.client as mqtt
import os, tempfile
import sys
import time
import logging
import signal
import threading
import json

current_threshold = 37.5 #initial threshold value on pi
old_threshold = None
hash={} #stores ip to device no. mapping
IPs = [] #stores list of ip addresses read from a file
cpu_usage = []
mem_usage = []
server_to_app = None
change_var_error = None
change_var_app = None
filenames = []
tmpdirs = []
fps =[]

def ping_sweep():
    print("in fcn")
    global server_to_app
    for ip in IPs:
        print("in for loop")
        response = os.system("sudo ping -c 1 " + ip + " > dump.txt")
        #check the response:
        if (not response):
            message = {
                "ip":ip,
                "uptime":"CONNECTED"
            }
            to_write = json.dumps(message)
            server_to_app.write(to_write)
            print("ping sweep: ",message) #debug

        else:
            message = {
                "ip":ip,
                "uptime":"DISCONNECTED",
                "details":"no ping response"
            }
            to_write = json.dumps(message)
            server_to_app.write(to_write)
            print("ping sweep: ",message) #debug

# The callback for when the client receives a CONNACK response from the server.
def on_connect(client, userdata, flags, rc):

    global server_to_app
    if rc==0:
        client.connected_flag = True
        print("connected OK Returned code=",rc)
        # Subscribing in on_connect() means that if we lose the connection and
        # reconnect then subscriptions will be renewed.
        #client.subscribe("$SYS/broker/clients/connected")
        #client.subscribe("$SYS/broker/clients/disconnected")
        #client.subscribe("$SYS/broker/clients/total")
        #client.subscribe("$SYS/broker/time")

        #initialization
        signal.signal(signal.SIGINT, signal_handler)
        server_to_app = fifo('server_to_app', 0) #creates fifo for server to web app communicaton

        #performance monitor initialization and subscribe
        NUM_NODES = 0
        f = open("node_IPs.txt", "r")
        for ip in f:
            NUM_NODES = NUM_NODES+1
            global IPs
            IPs.append(ip.rstrip())
            client.subscribe(IPs[-1])
            global hash
            hash.update({IPs[-1] : NUM_NODES})
            global cpu_usage
            global mem_usage
            cpu_usage[NUM_NODES-1] = fifo('cpu_usage', NUM_NODES)
            mem_usage[NUM_NODES-1] = fifo('mem_usage', NUM_NODES)
            message = {
                "ip":IPs[-1],
                "num":NUM_NODES
            }
            to_write = json.dumps(message)
            server_to_app.write(to_write)
            print("hash table: ",message) #debug

        f.close()

        #start threshold adjustment thread
        global change_var_server
        global change_var_app
        change_var_server = fifo('change_var_server', 0)
        change_var_app = open('change_var', 'r')
        global fps
        fps.append(change_var_app)
        try:
            change_var_thread = threading.Thread(target = change_var,args=())
        except:
            print ("Error: unable to start thread")
            client.disconnect() # disconnect
        else:
            change_var_thread.daemon = True
            change_var_thread.start()

        #uptime monitor initialization
        ping_sweep()

    else:
        logging.info("Bad connection Returned code=",str(rc))
        client.bad_connection_flag=True

# The callback for when a PUBLISH message is received from the server.
def on_message(client, userdata, msg):
    global server_to_app
    raw_topic=msg.topic,
    payload=msg.payload.decode("utf-8")
    temp = raw_topic.split('/', 1)
    ip = temp[1]
    print(ip)
    topic = temp[2]
    print(topic)

    if(topic == "cpu"):
        key = hash[ip]
        global cpu_usage
        cpu_usage[key-1].write(payload)
        print("CPU usage: ",payload) #debug

    elif(topic == "mem"):
        key = hash[ip]
        global mem_usage
        mem_usage[key-1].write(payload)
        print("CPU usage: ",payload) #debug

    elif(topic == "disconnection"):
        message = {
                "ip":ip,
                "uptime":"DISCONNECTED",
                "details":payload
        }
        to_write = json.dumps(message)
        server_to_app.write(to_write)
        print("Disconnection: ",message) #debug

    elif(topic == "change_var_response"):
        message = {
                "ip":ip
        }
        message.update(json.loads(payload))
        to_write = json.dumps(message)
        server_to_app.write(to_write)
        print("Change Var Response: ",message) #debug

def on_disconnect(client, userdata, rc):
    raise(signal.SIGUSR1)

def on_log(client, userdata, level, buf):
    print("log: ",buf)

def Initialise_client_object():
    #flags set
    mqtt.Client.bad_connection_flag=False
    mqtt.Client.connected_flag=False
    mqtt.Client.disconnected_flag=False
    mqtt.Client.suback_flag=False

def signal_handler(signum, frame):
    for fp in fps:
        fp.close()
    for filename in filenames:
        os.remove(filename)
    for tmpdir in tmpdirs:
        os.rmdir(tmpdir)
    logging.info("disconnecting reason " + str(rc))
    client.connected_flag = False
    client.disconnect_flag = True
    client.loop_stop()    #Stop loop
    sys.exit()

def fifo(filename,loop):

    global filenames
    global tmpdirs
    global fps

    tmpdirs.append(tempfile.mkdtemp())
    if loop>0:
        filenames.append(os.path.join(tmpdirs[-1], filename+str(loop)))
    else:
        filenames.append(os.path.join(tmpdirs[-1], filename))

    try:
        os.mkfifo(filenames[-1])
    except OSError as e:
        print ("Failed to create FIFO: %s") % e
        client.loop_stop()    #Stop loop
        sys.exit()
    else:
        fp = open(filenames[-1], 'w')
        fps.append(fp)
        return fp

def change_var():
    while (True):
        value = float(change_var_app.read())
        if value == TypeError:
            change_var_error.write("Invalid Input")
            print("Change Var Error: Invalid Input")
        else:
            client.publish("change_var", value)

#Bind callbacks
client = mqtt.Client(client_id="server_client", clean_session=False)
client.on_connect = on_connect
client.on_message = on_message
client.on_disconnect = on_disconnect
client.on_log=on_log
Initialise_client_object()

#client.connect("127.0.0.1", 1883, 60)     #connect to broker
client.connect("10.158.56.21", 1883, 60)     #connect to broker
while not client.connected_flag and not client.bad_connection_flag: #wait in loop
    print("In wait loop")
if client.bad_connection_flag:
    client.loop_stop()    #Stop loop
    sys.exit()

client.loop_forever()