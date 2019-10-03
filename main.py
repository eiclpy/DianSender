import json
import os
import threading
import time

from flask import Flask, jsonify, redirect, render_template, request, url_for
from flask_httpauth import HTTPBasicAuth

from server import Server
from config import username, password, listen, port

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
    if username == username:
        return password
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

app.run(host=listen, port=port)
