import paho.mqtt.client as mqtt
import socket
import psutil
#import time
import fcntl
import struct
from datetime import datetime

thresh = 37.5
ifname = socket.gethostname()
print(ifname)
def get_ip_address(ifname):
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    return socket.inet_ntoa(fcntl.ioctl(
        s.fileno(),
        0x8915, # SIOCGIFADDR
        struct.pack('256s', ifname[:15])
    )[20:24])
local_ip = get_ip_address('eth0')

#local_ip = socket.gethostbyname(hostname)
#local_ip = socket.gethostbyname()
#print(local_ip)


# The callback for when the client receives a CONNACK response from the server.
def on_connect(client, userdata, flags, rc):
    print("Connected with result code "+str(rc))

    # Subscribing in on_connect() means that if we lose the connection and
    # reconnect then subscriptions will be renewed.

    client.subscribe("flags")

# The callback for when a PUBLISH message is received from the server.
def on_message(client, userdata, msg):
    msg.payload = msg.payload.decode("utf-8")
    print(msg.topic+" "+str(msg.payload))

    if(str(msg.payload) == "uptime"):
        print(local_ip+"/uptime")
        timestamp = datetime.now().strftime("%d/%m/%Y, %H:%M:%S")
        client.publish(local_ip+"/connection_status",local_ip + " CONNECTED as of " + timestamp)

    elif(str(msg.payload) == "performance"):

        #print(local_ip+"/perf")
        #psutil.cpu_percent(interval=None, percpu=False)
        #time.sleep(0.2)
        client.publish(local_ip+"/cpu",psutil.cpu_percent(interval=1))
        x = str((psutil.virtual_memory().used/psutil.virtual_memory().total)*100)
        client.publish(local_ip+"/mem", "Memory Usage: " + x[0:5] + "%")

    elif(str(msg.payload)=="disconnect"):
        timestamp = datetime.now().strftime("%d/%m/%Y, %H:%M:%S")
        client.publish(local_ip+"/connection_status", local_ip + " DISCONNECTED as of " + timestamp)
        client.publish(local_ip+"/disconnection_log", "Disconnected by host")
        client.loop_stop()
        client.disconnect()
    else:
        global thresh
        old_thresh = thresh
        thresh = float(msg.payload)
        print("old thresh: " +str(old_thresh))
        print("new thresh: " + str(thresh))
        print(local_ip+"/thresh")
        client.publish(local_ip+"/thresh", "threshold has been changed from " + str(old_thresh)+" to " + str(thresh))

client = mqtt.Client()
client.on_connect = on_connect
client.on_message = on_message
#client.connect("127.0.0.1", 1883,60)
client.connect("10.158.56.21", 1883, 60)
client.will_set(local_ip+"/connection_status", local_ip + " DISCONNECTED")
client.will_set(local_ip+"/disconnection_log", "Due to socket error")

# Blocking call that processes network traffic, dispatches callbacks and
# handles reconnecting.
# Other loop*() functions are available that give a threaded interface and a
# manual interface.
client.loop_forever()
