import json
import os
import re
import tempfile
from urllib.parse import urlparse

from pyquery import PyQuery as pq

from codedebt_io.db.connection import connect
from codedebt_io.db.connection import txn
from codedebt_io.db.connection import use_db
from codedebt_io.git_code_debt import FakeSqlite
from codedebt_io.git_code_debt import METRIC_CONFIG
from codedebt_io.project import add_project
from codedebt_io.project import get_project


os.chdir(tempfile.mkdtemp())


def add_prefix(url, prefix):
    parsed = urlparse(url)
    # TODO: how to do this better?
    if parsed.netloc in ('', 'localhost:5000'):
        # TODO: disgusting
        return prefix + parsed.path + '?' + parsed.query
    else:
        return url


def transform_response(resp, prefix):
    content = b''.join(resp)
    p = pq(content)
    el, = p

    if el.tag != 'html':
        yield content
    else:
        for _el in p.find('link, a, script, img, div'):
            el = pq(_el)
            for attr in ('src', 'href', 'data-ajax-url'):
                a = el.attr(attr)
                if a:
                    el.attr(attr, add_prefix(a, prefix))

        yield p.html(method='html').encode('utf8')
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
                    prefix = '/github/{}/{}'.format(owner, project)
                    with txn(connection) as cursor:
                        with use_db(cursor, proj.db_name):
                            def fake_connect(*args):
                                fake = FakeSqlite(cursor)
                                fake.__enter__()
                                return fake

                            git_code_debt.server.app.sqlite3.connect = fake_connect

                            def _start_response(status, headers):
                                new_headers = []
                                for header, value in headers:
                                    header = header.lower()
                                    if header == 'location':
                                        value = add_prefix(value, prefix)
                                    elif header == 'content-length':
                                        # Flask adds this header, but we might manipulate the content later.
                                        # It's fine to remove (the WSGI server will probably add it back?)
                                        continue

                                    new_headers.append((header, value))

                                start_response(status, new_headers)

                            yield from transform_response(
                                git_code_debt.server.app.app(environ, _start_response),
                                prefix,
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
