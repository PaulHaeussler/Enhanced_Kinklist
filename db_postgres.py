import psycopg
from loguru import logger
from psycopg import errors
from psycopg_pool import ConnectionPool


class PostgresPool(object):
    """
    Postgres-backed replacement for MySQLPool.

    Keeps the MySQLPool call signature and return contract so existing call
    sites do not change:
      - execute(...)     -> list of tuples on read, None on commit, None on error
      - executemany(...) -> same contract
    Both drivers use the %s paramstyle, so query arguments are unchanged.
    """

    def __init__(self, host="127.0.0.1", port="5432", user="postgres",
                 password="", database="kinklist_legacy", pool_name="mypool",
                 pool_size=20, min_size=1):
        self._host = host
        self._port = port
        self._user = user
        self._password = password
        self._database = database

        self.conninfo = psycopg.conninfo.make_conninfo(
            host=host,
            port=port,
            user=user,
            password=password,
            dbname=database,
        )
        self.pool = self.create_pool(pool_name=pool_name, pool_size=pool_size,
                                     min_size=min_size)

    def create_pool(self, pool_name="mypool", pool_size=20, min_size=1):
        """
        Create a connection pool. psycopg_pool opens connections lazily, so a
        large max_size does not cost anything until the traffic needs it.
        """
        pool = ConnectionPool(
            conninfo=self.conninfo,
            name=pool_name,
            min_size=min_size,
            max_size=pool_size,
            open=True,
        )
        return pool

    def close(self, conn, cursor):
        """
        Kept for interface parity with MySQLPool. Connections are returned to
        the pool in the finally blocks below.
        """
        if cursor:
            cursor.close()
        if conn:
            self.pool.putconn(conn)

    def execute(self, sql, args=None, commit=False):
        """
        Execute a sql, it could be with args and with out args.
        :param sql: sql clause
        :param args: args need by sql clause
        :param commit: whether to commit
        :return: if commit, return None, else, return result
        """
        conn = None
        cursor = None
        try:
            conn = self.pool.getconn()
            conn.autocommit = False
            cursor = conn.cursor()
            if args is not None:
                cursor.execute(sql, args)
            else:
                cursor.execute(sql)

            if commit is True:
                conn.commit()
                return None

            if cursor.description is None:
                # Statement produced no result set. MySQLPool surfaced this as
                # an error, so keep returning None rather than an empty list.
                conn.rollback()
                return None

            result = cursor.fetchall()
            # End the read transaction so the pooled connection does not idle
            # inside an open snapshot.
            conn.rollback()
            return result
        except errors.IntegrityError as e:
            logger.warning(e)
            if conn:
                conn.rollback()
            return None
        except Exception as e:
            logger.error(f"Database error: {e}")
            if conn:
                conn.rollback()
            return None
        finally:
            if cursor:
                cursor.close()
            if conn:
                self.pool.putconn(conn)

    def executemany(self, sql, args, commit=False):
        """
        Execute with many args. args should be a sequence.
        :param sql: sql clause
        :param args: args
        :param commit: commit or not.
        :return: if commit, return None, else, return result
        """
        conn = None
        cursor = None
        try:
            conn = self.pool.getconn()
            conn.autocommit = False
            cursor = conn.cursor()
            cursor.executemany(sql, args)

            if commit is True:
                conn.commit()
                return None

            if cursor.description is None:
                conn.rollback()
                return None

            result = cursor.fetchall()
            conn.rollback()
            return result
        except Exception as e:
            logger.error(f"Database error in executemany: {e}")
            if conn:
                conn.rollback()
            return None
        finally:
            if cursor:
                cursor.close()
            if conn:
                self.pool.putconn(conn)
