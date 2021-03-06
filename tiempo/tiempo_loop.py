from twisted.internet import task
from constants import BUSY, IDLE
from tiempo import RUNNERS, TIEMPO_REGISTRY, all_runners
from twisted.logger import Logger
from tiempo.conn import REDIS
from tiempo.utils import utc_now, task_time_keys
import datetime

logger = Logger()


def run():
    this_loop_runtime = utc_now()

    # This loop basically does two things:
    for runner in all_runners():
        # 1) Let the runners pick up any queued tasks.
        result = runner.run()

        if not result in (BUSY, IDLE):
            # If the runner is neither busy nor idle, it will have returned a Deferred.
            result.addCallback(runner.finish_job)


    # 2) Queue up new tasks.
    for task_string, task in TIEMPO_REGISTRY.items():

        ### REPLACE with task.next_expiration_dt()
        if hasattr(task, 'force_interval'):
            expire_key = this_loop_runtime + datetime.timedelta(
                    seconds=task.force_interval
            )
        else:
            expire_key = task_time_keys().get(task.get_schedule())
        #########

        if expire_key:
            stop_key_has_expired = REDIS.setnx(task.stop_key, 0)

            if stop_key_has_expired:

                REDIS.expire(
                    task.stop_key,
                    int(float((expire_key - this_loop_runtime).total_seconds())) - 1
                )

                # OK, we're ready to queue up a new job for this task!
                task.spawn_job()


looper = task.LoopingCall(run)


def start():
    logger.info("tiempo_loop start() called.")

    if not looper.running:
        looper.start(1) #INTERVAL)
    else:
        logger.warning("Tried to call tiempo_loop start() while the loop is already running.")