from contextlib import closing
from contextlib import contextmanager

import pymysql

from codedebt_io.config import config


@contextmanager
def connect(**kwargs):
    kwargs.setdefault('autocommit', False)
    kwargs.setdefault('cursorclass', pymysql.cursors.DictCursor)
    kwargs.setdefault('charset', 'utf8mb4')

    kwargs.setdefault('user', config.get('database', 'user'))
    kwargs.setdefault('password', config.get('database', 'password'))
    kwargs.setdefault('host', config.get('database', 'host'))
    kwargs.setdefault('db', config.get('database', 'db'))

    with closing(pymysql.connect(**kwargs)) as c:
        yield c


@contextmanager
def txn(connection):
    assert not connection.autocommit_mode
    with connection as cursor:
        try:
            yield cursor
        except:
            connection.rollback()
            raise
        else:
            connection.commit()


@contextmanager
def use_db(cursor, db_name):
    cursor.execute('SELECT DATABASE() as db')
    current_db = cursor.fetchone()['db']
    try:
        cursor.execute('USE {}'.format(db_name))
        yield
    finally:
        cursor.execute('USE {}'.format(current_db))
