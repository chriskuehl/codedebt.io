"""Stuff for working with git-code-debt.

TODO: how much of this can we reasonably upstream?
"""
import os

import pkg_resources
import pymysql
from git_code_debt import create_tables
from git_code_debt import generate


class FakeSqlite:

    def __init__(self, cursor):
        self._cursor = cursor
        self.cursor = None

    def __enter__(self):
        """Produce a new cursor which is not a DictCursor."""
        # TODO: is this even a correct thing to do?
        old_cursor_class = self._cursor.connection.cursorclass
        self._cursor.connection.cursorclass = pymysql.cursors.Cursor
        self.cursor = self._cursor.connection.cursor()
        self._cursor.connection.cursorclass = old_cursor_class
        return self

    def execute(self, *args, **kwargs):
        self.cursor.execute(*args, **kwargs)
        return self.cursor

    def executemany(self, query, data):
        if query == "INSERT INTO metric_names ('name') VALUES (?)":
            query = 'INSERT INTO metric_names (name) VALUES (?)'
        query = query.replace('?', '%s')

        self.cursor.executemany(query, data)
        return self.cursor

    def __exit__(self, *args):
        self.cursor.close()
        self.cursor = None

    def connect(self, _):
        return self


def apply_schema(cursor):
    schema_dir = pkg_resources.resource_filename('git_code_debt', 'schema')
    for schema_file in os.listdir(schema_dir):
        with open(os.path.join(schema_dir, schema_file)) as f:
            for query in [q for q in f.read().split(';') if q.strip()]:
                # TODO: upstream?
                query = query.replace(
                    'INTEGER PRIMARY KEY ASC',
                    'INTEGER PRIMARY KEY AUTO_INCREMENT',
                )
                cursor.execute(query)
    # TODO: probably need to add a unique index back?
    cursor.execute('''
        ALTER TABLE metric_data
        DROP PRIMARY KEY
    ''')
    cursor.execute('''
        ALTER TABLE metric_data
        ADD COLUMN ROWID INT NOT NULL PRIMARY KEY AUTO_INCREMENT
    ''')


def populate_metric_ids(cursor):
    with FakeSqlite(cursor) as c:
        create_tables.populate_metric_ids(c, [], False)


def load_data(cursor, project):
    generate.sqlite3 = FakeSqlite(cursor)
    generate.load_data(
        None,
        project.git_url,
        [],
        False,
    )
