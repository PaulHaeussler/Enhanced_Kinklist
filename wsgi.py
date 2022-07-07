from enhanced_kinklist import Kinklist


def build(dbhost, dbschema, dbuser, dbpw):
    k = Kinklist(dbhost, dbuser, dbpw, dbschema)
    return k.create_app()
