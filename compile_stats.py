import json
import operator
from dataclasses import dataclass, field
from os.path import dirname, abspath

from db import MySQLPool
from enhanced_kinklist import read_args


class StatCompiler:

    def __init__(self, db):
        self.db = db
        json_file = dirname(abspath(__file__)) + "/enhanced_kinklist.json"
        self.config = json.load(open(json_file))

    def __build_global_choices(self):
        result = []
        for group in self.config["kink_groups"]:
            cols = group["columns"]
            for row in group["rows"]:
                kink = dict()
                kink["id"] = row["id"]
                kink["choices"] = []
                for col in cols:
                    kink["choices"].append(new_choices_dict())
                result.append(kink)
        return result


    def compile(self):
        # get users
        result = db.execute("SELECT * FROM users;")
        users = list()
        for r in result:
            users.append(User(r[0], r[3], r[4], r[5], r[6], r[7], None, None))

        for user in users:
            tmp = db.execute("SELECT timestamp, choices_json FROM answers WHERE user_id=%s ORDER BY timestamp DESC;", (user.id,))
            user.choices = json.loads(tmp[0][1])

        g_choices = self.__build_global_choices()

        for user in users:
            self.compile_user(user, g_choices)

        g_stats = GlobalStats(users, g_choices)
        print()
        # self.build_global_stats(g_stats)
        self.top10_hated(g_stats)


    def compile_user(self, user, g_choices=None):
        user.stats = Stats()
        irow = 0
        for group in self.config["kink_groups"]:
            kink_group = Kinkgroup(group["description"])
            user.stats.groups.append(kink_group)
            cols = group["columns"]
            for row in group["rows"]:

                vals = user.lookup_kink_id(row["id"])
                if vals is None:
                    vals = []
                    for col in cols:
                        vals.append("0")
                for index, val in enumerate(vals):
                    if val is None:
                        val = "0"
                    user.stats.total_counts[val] += 1
                    kink_group.total_counts[val] += 1
                    if not g_choices is None:
                        g_choices[irow]["choices"][index][val] += 1
                    if cols[index] == "Giving":
                        user.stats.giver_receiver["giver"][val] += 1
                    elif cols[index] == "Receiving":
                        user.stats.giver_receiver["receiver"][val] += 1
                irow += 1


    def build_global_stats(self, g_stats):
        print()




    def top10_hated(self, g_stats):
        l = dict()
        for row in g_stats.choices:
            for icol, col in enumerate(row["choices"]):
                l[str(row['id']) + "-" + str(icol)] = col["1"]
        l = sorted(l.items(), key=operator.itemgetter(1), reverse=True)
        print()
        sorted_l = {}
        for kink in l:
            tmp = kink[0].split("-")
            desc, col = self.lookup_kink_id(tmp[0], tmp[1])
            sorted_l[desc + "-" + col] = kink[1]
        print()


    def lookup_kink_id(self, id, col_index=None):
        for g in self.config["kink_groups"]:
            for row in g["rows"]:
                if row["id"] == int(id):
                    col = None
                    if not col_index is None:
                        for ci, c in enumerate(g["columns"]):
                            if ci == int(col_index):
                                col = c
                    return row["description"], col



def new_choices_dict():
     return dict(
        {"0": 0, "1": 0, "2": 0, "3": 0, "4": 0, "5": 0, "6": 0, "7": 0, "8": 0, "9": 0, "10": 0, "-1": 0, "-2": 0})


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


class GlobalStats:
    def __init__(self, users, choices):
        self.users = users
        self.choices = choices




class Stats:
    def __init__(self):
        self.groups = []
        self.total_counts = new_choices_dict()
        self.giver_receiver = dict({"giver": new_choices_dict(), "receiver": new_choices_dict()})


class Kinkgroup:
    def __init__(self, name):
        self.group_name = name
        self.total_counts = new_choices_dict()


if __name__ == '__main__':
    args = read_args()
    db = MySQLPool(host=args['dbhost'], user=args['dbuser'], password=args['dbpw'], database=args['dbschema'],
                        pool_size=15)
    StatCompiler(db).compile()