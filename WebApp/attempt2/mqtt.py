import paho.mqtt.client as mqtt
import os, tempfile
import schedule
import sys
import time
import logging
import signal
import thread

def ping_sweep():
    f = open("node_IPs.txt", "r")
    print("in fcn")
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
    f.close()

# The callback for when the client receives a CONNACK response from the server.
def on_connect(client, userdata, flags, rc):

    if rc==0:
        f = open("node_IPs.txt", "r")
        print("connected OK Returned code=",rc)
        # Subscribing in on_connect() means that if we lose the connection and
        # reconnect then subscriptions will be renewed.
        client.connected_flag = True
        client.subscribe("$SYS/broker/clients/connected")
        client.subscribe("$SYS/broker/clients/disconnected")
        client.subscribe("$SYS/broker/clients/total")
        client.subscribe("$SYS/broker/time")

        for ip in f:
            ip = ip.replace('\n','/+')
            print(ip)
            client.subscribe(ip)
        f.close()
    else:
        logging.info("Bad connection Returned code=",str(rc))
        client.bad_connection_flag=True

# The callback for when a PUBLISH message is received from the server.
def on_message(client, userdata, msg):
    raw_topic=msg.topic,
    payload=msg.payload.decode("utf-8")
    temp = raw_topic.split('/', 1)
    ip = temp[1]
    print(ip)
    topic = temp[2]
    print(topic)
    if(topic == "cpu"):
        key = hash[ip]
        cpu_usage[key-1].write(payload)

    elif(topic == "mem"):
        key = hash[ip]
        mem_usage[key-1].write(payload)


# Logs disconnection and set flags for disconnection detection
def on_disconnect(client, userdata, rc):
    logging.info("disconnecting reason " + str(rc))
    client.connected_flag = False
    client.disconnect_flag = True
    client.loop_stop()

def on_log(client, userdata, level, buf):
    print("log: ",buf)

def Initialise_client_object():
  #flags set
    mqtt.Client.bad_connection_flag=False
    mqtt.Client.connected_flag=False
    mqtt.Client.disconnected_flag=False
    mqtt.Client.suback_flag=False

def signal_handler(signum, frame):
    for x in cpu_usage:
        x.close()
    for x in mem_usage:
        x.close()
    #app_to_server.close()
    for filename in filenames:
        os.remove(filename)
    for tmpdir in tmpdirs:
        os.rmdir(tmpdir)
    client.loop_stop()    #Stop loop
    client.disconnect() # disconnect
    sys.exit()

def fifo(filename,loop):
    global filenames
    global tmpdirs
    filenames = []
    tmpdirs = []
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
        return fp

def change_var():
    change_var_server = fifo('change_var_server', 0)
    change_var_app = open('change_var', 'r')
    while (True):
        value = float(change_var_app.read())
        if value == TypeError:
            change_var_server.write("Please Enter Valid Value")
        else:
            client.publish("change_var", value)

client = mqtt.Client(client_id="server_client", clean_session=False)
client.on_connect = on_connect
client.on_message = on_message
client.on_disconnect = on_disconnect
client.on_log=on_log

client.loop_start() #main loop

signal.signal(signal.SIGINT, signal_handler)
Initialise_client_object()

try:
    thread.start_new_thread(change_var)
except:
   print ("Error: unable to start thread")
   raise(signal.SIGINT)

perf_to_app = fifo('perf_to_app', 0)

NUM_NODES = 0
global hash
f = open("node_IPs.txt", "r")
for ip in f:
    NUM_NODES = NUM_NODES+1
    ip = ip.rstrip()
    hash = dict(ip, NUM_NODES)
f.close()

global cpu_usage
cpu_usage = []
for i in range(NUM_NODES-1):
    perf_to_app = fifo('perf_to_app', i+1)

global mem_usage
mem_usage = []
for i in range(NUM_NODES-1):
    perf_to_app = fifo('perf_to_app', i+1)

#client.connect("127.0.0.1", 1883, 60)     #connect to broker
client.connect("10.158.56.21", 1883, 60)     #connect to broker
while not client.connected_flag and not client.bad_connection_flag: #wait in loop
    print("In wait loop")
    time.sleep(1)
if client.bad_connection_flag:
    client.loop_stop()    #Stop loop
    sys.exit()