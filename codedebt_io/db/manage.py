import argparse
import os

from codedebt_io.config import config
from codedebt_io.db.connection import connect
from codedebt_io.db.connection import txn


def apply_schema(connection, force=False):
    with txn(connection) as cursor:
        if force:
            cursor.execute('DROP DATABASE IF EXISTS codedebt')
        cursor.execute('CREATE DATABASE codedebt')
        cursor.execute('USE codedebt')
        cursor.execute('''
            CREATE TABLE projects (
                id INT NOT NULL PRIMARY KEY AUTO_INCREMENT,
                service VARCHAR(255) NOT NULL,
                name VARCHAR(255) NOT NULL,
                status VARCHAR(255) NOT NULL DEFAULT 'new',
                indexer VARCHAR(255),
                indexer_time DATETIME,
                UNIQUE KEY `idx_codedebt_unique` (`service`, `name`)
            ) ENGINE=InnoDB
        ''')


def makedb(argv=None):
    parser = argparse.ArgumentParser(
        description='Set up the database.',
    )
    parser.add_argument(
        '-f', '--force', default=False, action='store_true',
        help='drop existing database, if it exists.',
    )
    args = parser.parse_args()

    with connect(
        db=None,
    ) as connection:
        apply_schema(connection, force=args.force)


def cli():
    os.execlp(
        'mysql',
        'mysql',
        '--ssl',
        '--user=' + config.get('database', 'user'),
        '--password=' + config.get('database', 'password'),
        '--host', config.get('database', 'host'),
        config.get('database', 'db'),
    )
