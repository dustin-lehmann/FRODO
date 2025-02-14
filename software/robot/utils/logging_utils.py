import inspect
import logging
import os
import atexit
import threading
from datetime import datetime
from utils import colors
from utils import string_utils as string_utils


LOG_LEVELS = {
    "CRITICAL": logging.CRITICAL,
    "ERROR": logging.ERROR,
    "WARNING": logging.WARNING,
    "INFO": logging.INFO,
    "DEBUG": logging.DEBUG,
    "NOTSET": logging.NOTSET,
}

redirections = []

# Global variables to manage file logging state
log_files: dict = {}

def cleanup(*args, **kwargs):
    global log_files
    for filename, data in log_files.items():
        data['file'].close()

atexit.register(cleanup)

def enable_redirection(func):
    global redirections
    redirections.append(func)

def disable_redirection(func):
    global redirections
    if func in redirections:
        redirections.remove(func)

def enable_file_logging(filename, path = './', custom_header: str = '', log_all_levels=False):
    """
    Enables file logging. Creates a log file with the name "<filename>_yyyymmdd_hhmmss.log".
    """
    global log_files

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_filename = f"{path}/{filename}_{timestamp}.log"

    try:
        log_file = open(log_filename, 'a')
        log_file.write("BILBO Log\n")
        log_file.write(f"Time {timestamp}: {custom_header}\n")
        log_file.write("YYYY-MM-DD_hh-mm-ss-ms \t Logger \t Level \t Log\n")
        log_files[filename] = {
            'file': log_file,
            'all_levels': log_all_levels,
            'lock': threading.Lock()
        }
        print(f"File logging enabled. Logging to file: {log_filename}")
    except IOError as e:
        print(f"Failed to open log file {log_filename}: {e}")


def stop_file_logging(filename=None):
    """
    Stops file logging and closes the log file.
    """
    global log_files

    if filename is not None:

        if filename in log_files:
            log_files[filename]['file'].close()
            log_files.pop(filename)
            print(f"File logging stopped for {filename}.")
    else:
        for filename, data in log_files.items():
            data['file'].close()
            print(f"File logging stopped for {filename}.")
        log_files = {}

def enable_logging_redirect(function):
    """
    Redirects logging output to a custom function (open for now).
    """
    pass


def handle_log(log, logger: 'Logger', level):
    """
    Appends a line with the format: current_time \t Logger \t level \t log to the log file.
    """
    global log_files

    if len(log_files) == 0:
        return

    if isinstance(level, str):
        level = LOG_LEVELS[level]

    # Reverse the dictionary
    reversed_dict = {v: k for k, v in LOG_LEVELS.items()}

    # Get the key for the given value
    level_name = reversed_dict.get(level)

    current_time = datetime.now().strftime("%Y-%m-%d:%H-%M-%S-%f")[:-3]
    log_entry = f"{current_time}\t{logger.name}\t{level_name}\t{log}\n"

    for redirection in redirections:
        redirection(log_entry, logger, level)

    try:
        for filename, log_file_data in log_files.items():
            with log_file_data['lock']:
                if level >= logger.level or log_file_data['all_levels'] == True:
                    log_file_data['file'].write(log_entry)
                    log_file_data['file'].flush()
    except IOError as e:
        print(f"Failed to write to log file: {e}")




def disableAllOtherLoggers(module_name=None):
    for log_name, log_obj in logging.Logger.manager.loggerDict.items():
        if log_name != module_name:
            log_obj.disabled = True

def disableLoggers(loggers: list):
    for log_name, log_obj in logging.Logger.manager.loggerDict.items():
        if log_name in loggers:
            log_obj.disabled = True

def getLoggerByName(logger_name: str):
    for log_name, log_obj in logging.Logger.manager.loggerDict.items():
        if log_name == logger_name:
            return log_obj
    return None

