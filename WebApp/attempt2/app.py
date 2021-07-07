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

IPs = []
f = open("node_IPs.txt", "r")
for ip in f:
    IPs.append(ip.rstrip())
    NUM_NODES
f.close()

change_var_server = []      #fifo files from server to app where each device being monitored acks change var
ping_prompt = None          #fifo file that gets prompt to ping devices


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

#@app.route('/module/uptime_monitor')
#def uptime_monitor():
#    return render_template('uptime_monitor.html')

#@app.route('/module/thresh_adjust', methods=['POST', 'GET'])
#def change_var():
    #makes fifo file that sends the data to the server
    #tmpdir = tempfile.mkdtemp()
    #filename = os.path.join(tmpdir, 'change_var_app')
    #try:
    #    os.mkfifo(filename)
    #except OSError as e:
    #    print ("Failed to create FIFO: %s") % e
    #else:
    #    global fifo
    #    fifo_write = open(filename, 'w')
#
#    return render_template('thresh_adjust.html')

if __name__=="__main__":

    app.run(host=os.getenv('IP', '0.0.0.0'),
            port=int(os.getenv('PORT',4444)))

    fifo_write.close()
    fifo_read.close()
    os.remove(filename)
    os.rmdir(tmpdir)
