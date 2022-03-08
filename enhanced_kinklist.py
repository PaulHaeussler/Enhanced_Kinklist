import uuid
import argparse
import json

from loguru import logger
from flask import Flask, jsonify, request, render_template, make_response, url_for
from os.path import dirname, abspath



from werkzeug.utils import redirect

from db import MySQLPool


class Kinklist:


    def __init__(self):
        json_file = dirname(abspath(__file__)) + "/enhanced_kinklist.json"
        self.config = json.load(open(json_file))
        logger.info("Starting up...")

        parser = argparse.ArgumentParser(
            description='Bot to provide tracking of submissions in certain discord channels')
        parser.add_argument('dbhost')
        parser.add_argument('dbschema')
        parser.add_argument('dbuser')
        parser.add_argument('dbpw')
        args = vars(parser.parse_args())

        self.db = MySQLPool(host=args['dbhost'], user=args['dbuser'], password=args['dbpw'], database=args['dbschema'],
                       pool_size=5)

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
                
                res = make_response(redirect(url_for('results.html')))
                
                if user == '' or secret == '':
                    return redirect(url_for('error.html'))
                else:
                    logger.info(request.environ.get('HTTP_X_REAL_IP', request.remote_addr))
                    return res




        @self.app.route('/results')
        def results():
            res = make_response(render_template('results.html'))
            return res


        @self.app.route('/config')
        def config():
            response = jsonify(self.config)
            response.status_code = 200
            return response

        self.app.run(host='0.0.0.0', port=5000)

if __name__ == '__main__':
    k = Kinklist()
    k.create_app()
