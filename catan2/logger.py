from datetime import datetime
from enum import Enum
from typing import Callable
import inspect
import json
import logging

from catan2 import config

logging.TRACE = logging.DEBUG - 5
logging.addLevelName(logging.TRACE, 'TRACE')


def trace(self, message, *args, **kwargs):
    if self.isEnabledFor(logging.TRACE):
        self._log(logging.TRACE, message, args, **kwargs)


logging.getLoggerClass().trace = trace


class LogLevel(Enum):
    CRITICAL = logging.CRITICAL
    WARNING  = logging.WARNING
    ERROR    = logging.ERROR
    INFO     = logging.INFO
    DEBUG    = logging.DEBUG
    TRACE    = logging.TRACE


class Logger:

    def __init__(self):
        self.log = logging.getLogger()
        self.level = LogLevel['INFO']

    def setup(self, filename, level):
        self.level = LogLevel[level.upper()].value
        logging.basicConfig(filename=filename, level=self.level)

    @staticmethod
    def _log(message: str, data: object, tags: [str], log_func: Callable[[str], None]):
        if tags is None or any([config['logging']['categories'][tag] for tag in tags]):
            where = inspect.stack()[2].function
            when = ':' + datetime.now().strftime('%Y-%m-%dT%H:%M:%S.%f')[:-3]
            what = "#" + '#'.join([tag.upper() for tag in tags]) if tags is not None else ''
            message = '\n' + message if message else ''
            stringy_data = '\n' + json.dumps(data, indent=4) if data is not None else ''

            to_log = where + when + what + message + stringy_data + '\n'
            log_func(to_log)

    def critical(self, message: str = '', data: object = None, tags: [str] = None):
        if self.level <= LogLevel['CRITICAL'].value:
            self._log(message, data, tags, self.log.critical)

    def error(self, message: str = '', data: object = None, tags: [str] = None):
        if self.level <= LogLevel['ERROR'].value:
            self._log(message, data, tags, self.log.error)

    def warning(self, message: str = '', data: object = None, tags: [str] = None):
        if self.level <= LogLevel['WARNING'].value:
            self._log(message, data, tags, self.log.warning)

    def info(self, message: str = '', data: object = None, tags: [str] = None):
        if self.level <= LogLevel['INFO'].value:
            self._log(message, data, tags, self.log.info)

    def debug(self, message: str = '', data: object = None, tags: [str] = None):
        if self.level <= LogLevel['DEBUG'].value:
            self._log(message, data, tags, self.log.debug)

    def trace(self, message: str = '', data: object = None, tags: [str] = None):
        if self.level <= LogLevel['TRACE'].value:
            self._log(message, data, tags, self.log.trace)


log = Logger()
