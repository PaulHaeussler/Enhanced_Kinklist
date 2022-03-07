import uuid

from loguru import logger
from flask import Flask, jsonify, request, render_template, make_response
from os.path import dirname, abspath

import json

class Kinklist:


    def __init__(self):
        json_file = dirname(abspath(__file__)) + "/enhanced_kinklist.json"
        self.config = json.load(open(json_file))
        logger.info("Starting up...")


    def get_val_string(self):
        result = ""
        for group in self.config['kink_groups']:
            for kink in group['rows']:
                result += str(kink['id'])
                for cols in group['columns']:
                    result += "=" + str(0)
                result += "#"
        return result


    @logger.catch
    def create_app(self):

        self.app = Flask(__name__)


        @self.app.route('/', methods = ['GET', 'POST'])
        def index():
            user = request.cookies.get('user', default='')
            secret = request.cookies.get('secret', default='')
            values = request.cookies.get('values', default='')

            if request.method == 'GET':

                res = make_response(render_template('index.html'))
                if values == '':
                    res.set_cookie('values', self.get_val_string())
                if user == '' or secret == '':
                    new_user = str(uuid.uuid4())
                    new_secret = str(uuid.uuid4())
                    res.set_cookie('user', new_user)
                    res.set_cookie('secret', new_secret)
                return res

            elif request.method == 'POST':
                inputs = request.get_json()


        @self.app.route('/results')
        def results():
            pass


        @self.app.route('/config')
        def config():
            response = jsonify(self.config)
            response.status_code = 200
            return response

        self.app.run(host='127.0.0.1', port=5000)

if __name__ == '__main__':
    k = Kinklist()
    k.create_app()
