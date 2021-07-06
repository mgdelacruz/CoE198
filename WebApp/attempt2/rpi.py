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

threshold = 37.5 #variable to be adjusted on prompt
local_ip = None

def get_ip_address(ifname):
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    return socket.inet_ntoa(fcntl.ioctl(
        s.fileno(),
        0x8915, # SIOCGIFADDR
        struct.pack('256s', bytes(ifname[:15],'utf-8'))
    )[20:24])


# The callback for when the client receives a CONNACK response from the server.
def on_connect(client, userdata, flags, rc):
    print("Connected with result code "+str(rc))

    global local_ip
    local_ip = get_ip_address('eth0')

    # Subscribing in on_connect() means that if we lose the connection and
    # reconnect then subscriptions will be renewed.

    client.subscribe("change_var")

    try:
        cpu_thread = threading.Thread(cpu_monitor)
        memory_thread = threading.Thread(memory_monitor)
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
        client.publish(local_ip+"/cpu",psutil.cpu_percent(interval=1))

def memory_monitor():
    while(True):
        x = str((psutil.virtual_memory().used/psutil.virtual_memory().total)*100)
        client.publish(local_ip+"/mem", "Memory Usage: " + x[0:5] + "%")

# The callback for when a PUBLISH message is received from the server.
#handles change a variable feature
def on_message(client, userdata, msg):
    msg.payload = msg.payload.decode("utf-8")
    print(msg.topic+" "+str(msg.payload))

    global thresh
    old_thresh = thresh
    thresh = float(msg.payload)
    print("old thresh: " +str(old_thresh))
    print("new thresh: " + str(thresh))
    client.publish(local_ip+"/", "threshold has been changed from " + str(old_thresh)+" to " + str(thresh))

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