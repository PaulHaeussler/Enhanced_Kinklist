import time
import uuid
import argparse
import json
import logging

from loguru import logger
from flask import Flask, jsonify, request, render_template, make_response, url_for
from os.path import dirname, abspath



from werkzeug.utils import redirect

from db import MySQLPool

log = logging.getLogger('werkzeug')
log.setLevel(logging.ERROR)

class Kinklist:

    @logger.catch
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
                       pool_size=15)

    @logger.catch
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
    def get_item(self, meta, key):
        for m in meta:
                if m['id'] == key:
                    return m['val']

    @logger.catch
    def resolve_ids(self, data):
        result = []
        for group in self.config['kink_groups']:
            g = {"name": group['description'], "cols": self.__serialize_cols(group['columns'])}
            rows = []
            for k in group['rows']:
                vals = self.__get_id_val(k['id'], data)
                if vals is None:
                    vals = ["0"]
                rows.append({"name": k['description'], "vals": vals})
            g['rows'] = rows
            result.append(g)
        return result

    @logger.catch
    def __serialize_cols(self, cols):
        result = ""
        for col in cols:
            result += col + ", "
        return result[:-2]

    @logger.catch
    def __get_id_val(self, id, data):
        for d in data:
            if id == d['id']:
                return self.__get_color(json.loads(d['val'].replace('null', '\"0\"')))


    @logger.catch
    def __get_color(self, vals):
        result = []
        for val in vals:
            for choice in self.config['categories']:
                if int(val) == choice['id']:
                    result.append(choice['color'])
        return result

    @logger.catch
    def __log(self, req):
        ip = ""
        if request.environ.get('HTTP_X_FORWARDED_FOR') is None:
            ip = (request.environ['REMOTE_ADDR'])
        else:
            ip = (request.environ['HTTP_X_FORWARDED_FOR'])  # if behind a proxy
        logger.info(ip + " " + req.environ.get('REQUEST_URI'))
        self.db.execute("INSERT INTO hits(ip, timestamp, url, sec_ch_ua, sec_ch_ua_mobile, sec_ch_ua_platform, "
                        "user_agent, accept_language, path, query) VALUES(%s, %s, %s, %s, %s, %s, %s, %s, %s, %s);",
                        (ip, int(time.time()), req.environ.get('REQUEST_URI'), req.environ.get('HTTP_SEC_CH_UA'),
                         req.environ.get('HTTP_SEC_CH_UA_MOBILE'), req.environ.get('HTTP_SEC_CH_UA_PLATFORM'),
                         req.environ.get('HTTP_USER_AGENT'), req.environ.get('HTTP_ACCEPT_LANGUAGE'),
                         req.environ.get('PATH_INFO'), req.environ.get('QUERY_STRING')), commit=True)


    @logger.catch
    def create_app(self):

        self.app = Flask(__name__)


        @self.app.route('/', methods = ['GET', 'POST'])
        def index():
            self.__log(request)
            user = request.cookies.get('user', default='')
            secret = request.cookies.get('secret', default='')
            values = request.cookies.get('values', default='')

            if request.method == 'GET':

                res = make_response(render_template('index.html'))
                res.set_cookie('values', self.get_val_string())
                if user == '' or secret == '':
                    new_user = str(uuid.uuid4())
                    new_secret = str(uuid.uuid4())
                    res.set_cookie('user', new_user)
                    res.set_cookie('secret', new_secret)
                return res

            elif request.method == 'POST':
                inputs = request.get_json()

                if user == '' or secret == '':
                    return redirect(url_for('error.html'))
                else:
                    ip = ""
                    if request.environ.get('HTTP_X_FORWARDED_FOR') is None:
                        ip = (request.environ['REMOTE_ADDR'])
                    else:
                        ip = (request.environ['HTTP_X_FORWARDED_FOR'])  # if behind a proxy
                    logger.info(ip)
                    token = str(uuid.uuid4())
                    m = inputs['meta']
                    t = round(time.time()*1000)
                    if len(self.db.execute("SELECT * FROM users WHERE user=%s;", (user, ))) == 0:
                        self.db.execute("INSERT INTO users(user, username, sex, age, fap_freq, sex_freq, body_count, ip, created) VALUES(%s, %s, %s, %s, %s, %s, %s, %s, %s);", (user, self.get_item(m, 'name'), self.get_item(m, 'sex'), self.get_item(m, 'age'), self.get_item(m, 'fap_freq'), self.get_item(m, 'sex_freq'), self.get_item(m, 'body_count'), ip, t), commit=True)
                    uid = self.db.execute("SELECT id FROM users WHERE user=%s;", (user,))[0][0]

                    self.db.execute("INSERT INTO answers(user_id, timestamp, token, choices_json) VALUES(%s, %s, %s, %s);", (int(uid), t, token, json.dumps(inputs['kinks'])), commit=True)
                    logger.info("Created result token " + token)
                    res_results = make_response()
                    res_results.set_cookie('token', token)
                    return res_results
            elif request.method == 'HEAD':
                res = make_response()
                res.status_code = 200
                return res
            else:
                res = make_response()
                res.status_code = 501
                return res


        @self.app.route('/results')
        def results():
            self.__log(request)
            token = request.args.get('token', default='')

            if token == '':
                return redirect(url_for('index'))
            else:
                data = self.db.execute("SELECT * FROM answers INNER JOIN users ON answers.user_id=users.id WHERE token=%s;", (token,))
                res = make_response(render_template('results.html', kinks=self.resolve_ids(json.loads(data[0][3])), username=data[0][6], sex=data[0][7], age=data[0][8], fap_freq=data[0][9], sex_freq=data[0][10], body_count=data[0][11], created=[data[0][1]], choices=self.config['categories']))
                return res


        @self.app.route('/compare')
        def compare():
            self.__log(request)
            a = request.args.get('a', default='')
            b = request.args.get('b', default='')
            if a == '' or b == '':
                return redirect(url_for('index'))
            else:
                data_a = self.db.execute("SELECT * FROM answers INNER JOIN users ON answers.user_id=users.id WHERE token=%s;", (a,))
                data_b = self.db.execute("SELECT * FROM answers INNER JOIN users ON answers.user_id=users.id WHERE token=%s;", (b,))
                res = make_response(render_template('compare.html', kinks_a=self.resolve_ids(json.loads(data_a[0][3])), username_a=data_a[0][6], sex_a=data_a[0][7], age_a=data_a[0][8], fap_freq_a=data_a[0][9], sex_freq_a=data_a[0][10], body_count_a=data_a[0][11], created_a=[data_a[0][1]], choices=self.config['categories'],
                                                    kinks_b=self.resolve_ids(json.loads(data_b[0][3])), username_b=data_b[0][6], sex_b=data_b[0][7], age_b=data_b[0][8], fap_freq_b=data_b[0][9], sex_freq_b=data_b[0][10], body_count_b=data_b[0][11], created_b=[data_b[0][1]]))
                return res



        @self.app.route('/compare4')
        def compare4():
            self.__log(request)
            a = request.args.get('a', default='')
            b = request.args.get('b', default='')
            c = request.args.get('c', default='')
            d = request.args.get('d', default='')
            if a == '' or b == '':
                return redirect(url_for('index'))
            else:
                data_a = self.db.execute("SELECT * FROM answers INNER JOIN users ON answers.user_id=users.id WHERE token=%s;", (a,))
                data_b = self.db.execute("SELECT * FROM answers INNER JOIN users ON answers.user_id=users.id WHERE token=%s;", (b,))
                data_c = self.db.execute("SELECT * FROM answers INNER JOIN users ON answers.user_id=users.id WHERE token=%s;", (c,))
                data_d = self.db.execute("SELECT * FROM answers INNER JOIN users ON answers.user_id=users.id WHERE token=%s;", (d,))
                res = make_response(render_template('compare4.html', kinks_a=self.resolve_ids(json.loads(data_a[0][3])), username_a=data_a[0][6], sex_a=data_a[0][7], age_a=data_a[0][8], fap_freq_a=data_a[0][9], sex_freq_a=data_a[0][10], body_count_a=data_a[0][11], created_a=[data_a[0][1]], choices=self.config['categories'],
                                                    kinks_b=self.resolve_ids(json.loads(data_b[0][3])), username_b=data_b[0][6], sex_b=data_b[0][7], age_b=data_b[0][8], fap_freq_b=data_b[0][9], sex_freq_b=data_b[0][10], body_count_b=data_b[0][11], created_b=[data_b[0][1]],
                                                    kinks_c=self.resolve_ids(json.loads(data_c[0][3])), username_c=data_c[0][6], sex_c=data_c[0][7], age_c=data_c[0][8], fap_freq_c=data_c[0][9], sex_freq_c=data_c[0][10], body_count_c=data_c[0][11], created_c=[data_c[0][1]],
                                                    kinks_d=self.resolve_ids(json.loads(data_d[0][3])), username_d=data_d[0][6], sex_d=data_d[0][7], age_d=data_d[0][8], fap_freq_d=data_d[0][9], sex_freq_d=data_d[0][10], body_count_d=data_d[0][11], created_d=[data_d[0][1]]))
                return res


        @self.app.route('/config')
        def config():
            self.__log(request)
            response = jsonify(self.config)
            response.status_code = 200
            return response

        self.app.run(host='0.0.0.0', port=5000)

if __name__ == '__main__':
    k = Kinklist()
    k.create_app()
