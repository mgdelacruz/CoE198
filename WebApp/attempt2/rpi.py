import paho.mqtt.client as mqtt
import socket
import psutil
import fcntl
import struct
from datetime import datetime
import threading
import schedule
import logging
import sys
import json
import os

current_threshold = 37.5 #variable to be adjusted on prompt
old_threshold = None

def get_ip_address(ifname):
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    return socket.inet_ntoa(fcntl.ioctl(
        s.fileno(),
        0x8915, # SIOCGIFADDR
        struct.pack('256s', bytes(ifname[:15],'utf-8'))
    )[20:24])

local_ip = get_ip_address('eth0')

# The callback for when the client receives a CONNACK response from the server.
def on_connect(client, userdata, flags, rc):
    print("Connected with result code "+str(rc))

    # Subscribing in on_connect() means that if we lose the connection and
    # reconnect then subscriptions will be renewed.

    client.subscribe("change_var")

    try:
        cpu_thread = threading.Thread(target = cpu_monitor,args=())
        memory_thread = threading.Thread(target = memory_monitor,args=())
    except:
        print ("Error: unable to start thread")
        client.disconnect() # disconnect
    else:
        cpu_thread.daemon = True
        memory_thread.daemon = True
        cpu_thread.start()
        memory_thread.start()


def cpu_monitor():
    while(True):
        x=psutil.cpu_percent(interval=1)
        client.publish(local_ip+"/cpu",x)
        os.system(str(x) + " > cpu.txt")

def memory_monitor():
    while(True):
        x = str((psutil.virtual_memory().used/psutil.virtual_memory().total)*100)
        client.publish(local_ip+"/mem", x[0:5])
        os.system(str(x) + " > mem.txt")

# The callback for when a PUBLISH message is received from the server.
#handles change a variable feature
def on_message(client, userdata, msg):
    msg.payload = msg.payload.decode("utf-8")
    print(msg.topic+" "+str(msg.payload))

    global current_threshold
    global old_threshold
    old_threshold = current_threshold
    current_threshold = float(msg.payload)
    message = {
            "from":old_threshold,
            "to":current_threshold
    }
    to_pub = json.dumps(message)
    client.publish(local_ip+"/change_var_response", to_pub)
    print("Disconnection: ",message) #debug

def on_disconnect(client, userdata, rc):
    logging.info("disconnecting reason " + str(rc))
    client.connected_flag = False
    client.disconnect_flag = True
    client.loop_stop()    #Stop loop
    sys.exit()

client = mqtt.Client()
client.on_connect = on_connect
client.on_message = on_message
client.on_disconnect = on_disconnect
client.connect("10.158.56.21", 1883, 60)
client.will_set(local_ip+"/disconnect", "socket error")

# Blocking call that processes network traffic, dispatches callbacks and
# handles reconnecting.
# Other loop*() functions are available that give a threaded interface and a
# manual interface.
client.loop_forever()