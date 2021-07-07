import paho.mqtt.client as mqtt
import os, tempfile
import sys
import time
import logging
import signal
import threading
import json

#global variables
current_threshold = 37.5    #initial threshold value on pi
old_threshold = None
hash={}                     #stores ip to device no. mapping
IPs = []                    #stores list of ip addresses read from a file
change_var_server = []      #fifo files from server to app where each device being monitored acks change var
change_var_app = None       #fifo from app to server where app communicates value to change var
filenames = []              #list of filenames of each fifo used for cleanup upon server disconnect
tmpdirs = []                #paths of fifos used for cleanup upon server disconnect
fps =[]                     #file pointers to be closed upon server disconnect
cpu = []                    #array of file pointers to text file where cpu data for each node is dumped
mem = []                    #array of file pointers to text file where memory data for each node is dumped
connected_flags = []        #used for uptime monitoring
ping_prompt = None          #fifo file that gets prompt to ping devices

def fifo(filename,loop):

    print("making fifo file") #debug

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
        print("made a fifo file with filename: ", filenames[-1])
        fp = open(filenames[-1], 'w')
        print("opened a fifo file: ", str(fp))
        fps.append(fp)
        return fp

def signal_handler(signum, frame):
    global cpu
    global mem
    cpu.close() #debug
    mem.close() #debug
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

def ping_sweep():
    print("in fcn")
    global server_to_app
    for ip in IPs:
        print("in for loop")
        response = os.system("sudo ping -c 1 " + ip + " > dump.txt")
        dev_no = hash[ip]
        #check the response:
        if (not response):
            connected_flags[dev_no-1] = 1
        else:
            connected_flags[dev_no-1] = 0

def ping_prompt_loop():
    global ping_prompt
    while(True):
        prompt = ping_prompt.read(1)
        if prompt:
            ping_sweep()


def uptime_monitor(ip, local_flag):
    global uptime_app
    dev_no = hash[ip]
    uptime_app = fifo('uptime_app', dev_no) #creates fifo for server to web app communicaton
    if(local_flag):
                message = {
                        "ip":ip,
                        "uptime":"CONNECTED"
                }
    else:
            message = {
                "ip":ip,
                "uptime":"DISCONNECTED",
            }
    to_write = json.dumps(message)
    uptime_app.write(to_write)

    while(True):
        if local_flag != connected_flags[dev_no-1]:
            local_flag = connected_flags[dev_no-1]
            if(local_flag):
                message = {
                        "ip":ip,
                        "uptime":"CONNECTED"
                }
            else:
                message = {
                    "ip":ip,
                    "uptime":"DISCONNECTED",
                }
            to_write = json.dumps(message)
            uptime_app.write(to_write)

def change_var(NUM_NODES):
    global change_var_server
    global change_var_app
    global fps
    change_var_app = open('change_var_app', 'r')
    fps.append(change_var_app)
    for i in range(NUM_NODES-1):
        change_var_server.append(fifo('change_var_server', i+1))
    while (True):
        value = float(change_var_app.read())
        print("read change var file") #debug
        client.publish("change_var", value)


# The callback for when the client receives a CONNACK response from the server.
def on_connect(client, userdata, flags, rc):

    #global server_to_app
    if rc==0:
        client.connected_flag = True
        print("connected OK Returned code=",rc)

        signal.signal(signal.SIGINT, signal_handler)
        NUM_NODES = 0
        uptime_threads = []
        f = open("node_IPs.txt", "r")
        for ip in f:
            print("iterating through ips in node_ip.txt") #debug

            global IPs
            global hash
            NUM_NODES = NUM_NODES+1
            IPs.append(ip.rstrip())
            hash.update({IPs[-1] : NUM_NODES})
            client.subscribe(IPs[-1])

            #performance monitor initialization
            global cpu
            global mem
            cpu.append(open("cpu"+str(NUM_NODES)+".txt", "a"))
            mem.append(open("mem"+str(NUM_NODES)+".txt", "a"))
            print("opened cpu and mem files") #debug

            #uptime monitor initialization
            global ping_prompt
            ping_prompt=open("ping_prompt", "r")
            print("start ping prompt thread") #debug
            try:
                ping_prompt = threading.Thread(target = ping_prompt_loop,args=())
            except:
                print ("Error: unable to start uptime thread")
                client.disconnect() # disconnect
            else:
                ping_prompt.daemon = True
                ping_prompt.start()

            print("initializing uptime monitor threads") #debug
            ping_sweep()
            print("ping sweeped") #debug
            try:
                uptime_threads.append(threading.Thread(target = uptime_monitor,args=(IPs[-1],connected_flags[NUM_NODES-1],)))
            except:
                print ("Error: unable to start uptime thread")
                client.disconnect() # disconnect
            else:
                uptime_threads[-1].daemon = True
                uptime_threads[-1].start()

        print("done iterating through ips in node_ip.txt") #debug
        f.close()

        #start threshold adjustment thread
        print("initializing threshold adjustment thread") #debug
        try:
            change_var_thread = threading.Thread(target = change_var,args=(NUM_NODES,))
        except:
            print ("Error: unable to start change var thread")
            client.disconnect() # disconnect
        else:
            change_var_thread.daemon = True
            change_var_thread.start()

        #start ping prompt thread
        print("initializing ping prompt thread") #debug
        try:
            ping_prompt_thread = threading.Thread(target = ping_prompt_loop,args=())
        except:
            print ("Error: unable to start change var thread")
            client.disconnect() # disconnect
        else:
            change_var_thread.daemon = True
            change_var_thread.start()

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
        print("recvd cpu message") #debug

        key = hash[ip]
        global cpu_usage
        #cpu_usage[key-1].write(payload)
        cpu[key-1].write(payload) #debug

    elif(topic == "mem"):
        print("recvd mem message") #debug

        key = hash[ip]
        global mem_usage
        #mem_usage[key-1].write(payload)
        mem.write(payload) #debug

    elif(topic == "disconnection"):
        print("recvd disconnect message") #debug
        global connected_flags
        connected_flags[hash[ip]] = 0
        print("Disconnection: ",payload) #debug

    elif(topic == "change_var_response"):
        print("recvd change var response message") #debug
        message = {
                "ip":ip
        }
        message.update(json.loads(payload))
        to_write = json.dumps(message)
        global change_var_server
        change_var_server[hash[ip]].write(to_write)
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


#Bind callbacks
client = mqtt.Client(client_id="server_client", clean_session=False)
client.on_connect = on_connect
client.on_message = on_message
client.on_disconnect = on_disconnect
client.on_log=on_log
Initialise_client_object()

#connect to broker
#client.connect("127.0.0.1", 1883, 60)
client.connect("10.158.56.21", 1883, 60)
if client.bad_connection_flag:
    client.loop_stop()    #Stop loop
    sys.exit()

client.loop_forever()