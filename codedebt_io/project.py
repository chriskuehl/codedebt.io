import os
import argparse
import pkg_resources
from collections import namedtuple

from git_code_debt import create_tables
from cached_property import cached_property

from codedebt_io.db.connection import connect
from codedebt_io.db.connection import txn
from codedebt_io.db.connection import use_db


class Project(namedtuple('Project', (
    'id',
    'service',
    'name',
))):

    @classmethod
    def from_row(cls, row):
        return cls(
            id=row['id'],
            service=row['service'],
            name=row['name'],
        )

    @cached_property
    def git_url(self):
        return {
            'github': 'https://github.com/{self.name}.git',
        }[self.service].format(self=self)

    @cached_property
    def db_name(self):
        return 'proj_{self.id}'.format(self=self)

    def db_exists(self, cursor):
        cursor.execute('''
            SELECT COUNT(*) AS count
            FROM INFORMATION_SCHEMA.SCHEMATA
            WHERE SCHEMA_NAME = %s
        ''', (self.db_name,))
        count = cursor.fetchone()['count']
        assert count in {0, 1}, count
        return count == 1

    def db_create(self, cursor):
        # TODO: "CREATE DATABASE" triggers an implicit txn commit, so
        # we might fail in between creating db and adding tables
        cursor.execute('''
            CREATE DATABASE {}
        '''.format(self.db_name))
        with use_db(cursor, self.db_name):
            schema_dir = pkg_resources.resource_filename('git_code_debt', 'schema')
            for schema_file in os.listdir(schema_dir):
                with open(os.path.join(schema_dir, schema_file)) as f:
                    for query in [q for q in f.read().split(';') if q.strip()]:
                        # TODO: upstream
                        query = query.replace(
                            'INTEGER PRIMARY KEY ASC',
                            'INTEGER PRIMARY KEY',
                        )
                        cursor.execute(query)


    def update(self, connection, report):
        with txn(connection) as cursor:
            if not self.db_exists(cursor):
                report('must create database')
                self.db_create(cursor)
            else:
                report('okay')



def add_project(connection, service, name):
    with txn(connection) as cursor:
        cursor.execute('''
            INSERT INTO projects
                (service, name)
                VALUES (%s, %s)
        ''', (service, name))


def add_cli(argv=None):
    parser = argparse.ArgumentParser(
        description='Add a project to the queue.',
    )
    parser.add_argument(
        'service', choices=('github',),
        help='service the repo is hosted at',
    )
    parser.add_argument(
        'name',
        help='name of the repo (format varies by service)',
    )
    args = parser.parse_args()

    with connect() as connection:
        add_project(connection, args.service, args.name)
