import json
from dataclasses import dataclass, field
from os.path import dirname, abspath

from db import MySQLPool
from enhanced_kinklist import read_args


class Global_Stats:

    def __init__(self, db):
        self.db = db
        json_file = dirname(abspath(__file__)) + "/enhanced_kinklist.json"
        self.config = json.load(open(json_file))


    def compile(self):
        # get users
        result = db.execute("SELECT * FROM users;")
        users = list()
        for r in result:
            users.append(User(r[0], r[3], r[4], r[5], r[6], r[7], None, None))

        for user in users:
            tmp = db.execute("SELECT timestamp, choices_json FROM answers WHERE user_id=%s ORDER BY timestamp DESC;", (user.id,))
            user.choices = json.loads(tmp[0][1])

        for user in users:
            self.compile_user(user)

        print()

    def compile_user(self, user):
        user.stats = Stats()
        for group in self.config["kink_groups"]:
            kink_group = Kinkgroup(group["description"])
            user.stats.groups.append(kink_group)
            cols = group["columns"]
            for row in group["rows"]:
                vals = user.lookup_kink_id(row["id"])
                for index, val in enumerate(vals):
                    if val is None:
                        val = "0"
                    user.stats.total_counts[val] += 1
                    kink_group.total_counts[val] += 1
                    if cols[index] == "Giving":
                        user.stats.giver_receiver["giver"][val] += 1
                    elif cols[index] == "Receiving":
                        user.stats.giver_receiver["receiver"][val] += 1


@dataclass
class User:
    id: int
    sex: str
    age: int
    fap_freq: str
    sex_freq: str
    body_count: str
    choices: []
    stats: None

    def lookup_kink_id(self, id):
        for c in self.choices:
            if c["id"] == id:
                return json.loads(c["val"])



class Stats:
    def __init__(self):
        self.groups = []
        self.total_counts = dict(
            {"0": 0, "1": 0, "2": 0, "3": 0, "4": 0, "5": 0, "6": 0, "7": 0, "8": 0, "9": 0, "10": 0, "-1": 0})
        self.giver_receiver = dict({"giver": dict({"0": 0, "1": 0, "2": 0, "3": 0, "4": 0, "5": 0, "6": 0, "7": 0, "8": 0, "9": 0, "10": 0, "-1": 0}), "receiver": dict({"0": 0, "1": 0, "2": 0, "3": 0, "4": 0, "5": 0, "6": 0, "7": 0, "8": 0, "9": 0, "10": 0, "-1": 0})})


class Kinkgroup:
    def __init__(self, name):
        self.group_name = name
        self.total_counts = dict({"0": 0, "1": 0, "2": 0, "3": 0, "4": 0, "5": 0, "6": 0, "7": 0, "8": 0, "9": 0, "10": 0, "-1": 0})


if __name__ == '__main__':
    args = read_args()
    db = MySQLPool(host=args['dbhost'], user=args['dbuser'], password=args['dbpw'], database=args['dbschema'],
                        pool_size=15)
    Global_Stats(db).compile()