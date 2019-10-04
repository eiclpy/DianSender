import json
import os
import threading
import time
import logging

from flask import Flask, jsonify, redirect, render_template, request, url_for
from flask_httpauth import HTTPBasicAuth
from gevent.pywsgi import WSGIServer

from server import Server
from config import setting

app = Flask(__name__)
auth = HTTPBasicAuth()
pSend = None
percent = 0


def send(path):
    global percent
    server = Server(path)
    for i in server.send_all_mails():
        print(i, '%')
        percent = i
        time.sleep(0.5)


@auth.get_password
def get_password(username):
    if username == setting['username']:
        return setting['password']
    return None


@app.route('/', methods=['GET'])
@auth.login_required
def index():
    return app.send_static_file('index.html')


@app.route('/query', methods=['GET'])
@auth.login_required
def query():
    return app.send_static_file('query.html')


@app.route('/upload', methods=['POST'])
@auth.login_required
def upload():
    global pSend, percent
    if pSend and pSend.is_alive():
        return 'error'
    percent = 0
    qjson = request.get_json()
    fname = time.strftime('%Y-%m-%d-%H-%M-%S.json')
    path = os.path.join('jsons', fname)
    with open(path, 'w') as fp:
        json.dump(qjson, fp)
    pSend = threading.Thread(target=send, args=(path,))
    pSend.start()
    return 'ok'


@app.route('/queryPercent', methods=['GET'])
@auth.login_required
def queryPercent():
    global percent
    return jsonify(percent)


if not os.path.exists('jsons'):
    os.makedirs('jsons')

log = logging.getLogger('log')
errorlog = logging.getLogger('errorlog')

log.setLevel(logging.INFO)
errorlog.setLevel(logging.INFO)

loghandler = logging.FileHandler(filename="log.log")
errorloghandler = logging.FileHandler(filename="errorlog.log")
formatter = logging.Formatter("%(asctime)s %(name)s %(levelname)s %(message)s")

loghandler.setFormatter(formatter)
errorloghandler.setFormatter(formatter)

log.addHandler(loghandler)
errorlog.addHandler(errorloghandler)

http_server = WSGIServer((setting['listen'], setting['port']),
                         app, log=log, error_log=errorlog)
http_server.serve_forever()
