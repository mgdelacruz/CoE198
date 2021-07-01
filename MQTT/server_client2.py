import paho.mqtt.client as mqtt

f = open("node_IPs.txt", "r")

# The callback for when the client receives a CONNACK response from the server.
def on_connect(client, userdata, flags, rc):
    print("Connected with result code "+str(rc))

    # Subscribing in on_connect() means that if we lose the connection and
    # reconnect then subscriptions will be renewed.
    client.subscribe("$SYS/broker/clients/connected")
    client.subscribe("$SYS/broker/clients/disconnected")
    client.subscribe("$SYS/broker/clients/total")
    client.subscribe("$SYS/broker/time")

    for x in f:
        x = x.replace('\n','/+')
        print(x)
        client.subscribe(x)

# The callback for when a PUBLISH message is received from the server.
def on_message(client, userdata, msg):
    msg.payload = msg.payload.decode("utf-8")
    print(msg.topic+" "+str(msg.payload))
    client.publish("flags", "uptime")
    client.publish("flags", "performance")
    client.publish("flags", "36.7")
   # client.publish("threshold", "36.7")
    client.publish("flags", "disconnect")

# Logs disconnection and set flags for disconnection detection
def on_disconnect(client, userdata, rc):
#    logging.info("disconnecting reason " + str(rc))
    client.connected_flag = False
    client.disconnect_flag = True
    client.loop_stop()

client = mqtt.Client(client_id="server_client", clean_session=False)
client.on_connect = on_connect
client.on_message = on_message
client.on_disconnect = on_disconnect
client.connect("127.0.0.1", 1883, 60)

# Blocking call that processes network traffic, dispatches callbacks and
# handles reconnecting.
# Other loop*() functions are available that give a threaded interface and a
# manual interface.
client.loop_forever()
