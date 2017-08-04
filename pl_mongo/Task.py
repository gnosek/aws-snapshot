import logging

from multiprocessing import cpu_count
from signal import signal, SIGINT, SIGTERM, SIG_IGN

from pl_mongo.Errors import Error


class Task(object):
    def __init__(self, task_name, manager, config, timer, **kwargs):
        self.task_name  = task_name
        self.manager    = manager
        self.config     = config
        self.timer      = timer
        self.args       = kwargs
        self.verbose    = self.config.verbose

        self.runnning  = False
        self.stopped   = False
        self.completed = False
        self.exit_code = 255

        self.timer_name = self.__class__.__name__

        signal(SIGINT, SIG_IGN)
        signal(SIGTERM, self.close)

    def run(self):
        raise Error("Must define a .run() method when using %s class!" % self.__class__.__name__)

    def close(self, code=None, frame=None):
        raise Error("Must define a .close() method when using %s class!" % self.__class__.__name__)
