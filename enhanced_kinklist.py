import random
import string
import time
import traceback
import uuid
import json
import logging
import os
import copy
import collections
import re
import hashlib
import secrets
from datetime import datetime
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from loguru import logger
from flask import Flask, jsonify, request, render_template, make_response, url_for, send_from_directory
from os.path import dirname, abspath



from werkzeug.utils import redirect

from db import MySQLPool
from db_postgres import PostgresPool


force_mobile = False
DEFAULT_CATALOG_ID = "main"
DEFAULT_CATALOG_VERSION = "legacy"
DEFAULT_DOMAIN = "irl"
DEFAULT_SPICE_LEVEL = 2
DEFAULT_VISIBILITY = "default"
DEFAULT_ANSWER_CONTEXT = "realistic_adult_partner"
CATALOG_SNAPSHOT_DIR = "catalog_snapshots"
RESULT_TOKEN_PATTERN = re.compile(r"^[A-Za-z0-9_-]{5,64}$")
SENSITIVE_LOG_KEYS = {"token", "a", "b", "c", "d", "secret", "password", "cookie", "authorization"}
SAFE_PUBLIC_PATH_SEGMENTS = {
    "android-chrome-192x192.png",
    "android-chrome-512x512.png",
    "apple-touch-icon.png",
    "byid",
    "cinfo",
    "compare",
    "compare4",
    "config",
    "favicon-16x16.png",
    "favicon-32x32.png",
    "favicon.ico",
    "globalStats",
    "jump",
    "kot",
    "log_client_error",
    "meta",
    "missingKink",
    "party",
    "quiz",
    "results",
    "robots.txt",
    "sitemap.xml",
}

log = logging.getLogger('werkzeug')
log.setLevel(logging.ERROR)
log_dir = os.environ.get("LOG_DIR", ".")
os.makedirs(log_dir, exist_ok=True)
logger.add(os.path.join(log_dir, "latest.log"))

# Configure separate error logger
error_logger = logger.bind(name="errors")
error_logger.add(
    os.path.join(log_dir, "errors_{time:YYYY-MM-DD}.log"),
    format="{time:YYYY-MM-DD HH:mm:ss.SSS} | {level} | {message} | {extra}",
    rotation="00:00",  # Rotate daily
    retention="30 days",  # Keep error logs for 30 days
    level="WARNING",  # Only log warnings and above
    backtrace=True,
    diagnose=True,  # Add extra diagnostic info
)

def get_cat(color, colors):
    for c in colors:
        if str(c.get('color')) == str(color) or str(c.get('id')) == str(color):
            return c['description']
    return 'UNKNOWN CATEGORY'

def read_args():
    import argparse
    parser = argparse.ArgumentParser(
        description='Bot to provide tracking of submissions in certain discord channels')
    parser.add_argument('dbhost')
    parser.add_argument('dbschema')
    parser.add_argument('dbuser')
    parser.add_argument('dbpw')
    args = vars(parser.parse_args())
    return args

