import mysql.connector.pooling
from loguru import logger
from mysql.connector import IntegrityError


class MySQLPool(object):
    """
    create a pool when connect mysql, which will decrease the time spent in
    request connection, create connection and close connection.
    """

    def __init__(self, host="172.0.0.1", port="3306", user="root",
                 password="123456", database="test", pool_name="mypool",
                 pool_size=1000):
        res = {}
        self._host = host
        self._port = port
        self._user = user
        self._password = password
        self._database = database

        res["host"] = self._host
        res["port"] = self._port
        res["user"] = self._user
        res["password"] = self._password
        res["database"] = self._database
        self.dbconfig = res
        self.pool = self.create_pool(pool_name=pool_name, pool_size=pool_size)

    def create_pool(self, pool_name="mypool", pool_size=20):
        """
        Create a connection pool, after created, the request of connecting
        MySQL could get a connection from this pool instead of request to
        create a connection.
        :param pool_name: the name of pool, default is "mypool"
        :param pool_size: the size of pool, default is 3
        :return: connection pool
        """
        pool = mysql.connector.pooling.MySQLConnectionPool(
            pool_name=pool_name,
            pool_size=pool_size,
            pool_reset_session=True,
            **self.dbconfig)
        return pool

    def close(self, conn, cursor):
        """
        A method used to close connection of mysql.
        :param conn:
        :param cursor:
        :return:
        """
        cursor.close()
        conn.close()

    def execute(self, sql, args=None, commit=False):
        """
        Execute a sql, it could be with args and with out args. The usage is
        similar with execute() function in module pymysql.
        :param sql: sql clause
        :param args: args need by sql clause
        :param commit: whether to commit
        :return: if commit, return None, else, return result
        """
        # get connection form connection pool instead of create one.
        conn = None
        cursor = None
        try:
            conn = self.pool.get_connection()
            cursor = conn.cursor()
            if args:
                cursor.execute(sql, args)
            else:
                cursor.execute(sql)

            if commit is True:
                conn.commit()
                result = None
            else:
                result = cursor.fetchall()

            return result
        except IntegrityError as e:
            logger.warning(e)
            if conn and not commit:
                conn.rollback()
            return None
        except Exception as e:
            logger.error(f"Database error: {e}")
            if conn and not commit:
                conn.rollback()
            return None
        finally:
            if cursor:
                cursor.close()
            if conn:
                conn.close()

    def executemany(self, sql, args, commit=False):
        """
        Execute with many args. Similar with executemany() function in pymysql.
        args should be a sequence.
        :param sql: sql clause
        :param args: args
        :param commit: commit or not.
        :return: if commit, return None, else, return result
        """
        # get connection form connection pool instead of create one.
        conn = None
        cursor = None
        try:
            conn = self.pool.get_connection()
            cursor = conn.cursor()
            cursor.executemany(sql, args)

            if commit is True:
                conn.commit()
                result = None
            else:
                result = cursor.fetchall()

            return result
        except Exception as e:
            logger.error(f"Database error in executemany: {e}")
            if conn and not commit:
                conn.rollback()
            return None
        finally:
            if cursor:
                cursor.close()
            if conn:
                conn.close()