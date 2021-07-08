from flask import Flask, render_template, url_for, request, redirect
#from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
import os, tempfile
import logging
import json

logging.basicConfig(
                    filename='app.log',
                    filemode='w',
                    format='%(name)s - %(levelname)s - %(message)s'
                    )

app = Flask(__name__)

#Global Variables
IPs = []
hash = {}
fps = []
NUM_NODES = None

f = open("node_IPs.txt", "r")
for ip in f:
    #populate hash table, initialize connected flags and subscribe
    NUM_NODES = NUM_NODES+1
    IPs.append(ip.rstrip())
    hash.update({IPs[-1] : NUM_NODES})
f.close()

@app.route('/')
def homepage():

    fifo_read = open('mqtt-flask-fifo', 'r')
    return render_template('homepage.html')

@app.route('/module')
def mgmt_module():
    return render_template('module.html')

@app.route('/module/perf_monitor')
def performance_monitor():
    cpu = []
    for
    return render_template('perf_monitor.html', devices = devices)

@app.route('/module/uptime_monitor')
def uptime_monitor():
    #makes fifo file that sends the data to the server
    tmpdir = tempfile.mkdtemp()
    filename = os.path.join(tmpdir, 'ping_prompt')
    try:
        os.mkfifo(filename)
    except OSError as e:
        print ("Failed to create FIFO: %s") % e
    else:
        global change_var_app
        ping_prompt = open(filename, 'w')
    return render_template('uptime_monitor.html')

@app.route('/module/thresh_adjust', methods=['POST', 'GET'])
def change_var():

    change_var_server = []
    for i in range(NUM_NODES-1):
    change_var_server.append(open("change_var_server"+str(i+1),"r"))

    #makes fifo file that sends the data to the server
    tmpdir = tempfile.mkdtemp()
    filename = os.path.join(tmpdir, 'change_var_app')
    try:
        os.mkfifo(filename)
    except OSError as e:
        print ("Failed to create FIFO: %s") % e
    else:
        global change_var_app
        change_var_app = open(filename, 'w')

    return render_template('thresh_adjust.html')

if __name__=="__main__":

    app.run(host=os.getenv('IP', '0.0.0.0'),
            port=int(os.getenv('PORT',4444)))


    os.remove(filename)
    os.rmdir(tmpdir)