class Kinklist:

    @logger.catch
    def __init__(self, dbhost=None, dbuser=None, dbpw=None, dbschema=None):
        json_file = dirname(abspath(__file__)) + "/enhanced_kinklist.json"
        with open(json_file) as config:
            self.config = json.load(config)
        self.__normalize_config()
        self.catalog_snapshots = self.__load_catalog_snapshot_files()
        logger.info("Starting up...")

        byid = {}
        for group in self.config['kink_groups']:
            for kink in group['rows']:
                tip = ''
                if "tip" in kink.keys():
                    tip = kink["tip"]
                byid[kink['id']] = {
                    "name": kink["description"],
                    "tip": tip,
                    "group_name": group["description"],
                    "group_tip": group["tip"],
                    "cols": group["columns"],
                    "domain": kink["domain"],
                    "spice_level": kink["spice_level"],
                    "visibility": kink["visibility"],
                    "flags": kink["flags"],
                    "aliases": kink["aliases"],
                }

        self.byid = collections.OrderedDict(sorted(byid.items()))

        if dbhost is None:
            args = read_args()
            dbhost = args['dbhost']
            dbuser = args['dbuser']
            dbpw = args['dbpw']
            dbschema = args['dbschema']


        # DB_BACKEND=mysql is the rollback path during the Postgres cutover.
        if os.environ.get("DB_BACKEND", "postgres").lower() == "mysql":
            self.db = MySQLPool(host=dbhost, user=dbuser, password=dbpw, database=dbschema,
                           pool_size=15)
        else:
            self.db = PostgresPool(host=dbhost, port=os.environ.get("DB_PORT", "5432"),
                                   user=dbuser, password=dbpw, database=dbschema,
                                   pool_size=15)
        self.__ensure_catalog_snapshots()
        self.__load_catalog_snapshots_from_db()
        self.results = []
        for r in self.db.execute("SELECT token FROM answers;") or []:
            self.results.append(r[0])


    def __normalize_config(self):
        self.config.setdefault("catalog_id", DEFAULT_CATALOG_ID)
        self.config.setdefault("catalog_version", DEFAULT_CATALOG_VERSION)
        self.config.setdefault("default_domain", DEFAULT_DOMAIN)
        self.config.setdefault("default_spice_level", DEFAULT_SPICE_LEVEL)
        self.config.setdefault("default_visibility", DEFAULT_VISIBILITY)
        self.config.setdefault("default_answer_context", DEFAULT_ANSWER_CONTEXT)
        self.config.setdefault("answer_contexts", [
            {
                "id": DEFAULT_ANSWER_CONTEXT,
                "label": "Realistic adult partner",
                "description": "Answer for a consenting adult partner you would realistically choose for this activity, not necessarily your current partner.",
            }
        ])

        for group in self.config["kink_groups"]:
            group.setdefault("domain", self.config["default_domain"])
            group.setdefault("spice_level", self.config["default_spice_level"])
            group.setdefault("visibility", self.config["default_visibility"])
            group.setdefault("flags", [])

            for kink in group["rows"]:
                kink.setdefault("domain", group["domain"])
                kink.setdefault("spice_level", group["spice_level"])
                kink.setdefault("visibility", group["visibility"])
                kink.setdefault("flags", list(group["flags"]))
                kink.setdefault("aliases", [])

    def __load_catalog_snapshot_files(self):
        snapshots = {}
        snapshot_dir = os.path.join(dirname(abspath(__file__)), CATALOG_SNAPSHOT_DIR)
        if not os.path.isdir(snapshot_dir):
            return snapshots

        for filename in os.listdir(snapshot_dir):
            if not filename.endswith(".json"):
                continue
            path = os.path.join(snapshot_dir, filename)
            try:
                with open(path) as snapshot_file:
                    snapshot = self.__normalize_catalog_snapshot(json.load(snapshot_file))
            except Exception as e:
                logger.warning(f"Could not load catalog snapshot {path}: {e}")
                continue
            snapshots[(snapshot["catalog_id"], snapshot["catalog_version"])] = snapshot

        current_key = (self.get_catalog_id(), self.get_catalog_version())
        legacy_key = (self.get_catalog_id(), DEFAULT_CATALOG_VERSION)
        if current_key in snapshots and legacy_key not in snapshots:
            legacy_snapshot = copy.deepcopy(snapshots[current_key])
            legacy_snapshot["catalog_version"] = DEFAULT_CATALOG_VERSION
            snapshots[legacy_key] = legacy_snapshot

        return snapshots

    def __ensure_catalog_snapshots(self):
        current_snapshot = self.get_catalog_snapshot()
        current_key = (current_snapshot["catalog_id"], current_snapshot["catalog_version"])
        self.catalog_snapshots.setdefault(current_key, current_snapshot)

        for snapshot in self.catalog_snapshots.values():
            self.__insert_catalog_snapshot(snapshot)

    def __insert_catalog_snapshot(self, snapshot):
        self.db.execute(
            "INSERT INTO catalog_snapshots(catalog_id, catalog_version, data, created) "
            "VALUES(%s, %s, %s::jsonb, %s) ON CONFLICT (catalog_id, catalog_version) DO NOTHING;",
            (
                snapshot["catalog_id"],
                snapshot["catalog_version"],
                json.dumps(snapshot),
                int(time.time()),
            ),
            commit=True,
        )

    def __load_catalog_snapshots_from_db(self):
        rows = self.db.execute("SELECT catalog_id, catalog_version, data FROM catalog_snapshots;")
        if rows is None:
            return

        for catalog_id, catalog_version, data in rows:
            snapshot = self.__parse_json_value(data, None)
            if not isinstance(snapshot, dict):
                continue
            snapshot = self.__normalize_catalog_snapshot(snapshot)
            self.catalog_snapshots[(catalog_id, catalog_version)] = snapshot

    def __normalize_catalog_snapshot(self, snapshot):
        snapshot.setdefault("catalog_id", self.get_catalog_id())
        snapshot.setdefault("catalog_version", self.get_catalog_version())
        snapshot.setdefault("categories", copy.deepcopy(self.config["categories"]))
        snapshot.setdefault("kink_groups", [])

        for group in snapshot["kink_groups"]:
            group.setdefault("description", "")
            group.setdefault("tip", "")
            group.setdefault("columns", [])
            group.setdefault("rows", [])
            for kink in group["rows"]:
                kink.setdefault("id", "")
                kink.setdefault("description", "")
                kink.setdefault("tip", "")

        return snapshot

    def get_catalog_snapshot(self, shown_item_ids=None):
        shown = None
        if shown_item_ids is not None:
            shown = {str(item_id) for item_id in shown_item_ids}

        groups = []
        for group in self.config["kink_groups"]:
            rows = []
            for kink in group["rows"]:
                if shown is not None and str(kink["id"]) not in shown:
                    continue
                if shown is None and kink["visibility"] == "blocked":
                    continue
                rows.append({
                    "id": kink["id"],
                    "description": kink["description"],
                    "tip": kink.get("tip", ""),
                    "domain": kink["domain"],
                    "spice_level": kink["spice_level"],
                    "visibility": kink["visibility"],
                    "flags": copy.deepcopy(kink["flags"]),
                    "aliases": copy.deepcopy(kink["aliases"]),
                })
            if rows:
                groups.append({
                    "description": group["description"],
                    "tip": group.get("tip", ""),
                    "columns": copy.deepcopy(group["columns"]),
                    "domain": group["domain"],
                    "spice_level": group["spice_level"],
                    "visibility": group["visibility"],
                    "flags": copy.deepcopy(group["flags"]),
                    "rows": rows,
                })

        return {
            "catalog_id": self.get_catalog_id(),
            "catalog_version": self.get_catalog_version(),
            "categories": copy.deepcopy(self.config["categories"]),
            "kink_groups": groups,
        }

    def get_catalog_for_result(self, result):
        catalog_id = result.get("catalog_id", DEFAULT_CATALOG_ID)
        catalog_version = result.get("catalog_version", DEFAULT_CATALOG_VERSION)
        snapshot = self.catalog_snapshots.get((catalog_id, catalog_version))
        if snapshot is not None:
            return copy.deepcopy(snapshot)

        if catalog_version == DEFAULT_CATALOG_VERSION:
            current_snapshot = self.catalog_snapshots.get((catalog_id, self.get_catalog_version()))
            if current_snapshot is not None:
                legacy_snapshot = copy.deepcopy(current_snapshot)
                legacy_snapshot["catalog_version"] = DEFAULT_CATALOG_VERSION
                return legacy_snapshot

        return self.get_catalog_snapshot(result.get("shown_item_ids"))

    def get_result_choices(self, *catalogs):
        choices = []
        seen = set()
        for catalog in catalogs:
            for choice in catalog.get("categories", []):
                key = (choice.get("id"), choice.get("color"))
                if key not in seen:
                    seen.add(key)
                    choices.append(choice)
        return choices

    def get_catalog_id(self):
        return self.config["catalog_id"]

    def get_catalog_version(self):
        return self.config["catalog_version"]

    def get_shown_item_ids(self):
        # Until client-side catalog filtering exists, every configured row is still shown.
        return [kink["id"] for group in self.config["kink_groups"] for kink in group["rows"]]

    def get_answer_context(self, inputs):
        valid_contexts = {context["id"] for context in self.config["answer_contexts"]}
        answer_context = inputs.get("answer_context", self.config["default_answer_context"])
        if answer_context not in valid_contexts:
            return self.config["default_answer_context"]
        return answer_context

    def get_partner_personas(self, inputs):
        personas = inputs.get("partner_personas", [])
        if not isinstance(personas, list):
            return []

        result = []
        for index, persona in enumerate(personas[:5]):
            if not isinstance(persona, dict):
                continue
            label = str(persona.get("label", "")).strip()
            if not label:
                continue
            result.append({
                "id": str(persona.get("id") or f"persona_{index + 1}")[:64],
                "label": label[:80],
                "domain": str(persona.get("domain") or self.config["default_domain"])[:32],
            })
        return result

    def __result_select_columns(self, include_catalog_context=True):
        columns = [
            "answers.timestamp",
            "answers.choices_json",
            "answers.submitter->>'username'",
            "answers.submitter->>'sex'",
            "answers.submitter->>'age'",
            "answers.submitter->>'fap_freq'",
            "answers.submitter->>'sex_freq'",
            "answers.submitter->>'body_count'",
        ]
        if include_catalog_context:
            columns.extend([
                "answers.catalog_id",
                "answers.catalog_version",
                "answers.max_spice_level",
                "answers.shown_item_ids",
                "answers.answer_context",
                "answers.partner_personas",
            ])
        return ", ".join(columns)

    def get_result_data(self, token):
        query = (
            f"SELECT {self.__result_select_columns()} "
            "FROM answers "
            "WHERE token=%s;"
        )
        rows = self.db.execute(query, (token,))

        if rows is None:
            query = (
                f"SELECT {self.__result_select_columns(include_catalog_context=False)} "
                "FROM answers "
                "WHERE token=%s;"
            )
            rows = self.db.execute(query, (token,))

        if not rows:
            return None

        row = rows[0]
        return {
            "created": row[0],
            "choices": self.__parse_json_value(row[1], []),
            "username": row[2] or "---",
            "sex": row[3] or "---",
            "age": row[4] or "---",
            "fap_freq": row[5] or "---",
            "sex_freq": row[6] or "---",
            "body_count": row[7] or "---",
            "catalog_id": row[8] if len(row) > 8 else DEFAULT_CATALOG_ID,
            "catalog_version": row[9] if len(row) > 9 else DEFAULT_CATALOG_VERSION,
            "max_spice_level": row[10] if len(row) > 10 else None,
            "shown_item_ids": self.__parse_json_value(row[11], None) if len(row) > 11 else None,
            "answer_context": row[12] if len(row) > 12 else DEFAULT_ANSWER_CONTEXT,
            "partner_personas": self.__parse_json_value(row[13], []) if len(row) > 13 else [],
        }

    def __parse_json_value(self, value, default):
        if value is None:
            return default
        if isinstance(value, (dict, list)):
            return value
        try:
            return json.loads(value)
        except (TypeError, json.JSONDecodeError):
            return default




    def get_val_string(self):
        result = ""
        for group in self.config['kink_groups']:
            for kink in group['rows']:
                result += str(kink['id'])
                for cols in group['columns']:
                    result += "=" + str(0)
                result += "#"
        return result


    def get_item(self, meta, key):
        for m in meta:
                if m['id'] == key:
                    return m['val']


    def resolve_ids(self, data, catalog=None):
        if catalog is None:
            catalog = self.get_catalog_snapshot()
        result = []
        for group in catalog['kink_groups']:
            g = {"name": group['description'], "cols": self.__serialize_cols(group['columns'])}
            rows = []
            for k in group['rows']:
                vals = self.__get_id_val(k['id'], data, catalog['categories'], len(group['columns']))

                if vals is None:
                    vals = [self.__get_default_color(catalog['categories']) for _ in group['columns']]

                vv = []
                for index, v in enumerate(vals):
                    vv.append({"color": vals[index], "id": self.__get_id_by_color(vals[index], catalog['categories'])})
                rows.append({"name": k['description'], "vals": vv})
            g['rows'] = rows
            result.append(g)
        return result


    def __serialize_cols(self, cols):
        result = ""
        for col in cols:
            result += col + ", "
        return result[:-2]


    def __get_id_by_color(self, color, choices=None):
        if choices is None:
            choices = self.config["categories"]
        for c in choices:
            if c["color"] == color:
                return c["id"]
        return 0


    def __get_id_val(self, id, data, choices=None, expected_len=None):
        if choices is None:
            choices = self.config["categories"]
        for d in data:
            if not isinstance(d, dict):
                continue
            if str(id) == str(d.get('id')):
                raw = d.get('val')
                if raw is None:
                    return None
                if isinstance(raw, list):
                    values = raw
                elif isinstance(raw, str):
                    values = self.__parse_json_value(raw.replace('null', '\"0\"'), [])
                else:
                    values = [raw]

                colors = self.__get_color(values, choices)
                if expected_len is not None:
                    default_color = self.__get_default_color(choices)
                    colors = colors[:expected_len]
                    while len(colors) < expected_len:
                        colors.append(default_color)
                return colors



    def __get_color(self, vals, choices=None):
        if choices is None:
            choices = self.config["categories"]
        result = []
        default_color = self.__get_default_color(choices)
        for val in vals:
            if isinstance(val, str) and val.startswith("#"):
                result.append(val)
                continue

            try:
                choice_id = int(val)
            except (TypeError, ValueError):
                result.append(default_color)
                continue

            found = False
            for choice in choices:
                if choice_id == choice['id']:
                    result.append(choice['color'])
                    found = True
                    break
            if not found:
                result.append(default_color)
        return result

    def __get_default_color(self, choices):
        for choice in choices:
            if choice.get("default") or choice.get("id") == 0:
                return choice["color"]
        return "#d1d1d1"


    def check_token(self, token):
        return token in self.results


    def createHash(self):
        return secrets.token_urlsafe(18)

    def __sanitize_query(self, query):
        if not query:
            return ""
        safe_values = []
        for key, value in parse_qsl(query, keep_blank_values=True):
            if key.lower() in SENSITIVE_LOG_KEYS:
                safe_values.append((key, "[redacted]"))
            else:
                safe_values.append((key, value[:200]))
        return urlencode(safe_values)

    def __sanitize_path(self, path):
        if not path:
            return ""
        stripped = path.strip("/")
        if "/" not in stripped and stripped not in SAFE_PUBLIC_PATH_SEGMENTS and RESULT_TOKEN_PATTERN.match(stripped):
            return "/[result-token]"
        return path[:255]

    def __sanitize_url(self, url):
        if not url:
            return ""
        try:
            parts = urlsplit(url)
            return urlunsplit((
                parts.scheme,
                parts.netloc,
                self.__sanitize_path(parts.path),
                self.__sanitize_query(parts.query),
                "",
            ))[:512]
        except Exception:
            return "[redacted-url]"

    def __sanitize_log_value(self, value):
        if isinstance(value, dict):
            result = {}
            for key, nested in value.items():
                key_text = str(key)
                if key_text.lower() in SENSITIVE_LOG_KEYS or key_text.lower() in {"raw_data", "request_data"}:
                    result[key_text] = "[redacted]"
                elif key_text.lower() == "url":
                    result[key_text] = self.__sanitize_url(str(nested))
                else:
                    result[key_text] = self.__sanitize_log_value(nested)
            return result
        if isinstance(value, list):
            return [self.__sanitize_log_value(item) for item in value[:50]]
        if isinstance(value, str):
            return self.__sanitize_url(value) if "://" in value else value[:500]
        return value

    def __log(self, req):
        ip = ""
        if request.environ.get('HTTP_X_FORWARDED_FOR') is None:
            ip = (request.environ['REMOTE_ADDR'])
        else:
            ip = (request.environ['HTTP_X_FORWARDED_FOR'])  # if behind a proxy
        uri = req.environ.get('REQUEST_URI')
        if uri is None:
            uri = ""
        uri = self.__sanitize_url(uri)[:200]
        path = self.__sanitize_path(req.environ.get('PATH_INFO'))
        query = self.__sanitize_query(req.environ.get('QUERY_STRING'))
        logger.info(ip + " " + uri)
        # Request logging is no longer persisted. The hits table stored raw IPs
        # and query strings and was dropped in the Postgres migration.
        return ip

    def log_error(self, error_type, message, request_data=None, exception=None):

        if exception is not None and getattr(exception, "code", None) == 404:
            return
        """Centralized error logging function"""
        error_data = {
            "timestamp": datetime.now().isoformat(),
            "type": error_type,
            "message": message,
            "ip": self.get_client_ip(request) if request else "unknown",
            "user_agent": request.headers.get('User-Agent', 'unknown') if request else "unknown",
            "url": self.__sanitize_url(request.url) if request else "unknown",
            "method": request.method if request else "unknown",
        }

        if request_data:
            error_data["request_data"] = self.__sanitize_log_value(request_data)

        if exception:
            error_data["exception"] = {
                "type": type(exception).__name__,
                "message": str(exception),
                "traceback": traceback.format_exc()
            }

        # Log to error-specific file
        error_logger.error(json.dumps(error_data, indent=2))

        # Also store critical errors in database
        if error_type in ["EMPTY_SUBMISSION", "CORRUPT_DATA", "STORAGE_ERROR"]:
            try:
                self.db.execute(
                    "INSERT INTO error_logs(timestamp, error_type, message, ip, user_agent, data) VALUES(%s, %s, %s, %s, %s, %s);",
                    (int(time.time()), error_type, message, error_data["ip"],
                     error_data["user_agent"], json.dumps(error_data)),
                    commit=True
                )
            except Exception as db_err:
                error_logger.critical(f"Failed to log to database: {db_err}")

    def get_client_ip(self, req):
        """Extract client IP from request"""
        if req.environ.get('HTTP_X_FORWARDED_FOR'):
            return req.environ['HTTP_X_FORWARDED_FOR'].split(',')[0]
        return req.environ.get('REMOTE_ADDR', 'unknown')



    def isMobile(self, request):
        ua = request.headers.get('User-Agent')
        if ua is None:
            ua = ""
        ua = ua.lower()
        if force_mobile:
            ua += "android"
        return "iphone" in ua or "android" in ua



    @logger.catch
    def create_app(self):

        self.app = Flask(__name__)
        self.app.jinja_env.globals.update(get_cat=get_cat)

        @self.app.route('/<token>', methods=['GET'])
        def short_results(token):
            return results(token)

        @self.app.route('/', methods=['GET', 'POST', 'HEAD'])
        def index():
            try:
                self.__log(request)
                if request.method == 'HEAD':
                    res = make_response()
                    res.status_code = 200
                    return res

                elif request.method == 'GET':
                    # Your existing GET logic
                    user = request.cookies.get('user', default='')
                    secret = request.cookies.get('secret', default='')

                    if self.isMobile(request):
                        res = make_response(render_template('mobile_index.html'))
                    else:
                        res = make_response(render_template('index.html'))

                    res.set_cookie('values', self.get_val_string())
                    if user == '' or secret == '' or user == 'null' or secret == 'null':
                        new_user = str(uuid.uuid4())
                        new_secret = str(uuid.uuid4())
                        res.set_cookie('user', new_user)
                        res.set_cookie('secret', new_secret)
                    return res

                elif request.method == 'POST':
                    try:
                        inputs = request.get_json()

                        # Validate inputs exist
                        if not inputs:
                            self.log_error("EMPTY_SUBMISSION", "Received null/empty POST data", {
                                "content_length": request.content_length,
                                "content_type": request.content_type
                            })
                            return jsonify({"error": "No data received"}), 400

                        # Validate required fields
                        if 'kinks' not in inputs or not inputs['kinks']:
                            self.log_error("EMPTY_SUBMISSION", "Missing or empty kinks array", {
                                "received_keys": list(inputs.keys()) if inputs else [],
                                "raw_data": str(inputs)[:500]  # First 500 chars for debugging
                            })
                            return jsonify({"error": "Invalid data structure"}), 400

                        # Check for empty/corrupted kinks data
                        valid_kinks = []
                        for k in inputs['kinks']:
                            if k.get("val") is None:
                                self.log_error("CORRUPT_DATA", f"Null value in kink {k.get('id', 'unknown')}", {
                                    "kink_data": k,
                                    "all_kinks_count": len(inputs['kinks'])
                                })
                            else:
                                valid_kinks.append(k)

                        if not valid_kinks:
                            self.log_error("EMPTY_SUBMISSION", "All kinks had null values", {
                                "kinks_count": len(inputs['kinks']),
                                "meta": inputs.get('meta', {})
                            })
                            return jsonify({"error": "No valid data to save"}), 400

                        # Your existing logic with validated data
                        user = request.cookies.get('user', default='')
                        secret = request.cookies.get('secret', default='')

                        if user == '' or secret == '' or user == 'null' or secret == 'null':
                            self.log_error("AUTH_ERROR", "Invalid user/secret cookies during submission")
                            return jsonify({"error": "Session expired"}), 401

                        ip = self.get_client_ip(request)
                        token = self.createHash()
                        while self.check_token(token):
                            token = self.createHash()

                        m = inputs.get('meta', [])
                        t = round(time.time() * 1000)

                        # Submitter metadata is a point-in-time snapshot stored on
                        # the answer itself. No users table, and no IP address.
                        submitter = {
                            "username": self.get_item(m, 'name'),
                            "sex": self.get_item(m, 'sex'),
                            "age": self.get_item(m, 'age'),
                            "fap_freq": self.get_item(m, 'fap_freq'),
                            "sex_freq": self.get_item(m, 'sex_freq'),
                            "body_count": self.get_item(m, 'body_count'),
                            "created": t,
                        }
                        submitter = {k: v for k, v in submitter.items() if v is not None}

                        max_spice_level = inputs.get("max_spice_level")
                        answer_context = self.get_answer_context(inputs)
                        partner_personas = self.get_partner_personas(inputs)
                        self.db.execute(
                            "INSERT INTO answers(user_uuid, submitter, timestamp, token, choices_json, hit_count, catalog_id, catalog_version, max_spice_level, shown_item_ids, answer_context, partner_personas) VALUES(%s, %s::jsonb, %s, %s, %s::jsonb, 0, %s, %s, %s, %s::jsonb, %s, %s::jsonb);",
                            (user, json.dumps(submitter), t, token, json.dumps(valid_kinks), self.get_catalog_id(),
                             self.get_catalog_version(), max_spice_level, json.dumps(self.get_shown_item_ids()),
                             answer_context, json.dumps(partner_personas)),
                            commit=True
                        )
                        saved_answer = self.db.execute("SELECT token FROM answers WHERE token=%s;", (token,))
                        if not saved_answer:
                            self.db.execute(
                                "INSERT INTO answers(user_uuid, submitter, timestamp, token, choices_json, hit_count) VALUES(%s, %s::jsonb, %s, %s, %s::jsonb, 0);",
                                (user, json.dumps(submitter), t, token, json.dumps(valid_kinks)),
                                commit=True
                            )
                            saved_answer = self.db.execute("SELECT token FROM answers WHERE token=%s;", (token,))
                        if not saved_answer:
                            self.log_error("DB_ERROR", "Could not retrieve answer after insert", {"token": token})
                            return jsonify({"error": "Database error"}), 500
                        self.results.append(token)

                        logger.info(f"Created result token {token}")
                        res_results = make_response()
                        res_results.set_cookie('token', token)
                        return res_results

                    except json.JSONDecodeError as e:
                        self.log_error("JSON_ERROR", "Failed to parse POST data", {
                            "raw_data": request.get_data(as_text=True)[:1000]
                        }, e)
                        return jsonify({"error": "Invalid JSON"}), 400
                    except Exception as e:
                        self.log_error("POST_ERROR", "Unexpected error during POST", None, e)
                        return jsonify({"error": "Server error"}), 500

            except Exception as e:
                self.log_error("ROUTE_ERROR", "Unexpected error in index route", None, e)
                return jsonify({"error": "Server error"}), 500

        @self.app.route('/quiz')
        def quiz():
            self.__log(request)
            id = request.args.get('id', default='')
            keys = list(self.byid.keys())
            if id == '' or not int(id) in keys:
                return redirect(url_for('index'))

            cats = []
            for c in self.config["categories"]:
                if not "default" in c:
                    cats.append(c)


            id = int(id)
            first = keys[0]
            last = keys[-1]
            index = keys.index(int(id))
            prev = keys[index-1]
            kink = self.byid[int(id)]
            if prev == last:
                prev = id
            next = None
            if index == len(keys) - 1:
                next = id
            else:
                next = keys[index + 1]

            return render_template('mobile_quiz.html', id=id, first=first, prev=prev, next=next, last=last, cols=kink['cols'], group_name=kink['group_name'], group_tip=kink['group_tip'], kink_title=kink['name'], kink_desc=kink['tip'], cats=cats)


        @self.app.route('/meta')
        def meta():
            self.__log(request)
            return render_template('mobile_meta.html')
        
        
        @self.app.route('/jump')
        def jump():
            self.__log(request)
            return render_template('mobile_jump.html', groups=self.config['kink_groups'])
        
        
        @self.app.route('/cinfo')
        def cinfo():
            self.__log(request)
            cats = []
            for c in self.config["categories"]:
                if not "default" in c:
                    cats.append(c)

            return render_template('mobile_cinfo.html', cats=cats)


        @self.app.route('/results')
        def results(token=''):
            self.__log(request)
            t = request.args.get('token', default='')
            if token != '':
                t = token.split('&')[0]

            if not self.check_token(t):
                return redirect('/')
            else:
                self.db.execute("UPDATE answers SET hit_count = hit_count + 1 WHERE token = %s;", (t,), commit=True)
                data = self.get_result_data(t)
                if data is None:
                    return redirect('/')
                catalog = self.get_catalog_for_result(data)
                choices = self.get_result_choices(catalog)

                ua = request.headers.get('User-Agent')
                if ua is None:
                    ua = ""
                ua = ua.lower()
                page = None
                if "iphone" in ua or "android" in ua:
                    page = 'results.html'
                else:
                    page = 'results.html'


                res = make_response(render_template(page, kinks=self.resolve_ids(data["choices"], catalog), username=data["username"], sex=data["sex"], age=data["age"], fap_freq=data["fap_freq"], sex_freq=data["sex_freq"], body_count=data["body_count"], created=[data["created"]], choices=choices))
                return res


        @self.app.route('/missingKink', methods=['POST'])
        def missingKink():
            ip = self.__log(request)
            logger.info("New suggestion!")
            data = request.get_json(silent=True) or {}
            mk = data.get('missingkink')
            if mk == '' or mk is None:
                return make_response('', 400)
            ts = int(time.time())
            digest = hashlib.md5(f"{ts}\x00{mk}".encode("utf-8")).hexdigest()
            self.db.execute(
                'INSERT INTO suggestions("timestamp", suggestion, legacy_digest) VALUES(%s, %s, %s) '
                "ON CONFLICT (legacy_digest) DO NOTHING;",
                (ts, mk, digest), commit=True)
            return make_response('', 200)


        @self.app.route('/compare')
        def compare():
            self.__log(request)
            a = request.args.get('a', default='')
            b = request.args.get('b', default='')
            if not self.check_token(a) or not self.check_token(b):
                return redirect('/')
            else:
                data_a = self.get_result_data(a)
                data_b = self.get_result_data(b)
                if data_a is None or data_b is None:
                    return redirect('/')
                catalog_a = self.get_catalog_for_result(data_a)
                catalog_b = self.get_catalog_for_result(data_b)
                choices = self.get_result_choices(catalog_a, catalog_b)
                res = make_response(render_template('compare.html', kinks_a=self.resolve_ids(data_a["choices"], catalog_a), username_a=data_a["username"], sex_a=data_a["sex"], age_a=data_a["age"], fap_freq_a=data_a["fap_freq"], sex_freq_a=data_a["sex_freq"], body_count_a=data_a["body_count"], created_a=[data_a["created"]], choices=choices,
                                                    kinks_b=self.resolve_ids(data_b["choices"], catalog_b), username_b=data_b["username"], sex_b=data_b["sex"], age_b=data_b["age"], fap_freq_b=data_b["fap_freq"], sex_freq_b=data_b["sex_freq"], body_count_b=data_b["body_count"], created_b=[data_b["created"]]))
                return res



        @self.app.route('/compare4')
        def compare4():
            self.__log(request)
            a = request.args.get('a', default='')
            b = request.args.get('b', default='')
            c = request.args.get('c', default='')
            d = request.args.get('d', default='')
            if not self.check_token(a) or not self.check_token(b) or not self.check_token(c) or not self.check_token(d):
                return redirect('/')
            else:
                data_a = self.get_result_data(a)
                data_b = self.get_result_data(b)
                data_c = self.get_result_data(c)
                data_d = self.get_result_data(d)
                if data_a is None or data_b is None or data_c is None or data_d is None:
                    return redirect('/')
                catalog_a = self.get_catalog_for_result(data_a)
                catalog_b = self.get_catalog_for_result(data_b)
                catalog_c = self.get_catalog_for_result(data_c)
                catalog_d = self.get_catalog_for_result(data_d)
                choices = self.get_result_choices(catalog_a, catalog_b, catalog_c, catalog_d)
                res = make_response(render_template('compare4.html', kinks_a=self.resolve_ids(data_a["choices"], catalog_a), username_a=data_a["username"], sex_a=data_a["sex"], age_a=data_a["age"], fap_freq_a=data_a["fap_freq"], sex_freq_a=data_a["sex_freq"], body_count_a=data_a["body_count"], created_a=[data_a["created"]], choices=choices,
                                                    kinks_b=self.resolve_ids(data_b["choices"], catalog_b), username_b=data_b["username"], sex_b=data_b["sex"], age_b=data_b["age"], fap_freq_b=data_b["fap_freq"], sex_freq_b=data_b["sex_freq"], body_count_b=data_b["body_count"], created_b=[data_b["created"]],
                                                    kinks_c=self.resolve_ids(data_c["choices"], catalog_c), username_c=data_c["username"], sex_c=data_c["sex"], age_c=data_c["age"], fap_freq_c=data_c["fap_freq"], sex_freq_c=data_c["sex_freq"], body_count_c=data_c["body_count"], created_c=[data_c["created"]],
                                                    kinks_d=self.resolve_ids(data_d["choices"], catalog_d), username_d=data_d["username"], sex_d=data_d["sex"], age_d=data_d["age"], fap_freq_d=data_d["fap_freq"], sex_freq_d=data_d["sex_freq"], body_count_d=data_d["body_count"], created_d=[data_d["created"]]))
                return res

        @self.app.route('/log_client_error', methods=['POST'])
        def log_client_error():
            """Endpoint to receive client-side errors"""
            try:
                error_data = request.get_json()
                if not error_data:
                    return jsonify({"status": "ignored"}), 202
                if error_data.get("message") == "Unknown error":
                    return jsonify({"status": "logged"}), 202
                if error_data.get("event_type") in ["SUBMIT_ATTEMPT", "SUBMIT_SUCCESS", "MOBILE_SUBMIT_ATTEMPT", "MOBILE_BROWSER_KEYS", "BROWSER_KEYS"]:
                    return jsonify({"status": "ignored"}), 202

                self.log_error("CLIENT_ERROR", error_data.get('message', 'Unknown client error'), request_data=error_data)

                return jsonify({"status": "logged"}), 200
            except Exception as e:
                error_logger.error(f"Failed to log client error: {e}")
                return jsonify({"status": "error"}), 500

        @self.app.errorhandler(Exception)
        def handle_exception(e):
            """Global error handler for uncaught exceptions"""
            self.log_error("UNCAUGHT_ERROR", "Unhandled exception", None, e)

            # Don't expose internal errors to users
            if self.app.config.get('DEBUG'):
                return jsonify({"error": str(e)}), 500
            return jsonify({"error": "An error occurred"}), 500


        @self.app.route('/party')
        def party():
            self.__log(request)
            return render_template('party.html')


        @self.app.route('/party/draw', methods = ["GET"])
        def party_draw():
            cat = random.choice(self.config["kink_groups"])
            kink = copy.deepcopy(random.choice(cat["rows"]))
            col = random.choice(cat["columns"])
            kink["column"] = col
            return jsonify(kink)


        @self.app.route('/config')
        def config():
            self.__log(request)
            response = jsonify(self.config)
            response.status_code = 200
            return response

        @self.app.route('/kot')
        def kot():
            return redirect(url_for('index'))

        @self.app.route('/byid')
        def byid():
            self.__log(request)
            response = jsonify(self.byid)
            response.status_code = 200
            return response


        @self.app.route("/globalStats")
        def globalStats():
            self.__log(request)
            # The stats compiler was retired with the Postgres migration.
            response = jsonify({"categories": [], "colors": [], "distr_cat": {}})
            response.status_code = 200
            return response

        @self.app.route('/android-chrome-192x192.png')
        @self.app.route('/android-chrome-512x512.png')
        @self.app.route('/apple-touch-icon.png')
        @self.app.route('/favicon.ico')
        @self.app.route('/favicon-16x16.png')
        @self.app.route('/favicon-32x32.png')
        def static_from_ico():
            return send_from_directory(os.path.join(self.app.static_folder, 'ico'), request.path[1:])

        @self.app.route('/robots.txt')
        @self.app.route('/sitemap.xml')
        def static_from_root():
            return send_from_directory(self.app.static_folder, request.path[1:])

        if __name__ == '__main__':
            self.app.run(host='0.0.0.0', port=int(os.environ.get("DEV_PORT", "5055")))
        else:
            return self.app

if __name__ == '__main__':
    k = Kinklist()
    k.create_app()
