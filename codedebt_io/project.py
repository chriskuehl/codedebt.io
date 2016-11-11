import argparse
from collections import namedtuple

from cached_property import cached_property

from codedebt_io.db.connection import connect
from codedebt_io.db.connection import txn
from codedebt_io.db.connection import use_db
from codedebt_io.git_code_debt import apply_schema
from codedebt_io.git_code_debt import load_data
from codedebt_io.git_code_debt import populate_metric_ids


class Project(namedtuple('Project', (
    'id',
    'service',
    'name',
    'status',
    'indexer',
    'indexer_time',
))):

    @classmethod
    def from_row(cls, row):
        return cls(
            id=row['id'],
            service=row['service'],
            name=row['name'],
            status=row['status'],
            indexer=row['indexer'],
            indexer_time=row['indexer_time'],
        )

    @cached_property
    def git_url(self):
        return {
            'github': 'git://github.com/{self.name}.git',
        }[self.service].format(self=self)

    @cached_property
    def db_name(self):
        return 'proj_{self.id}'.format(self=self)

    def position_in_queue(self, cursor):
        cursor.execute('''
            SELECT COUNT(*) AS count
            FROM projects
            WHERE status != 'ready' AND indexer_time < %s AND indexer IS NULL
        ''', (self.indexer_time,))
        return cursor.fetchone()['count'] + 1

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
            apply_schema(cursor)
            populate_metric_ids(cursor)

    def update(self, connection, report):
        with txn(connection) as cursor:
            if not self.db_exists(cursor):
                report('must create database')
                self.db_create(cursor)

            report('updating data')
            with use_db(cursor, self.db_name):
                try:
                    load_data(cursor, self)
                except Exception:
                    # This might be fatal (project does not exist) or temporary
                    # (network error). For now we just remove forever. It can
                    # be queued again later if desired.
                    with use_db(cursor, 'codedebt'):
                        remove_project(connection, self.service, self.name)


def add_project(connection, service, name):
    with txn(connection) as cursor:
        cursor.execute('''
            INSERT INTO projects
                (service, name)
                VALUES (%s, %s)
        ''', (service, name))


def remove_project(connection, service, name):
    with txn(connection) as cursor:
        cursor.execute('''
            DELETE FROM projects
                WHERE service = %s AND name = %s
        ''', (service, name))


def get_project(connection, service, name):
    with txn(connection) as cursor:
        cursor.execute('''
            SELECT * FROM projects
            WHERE
                service = %s AND
                name = %s
        ''', (service, name))
        job = cursor.fetchone()

    if job:
        return Project.from_row(job)


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
