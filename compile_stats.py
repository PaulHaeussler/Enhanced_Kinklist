import argparse
import json
import os
import time
from dataclasses import dataclass
from os.path import abspath, dirname

from db import MySQLPool


DEFAULT_STATS_INTERVAL = 21600
LOW_INFO_NOT_ENTERED_LIMIT = 150
LOW_INFO_MISSING_LIMIT = 100


class StatCompiler:

    def __init__(self, db):
        self.db = db
        json_file = dirname(abspath(__file__)) + "/enhanced_kinklist.json"
        with open(json_file) as config:
            self.config = json.load(config)
        self.choice_by_id = {str(c["id"]): c for c in self.config["categories"]}

    def compile(self):
        users = self.load_users()
        global_choices = self.build_global_choices()

        for user in users:
            self.compile_user(user, global_choices)

        included_users = [user for user in users if self.include_user(user)]
        analysis_users = included_users or users
        result_count = self.count_answers()
        total_fields = self.total_field_count()

        stats = {
            "generated_at": int(time.time()),
            "summary": {
                "result_count": result_count,
                "participant_count": len(users),
                "included_participant_count": len(included_users),
                "total_kinks": self.total_kink_count(),
                "total_fields": total_fields,
                "average_completion_rate": self.average_completion_rate(analysis_users, total_fields),
            },
            "categories": self.category_names(),
            "colors": self.category_colors(),
            "distr_cat": self.average_choice_distribution(analysis_users),
            "top": {
                "favorites": self.top_choices(global_choices, ["1"], analysis_users),
                "want_to_try": self.top_choices(global_choices, ["6", "7"], analysis_users),
                "hard_limits": self.top_choices(global_choices, ["5", "10"], analysis_users),
            },
        }

        self.db.execute("INSERT INTO stats(data, created) VALUES(%s, %s);", (json.dumps(stats), time.time()), commit=True)
        print(f"Compiled stats for {len(users)} participants and {result_count} saved results")
        return stats

    def load_users(self):
        rows = self.db.execute(
            "SELECT users.id, users.sex, users.age, users.fap_freq, users.sex_freq, users.body_count, answers.choices_json "
            "FROM users "
            "INNER JOIN ("
            "  SELECT user_id, MAX(timestamp) AS latest_timestamp "
            "  FROM answers "
            "  GROUP BY user_id"
            ") latest ON latest.user_id = users.id "
            "INNER JOIN answers ON answers.user_id = latest.user_id AND answers.timestamp = latest.latest_timestamp;"
        ) or []

        users = []
        for row in rows:
            users.append(
                User(
                    id=row[0],
                    sex=row[1],
                    age=row[2],
                    fap_freq=row[3],
                    sex_freq=row[4],
                    body_count=row[5],
                    choices=self.parse_choices(row[6]),
                    stats=None,
                )
            )
        return users

    def count_answers(self):
        rows = self.db.execute("SELECT COUNT(*) FROM answers;") or [(0,)]
        return rows[0][0]

    def parse_choices(self, choices_json):
        if choices_json is None:
            return []
        if isinstance(choices_json, list):
            return choices_json
        return json.loads(choices_json)

    def build_global_choices(self):
        result = []
        for group in self.config["kink_groups"]:
            for row in group["rows"]:
                result.append({
                    "id": row["id"],
                    "name": row["description"],
                    "group": group["description"],
                    "choices": [new_choices_dict() for _ in group["columns"]],
                    "columns": group["columns"],
                })
        return result

    def category_names(self):
        return [category["description"] for category in self.config["categories"]]

    def category_colors(self):
        return [category["color"] for category in self.config["categories"]]

    def total_kink_count(self):
        return sum(len(group["rows"]) for group in self.config["kink_groups"])

    def total_field_count(self):
        total = 0
        for group in self.config["kink_groups"]:
            total += len(group["rows"]) * len(group["columns"])
        return total

    def include_user(self, user):
        counts = user.stats.total_counts
        return counts["0"] <= LOW_INFO_NOT_ENTERED_LIMIT and counts["-999"] <= LOW_INFO_MISSING_LIMIT

    def average_completion_rate(self, users, total_fields):
        if not users or total_fields == 0:
            return 0

        rates = []
        for user in users:
            answered = total_fields - user.stats.total_counts["0"] - user.stats.total_counts["-999"]
            rates.append(answered / total_fields * 100)
        return round(sum(rates) / len(rates), 1)

    def average_choice_distribution(self, users):
        result = {}
        names = self.category_names()

        if not users:
            for name in names:
                result[name] = 0
            return result

        sums = new_choices_dict()
        for user in users:
            for key, value in user.stats.total_counts.items():
                sums[key] += value

        for name in names:
            choice_id = str(self.get_id_by_name(name))
            result[name] = round(sums[choice_id] / len(users), 2)
        return result

    def get_id_by_name(self, name):
        for category in self.config["categories"]:
            if category["description"] == name:
                return category["id"]
        return None

    def compile_user(self, user, global_choices=None):
        user.stats = Stats()
        row_index = 0
        for group in self.config["kink_groups"]:
            kink_group = Kinkgroup(group["description"])
            user.stats.groups.append(kink_group)
            columns = group["columns"]
            for row in group["rows"]:
                vals = user.lookup_kink_id(row["id"])
                if vals is None:
                    vals = []

                for index, column in enumerate(columns):
                    val = self.normalized_choice(vals, index)
                    user.stats.total_counts[val] += 1
                    kink_group.total_counts[val] += 1
                    if global_choices is not None:
                        global_choices[row_index]["choices"][index][val] += 1
                    if column == "Giving":
                        user.stats.giver_receiver["giver"][val] += 1
                    elif column == "Receiving":
                        user.stats.giver_receiver["receiver"][val] += 1
                row_index += 1

    def normalized_choice(self, vals, index):
        if index >= len(vals) or vals[index] is None:
            return "-999"
        val = str(vals[index])
        if val == "null":
            return "-999"
        if val not in self.choice_by_id:
            return "-999"
        return val

    def top_choices(self, global_choices, choice_ids, users, limit=5):
        if not users:
            return []

        result = []
        for row in global_choices:
            for index, column_counts in enumerate(row["choices"]):
                count = sum(column_counts[choice_id] for choice_id in choice_ids)
                if count == 0:
                    continue

                result.append({
                    "id": row["id"],
                    "name": row["name"],
                    "group": row["group"],
                    "column": row["columns"][index],
                    "count": count,
                    "percent": round(count / len(users) * 100, 1),
                })

        return sorted(result, key=lambda item: (item["count"], item["percent"]), reverse=True)[:limit]


