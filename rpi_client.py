import paho.mqtt.client as mqtt
import socket
import psutil
#from psutil._common import bytes2human
#import time

thresh = 37.5
hostname = socket.gethostname()
local_ip = socket.gethostbyname(hostname)
#p = psutil.Process(os.getpid())

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
    fmsg = float(msg.payload)
    if(!fmsg):
        print(local_ip+"/uptime")
        client.publish(local_ip+"/uptime","CONNECTED")
    
    elif(fmsg> 1):
        global thresh
        old_thresh = thresh
        thresh = fmsg
        client.publish(local_ip+"/thresh", "Threshold changed from " + str(old_thresh) + "to " + str(thresh))

    elif(fmsg<0):
        client.loop_stop()
        client.disconnect()
    else:
        print(local_ip+"/perf")
        client.publish(local_ip+"/perf","CPU usage: " + str(psutil.cpu_percent(interval=10)) + "%")
        x = str((psutil.virtual_memory().used/psutil.virtual_memory().total)*100)
        client.publish(local_ip+"/perf", "Memory usage: " + x[0:5] + "%")

client = mqtt.Client()
client.on_connect = on_connect
client.on_message = on_message
client.connect("127.0.0.1", 1883,60)
#client.connect("10.158.56.21", 1883, 60)

# Blocking call that processes network traffic, dispatches callbacks and
# handles reconnecting.
# Other loop*() functions are available that give a threaded interface and a
# manual interface.
client.loop_forever()
