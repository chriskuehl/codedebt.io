import json
import os
import re
import tempfile

from codedebt_io.db.connection import connect
from codedebt_io.db.connection import txn
from codedebt_io.db.connection import use_db
from codedebt_io.git_code_debt import FakeSqlite
from codedebt_io.git_code_debt import METRIC_CONFIG
from codedebt_io.project import add_project
from codedebt_io.project import get_project


def app(environ, start_response):
    import git_code_debt.server.app

    with tempfile.TemporaryDirectory() as tempdir:
        cwd = os.getcwd()
        try:
            os.chdir(tempdir)

            # write out metric config
            with open('metric_config.yaml', 'w') as f:
                json.dump(METRIC_CONFIG, f)

            # munge some stuff
            # TODO: better way to do this...
            # TODO: eventually want to not assume github
            m = re.match(r'/github/([^/]+)/([^/]+)(/.*|$)', environ['PATH_INFO'])

            if m:
                owner = m.group(1)
                project = m.group(2)
                remainder = m.group(3) or '/'

                service = 'github'
                name = '{}/{}'.format(owner, project)

                environ['PATH_INFO'] = remainder

                with connect() as connection:
                    proj = get_project(connection, service, name)
                    if proj is not None:
                        if proj.status == 'new':
                            start_response('503 Service Unavailable', [
                                ('Content-Type', 'text/plain'),
                            ])
                            return [b'that project is waiting to be indexed!']
                        else:
                            with txn(connection) as cursor:
                                with use_db(cursor, proj.db_name):
                                    def fake_connect(*args):
                                        fake = FakeSqlite(cursor)
                                        fake.__enter__()
                                        return fake

                                    git_code_debt.server.app.sqlite3.connect = fake_connect
                                    return git_code_debt.server.app.app(environ, start_response)
                    else:
                        add_project(connection, service, name)
                        start_response('404 Not Found', [
                            ('Content-Type', 'text/plain'),
                        ])
                        return [b'that project does not exist yet; try refreshing']

            else:
                start_response('404 Not Found', [
                    ('Content-Type', 'text/plain'),
                ])
                return [b'you probably want: /github/{owner}/{project}']
        finally:
            os.chdir(cwd)