def new_choices_dict():
    return {"0": 0, "1": 0, "2": 0, "3": 0, "4": 0, "5": 0, "6": 0, "7": 0, "8": 0, "9": 0, "10": 0, "-1": 0, "-2": 0, "-999": 0}


@dataclass
class User:
    id: int
    sex: str
    age: int
    fap_freq: str
    sex_freq: str
    body_count: str
    choices: list
    stats: object

    def lookup_kink_id(self, kink_id):
        for choice in self.choices:
            if int(choice["id"]) == int(kink_id):
                try:
                    return json.loads(choice["val"])
                except (TypeError, json.JSONDecodeError):
                    return None
        return None


class Stats:
    def __init__(self):
        self.groups = []
        self.total_counts = new_choices_dict()
        self.giver_receiver = {"giver": new_choices_dict(), "receiver": new_choices_dict()}


class Kinkgroup:
    def __init__(self, name):
        self.group_name = name
        self.total_counts = new_choices_dict()


def read_args():
    parser = argparse.ArgumentParser(description="Compile aggregate Enhanced Kinklist stats")
    parser.add_argument("dbhost", nargs="?")
    parser.add_argument("dbschema", nargs="?")
    parser.add_argument("dbuser", nargs="?")
    parser.add_argument("dbpw", nargs="?")
    parser.add_argument("--loop", action="store_true", help="Run forever and recompile on an interval")
    parser.add_argument("--interval", type=int, default=int(os.environ.get("STATS_INTERVAL", DEFAULT_STATS_INTERVAL)))
    return parser.parse_args()


def db_config(args):
    return {
        "host": args.dbhost or os.environ["DB_HOST"],
        "database": args.dbschema or os.environ["DB_SCHEMA"],
        "user": args.dbuser or os.environ["DB_USER"],
        "password": args.dbpw or os.environ["DB_PW"],
    }


def run_once(db):
    return StatCompiler(db).compile()


if __name__ == "__main__":
    args = read_args()
    config = db_config(args)
    db = MySQLPool(host=config["host"], user=config["user"], password=config["password"], database=config["database"], pool_size=3)

    while True:
        try:
            run_once(db)
        except Exception as exc:
            print(f"Failed to compile stats: {exc}")
            if not args.loop:
                raise

        if not args.loop:
            break
        time.sleep(args.interval)
