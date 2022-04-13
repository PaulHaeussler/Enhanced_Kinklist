from dataclasses import dataclass

from db import MySQLPool
from enhanced_kinklist import read_args


class Stats:

    def __init__(self, db):
        self.db = db


    def compile(self):
        # get users
        result = db.execute("SELECT * FROM users;")
        users = list()



@dataclass
class User:
    id: int
    sex: str
    age: int
    fap_freq: str
    sex_freq: str
    body_count: str
    choices: []



if __name__ == '__main__':
    args = read_args()
    db = MySQLPool(host=args['dbhost'], user=args['dbuser'], password=args['dbpw'], database=args['dbschema'],
                        pool_size=15)
    Stats(db).compile()