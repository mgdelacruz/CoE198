from flask import Flask, render_template, url_for, request, redirect
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
import os, tempfile
import logging
import json

logging.basicConfig(
                    filename='app.log',
                    filemode='w',
                    format='%(name)s - %(levelname)s - %(message)s'
                    )

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
db_path = os.path.join(BASE_DIR, "catifs.db")
app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + db_path
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

class Nodes(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    device = db.Column(db.String(200), nullable=False)
    ip = db.Column(db.String(15), primary_key=True)
#class Performance(db.Model):
    cpu = db.Column(db.Float, nullable=True)
    memory = db.Column(db.Float, nullable=True)
#class Uptime(db.Model):
#    status = db.Column(db.String(15), nullable = False)
#    last_disconnect = db.Column(db.DateTime)
#    disconnection_details = db.Column(db.Text)
#class Threshold(db.Model):
#    current_threshold = (db.Float, nullable=False)
    def __repr__(self):
        return '<Node %r>' %self.id

f = open("node_IPs.txt", "r")
IPs = []
for ip in f:
    IPs.append(ip.rstrip())

@app.route('/')
def homepage():
    return render_template('homepage.html')

@app.route('/module')
def mgmt_module():
    return render_template('module.html')

@app.route('/module/perf_monitor')
def performance_monitor():
    #do something here to connect to mqtt i guess
    devices = Nodes.query.order_by(Nodes.id).all()
    #return render_template('product-page.html', tasks = tasks)
    return render_template('perf_monitor.html', devices = devices)

#@app.route('/module/uptime_monitor')
#def uptime_monitor():
#    return render_template('uptime_monitor.html')

#@app.route('/module/thresh_adjust', methods=['POST', 'GET'])
#def performance_monitor():
#    mqtt.publish('flag', '36.5')
#    return render_template('thresh_adjust.html')

if __name__=="__main__":

    tmpdir = tempfile.mkdtemp()
    filename = os.path.join(tmpdir, '')
    try:
        os.mkfifo(filename)
    except OSError as e:
        print ("Failed to create FIFO: %s") % e
    else:
        global fifo
        fifo_write = open(filename, 'w')
        fifo_read = open('mqtt-flask-fifo', 'r')
        app.run(host=os.getenv('IP', '0.0.0.0'),
                port=int(os.getenv('PORT',4444)))
        fifo_write.close()
        fifo_read.close()
        os.remove(filename)
        os.rmdir(tmpdir)
