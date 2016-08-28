import sys
import time
import uuid
from contextlib import contextmanager

from codedebt_io.db.connection import connect
from codedebt_io.db.connection import txn
from codedebt_io.project import Project


class Worker:

    def __init__(self, connection):
        self.name = str(uuid.uuid4())
        self.connection = connection
        self.report('initialized')

    def report(self, line):
        print('[worker {}] {}'.format(self.name, line), file=sys.stderr)

    @contextmanager
    def get_job(self):
        """Atomically acquire a lock on a job.

        Returns a job row, or None if there is no outstanding work.
        """
        try:
            # acquire lock on job
            with txn(self.connection) as cursor:
                cursor.execute('''
                    SELECT * FROM projects
                    WHERE indexer IS NULL
                        AND status IN ('new', 'pending')
                    ORDER BY indexer_time ASC
                    LIMIT 1
                ''')
                job = cursor.fetchone()
                if job:
                    cursor.execute('''
                        UPDATE projects
                        SET indexer = %s, indexer_time = NOW()
                        WHERE id = %s
                    ''', (self.name, job['id']))
            yield Project.from_row(job) if job else None
        finally:
            # release lock on the job
            if job:
                with txn(self.connection) as cursor:
                    cursor.execute('''
                        UPDATE projects
                        SET indexer = NULL
                        WHERE id = %s
                    ''', (job['id'],))

    def work_forever(self):
        self.report('started')
        while True:
            self.work()
            time.sleep(1)

    def work(self):
        with self.get_job() as project:
            if not project:
                self.report('no work available')
                return
            self.report('updating: {}'.format(project))
            project.update(self.connection, self.report)


def main(argv=None):
    with connect() as connection:
        worker = Worker(connection)
        worker.work_forever()
