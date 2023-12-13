from enhanced_kinklist import Kinklist
import os



def build():
    dbhost = os.environ["DB_HOST"]
    dbuser = os.environ["DB_USER"]
    dbpw = os.environ["DB_PW"]
    dbschema = os.environ["DB_SCHEMA"]
    k = Kinklist(dbhost, dbuser, dbpw, dbschema)
    return k.create_app()