def setLoggerLevel(logger, level=logging.DEBUG):
    if isinstance(logger, str):
        l = logging.getLogger(logger)
        l.setLevel(level)
    elif isinstance(logger, list) and all(isinstance(l, tuple) for l in logger):
        for logger_tuple in logger:
            l = getLoggerByName(logger_tuple[0])
            if l is not None:
                l.setLevel(logger_tuple[1])
    elif isinstance(logger, list) and all(isinstance(l, str) for l in logger):
        for l in logger:
            logger_object = getLoggerByName(l)
            if logger_object is not None:
                logger_object.setLevel(level)

class CustomFormatter(logging.Formatter):
    _filename: str

    def __init__(self, info_color=string_utils.grey):
        logging.Formatter.__init__(self)

        for handler in logging.root.handlers[:]:
            logging.root.removeHandler(handler)

        self.str_format = "%(asctime)s.%(msecs)03d %(levelname)-10s  %(name)-20s %(filename)-30s  %(message)s"
        self._filename = None

        self.FORMATS = {
            logging.DEBUG: string_utils.escapeCode(colors.DARK_BROWN) + self.str_format + string_utils.reset,
            logging.INFO: info_color + self.str_format + string_utils.reset,
            logging.WARNING: string_utils.yellow + self.str_format + string_utils.reset,
            logging.ERROR: string_utils.red + self.str_format + string_utils.reset,
            logging.CRITICAL: string_utils.bold_red + self.str_format + string_utils.reset
        }

    def setFileName(self, filename):
        self._filename = filename

    def format(self, record):
        log_fmt = self.FORMATS.get(record.levelno)
        formatter = logging.Formatter(log_fmt, "%H:%M:%S")
        record.filename = self._filename
        record.levelname = '[%s]' % record.levelname
        record.filename = '(%s)' % record.filename
        record.name = '[%s]' % record.name
        record.filename = '%s:' % record.filename

        return formatter.format(record)

class Logger:
    _logger: logging.Logger
    name: str
    level: str
    def __init__(self, name, level: str = 'INFO', info_color=colors.LIGHT_GREY, background=None):
        self.name = name
        self._logger = logging.getLogger(name)
        self.setLevel(level)

        if isinstance(info_color, tuple):
            info_color = string_utils.rgb_to_256color_escape(info_color, background)
        elif isinstance(info_color, list):
            info_color = string_utils.rgb_to_256color_escape(info_color, background)

        self.formatter = CustomFormatter(info_color=info_color)
        stream_handler = logging.StreamHandler()
        stream_handler.setFormatter(self.formatter)
        self._logger.addHandler(stream_handler)

    def getFileName(self):
        frame = inspect.currentframe().f_back.f_back
        filename = frame.f_globals.get('__file__')  # Safely get __file__
        if filename:
            filename = os.path.basename(filename)
        else:
            filename = '<unknown>'  # Fallback if __file__ is not found
        return filename

    def debug(self, msg, *args, **kwargs):
        self.formatter.setFileName(self.getFileName())
        self._logger.debug(msg, *args, **kwargs)
        handle_log(msg, logger=self, level=logging.DEBUG)

    def info(self, msg, *args, **kwargs):
        self.formatter.setFileName(self.getFileName())
        self._logger.info(msg, *args, **kwargs)
        handle_log(msg, logger=self, level=logging.INFO)

    def warning(self, msg, *args, **kwargs):
        self.formatter.setFileName(self.getFileName())
        self._logger.warning(msg, *args, **kwargs)
        handle_log(msg, logger=self, level=logging.WARNING)

    def error(self, msg, *args, **kwargs):
        self.formatter.setFileName(self.getFileName())
        self._logger.error(msg, *args, **kwargs)
        handle_log(msg, logger=self, level=logging.ERROR)

    def critical(self, msg, *args, **kwargs):
        self.formatter.setFileName(self.getFileName())
        self._logger.critical(msg, *args, **kwargs)
        handle_log(msg, logger=self, level=logging.CRITICAL)

    def setLevel(self, level):
        if not level in LOG_LEVELS:
            raise ValueError('Invalid log level')
        self.level = LOG_LEVELS[level]
        self._logger.setLevel(level)
