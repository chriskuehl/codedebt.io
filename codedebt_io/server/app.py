import json
import os
import re
import tempfile

from pyquery import PyQuery as pq

from codedebt_io.db.connection import connect
from codedebt_io.db.connection import txn
from codedebt_io.db.connection import use_db
from codedebt_io.git_code_debt import FakeSqlite
from codedebt_io.git_code_debt import METRIC_CONFIG
from codedebt_io.project import add_project
from codedebt_io.project import get_project


os.chdir(tempfile.mkdtemp())


def transform_response(resp, prefix):
    content = b''.join(resp)
    p = pq(content)
    el, = p

    if el.tag != 'html':
        yield content
    else:
        for _el in p.find('link, a, script'):
            el = pq(_el)
            for attr in ('src', 'href'):
                a = el.attr(attr)
                if a and not a.startswith(('//', 'http:', 'https:')):
                    el.attr(attr, prefix + a)

        yield str(p).encode('utf8')
        yield b'\n'


def app(environ, start_response):
    import git_code_debt.server.app

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
                    yield b'in the queue now, try refreshing'
                else:
                    with txn(connection) as cursor:
                        with use_db(cursor, proj.db_name):
                            def fake_connect(*args):
                                fake = FakeSqlite(cursor)
                                fake.__enter__()
                                return fake

                            git_code_debt.server.app.sqlite3.connect = fake_connect

                            def _start_response(status, headers):
                                start_response(status, [
                                    (header, value) for (header, value) in headers
                                    if header.lower() != 'content-length'
                                ])

                            yield from transform_response(
                                git_code_debt.server.app.app(environ, _start_response),
                                '/github/{}/{}'.format(owner, project),
                            )
            else:
                add_project(connection, service, name)
                start_response('404 Not Found', [
                    ('Content-Type', 'text/plain'),
                ])
                yield b'this project has been queued, try refreshing.'

    elif environ['PATH_INFO'] == '/status':
        start_response('200 Ok', [
            ('Content-Type', 'text/plain'),
        ])
        yield b'ok!'
    else:
        start_response('404 Not Found', [
            ('Content-Type', 'text/plain'),
        ])
        yield b'you probably want: /github/{owner}/{project}'
