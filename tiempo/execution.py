from . import RECENT_KEY
from tiempo import tiempo_loop
from tiempo.work import Job
from tiempo.runner import Runner
from .conn import REDIS
from .conf import INTERVAL, THREAD_CONFIG, RESULT_LIFESPAN, DEBUG
from cStringIO import StringIO

import sys
import chalk
import json

from dateutil.relativedelta import relativedelta
from tiempo.utils import utc_now
from twisted.logger import Logger
logger = Logger()


class CaptureStdOut(list):

    def __init__(self, *args, **kwargs):

        self.task = kwargs.pop('task')
        self.start_time = utc_now()

        super(CaptureStdOut, self).__init__(*args, **kwargs)

    def __enter__(self):
        if DEBUG:
            pass
            # return self
        self._stdout = sys.stdout
        sys.stdout = self._stringio = StringIO()
        return self

    def __exit__(self, *args):
        if DEBUG:
            # return
            pass

        self.extend(self._stringio.getvalue().splitlines())
        sys.stdout = self._stdout

    def finished(self, timestamp=None):
        if DEBUG:
            pass
            # return

        self.timestamp = timestamp
        if not timestamp:
            self.timestamp = utc_now()

        task_key = '%s:%s' % (self.task.key, self.task.uid)
        expire_time = int(((self.timestamp + relativedelta(
            days=RESULT_LIFESPAN)) - self.timestamp).total_seconds())

        pipe = REDIS.pipeline()
        pipe.zadd(RECENT_KEY, self.start_time.strftime('%s'), task_key)
        pipe.set(self.task.uid, self.format_output())
        pipe.expire(self.task.uid, expire_time)
        pipe.execute()

    def format_output(self):

        return json.dumps(
            {
                'task': self.task.key,
                'uid': self.task.uid,
                'start_time': self.start_time.isoformat(),
                'end_time': self.timestamp.isoformat(),
                'duration': (self.timestamp - self.start_time).total_seconds(),
                'output': self
            }
        )





def thread_init():
    if len(THREAD_CONFIG):
        chalk.green('current time: %r' % utc_now())
        chalk.green(
            'Found %d thread(s) specified by THREAD_CONFIG' % len(THREAD_CONFIG)
        )

        for index, thread_group_list in enumerate(THREAD_CONFIG):
            runner = Runner(index, thread_group_list)

    tiempo_loop.start()
