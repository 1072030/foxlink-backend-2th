import logging

grey = '\x1b[38;21m'
blue = '\x1b[38;5;39m'
bold_blue = '\x1b[1;34m'
yellow = '\x1b[38;5;226m'
red = '\x1b[38;5;196m'
bold_red = '\x1b[31;1m'
reset = '\x1b[0m'

LOGGER_NAME: str = "uvicorn"
# LOG_FORMAT: str = f"{grey}@%(asctime)s{reset}[{{color_level}}%(levelname)s{reset}]: {reset}%(message)s{reset}"
LOG_FORMAT_TERMINAL: str = f"{bold_blue}@%(name)s{reset}[{{color_level}}%(levelname)s{reset}](%(asctime)s): {reset}%(message)s{reset}"
LOG_FORMAT_FILE: str = f"@%(name)s[%(levelname)s](%(asctime)s):%(message)s"
LOG_LEVEL: str = "INFO"


class CustomFormatter(logging.Formatter):
    """Logging colored formatter, adapted from https://stackoverflow.com/a/56944256/3638629"""

    def __init__(self, fmt):
        super().__init__()
        self.fmt = fmt
        self.FORMATS = {
            logging.DEBUG: self.fmt.format(
                color_level=grey,
            ),
            logging.INFO: self.fmt.format(
                color_level=blue,
            ),
            logging.WARNING: self.fmt.format(
                color_level=yellow,
            ),
            logging.ERROR: self.fmt.format(
                color_level=red,
            ),
            logging.CRITICAL: self.fmt.format(
                color_level=bold_red,
            ),
        }

    def format(self, record):
        log_fmt = self.FORMATS.get(record.levelno)
        formatter = logging.Formatter(log_fmt)
        return formatter.format(record)


baseHandler = logging.StreamHandler()
baseHandler.setFormatter(CustomFormatter(LOG_FORMAT_TERMINAL))

logging.basicConfig(level=LOG_LEVEL, handlers=[baseHandler])

# class LogConfig(BaseModel):
# pass
#     """Logging configuration to be set for the server"""

#     # Logging config
#     version = 1
#     disable_existing_loggers = True
#     formatters = {
#         "default": {
#             "()": "uvicorn.logging.DefaultFormatter",
#             "fmt": LOG_FORMAT,
#             "datefmt": "%Y-%m-%d %H:%M:%S",
#         },
#     }
#     handlers = {
#         "default": {
#             "formatter": "default",
#             "class": "logging.StreamHandler",
#             "stream": "ext://sys.stderr",
#         },
#     }
#     loggers = {
#         f"{LOGGER_NAME}": {"handlers": ["default"], "level": LOG_LEVEL},
#         "uvicorn.access": {"handlers": ["default"], "level": "INFO"},
#         # "uvicorn": {"handlers": ["default"], "level": "INFO"},
#         "uvicorn.error": {"handlers": ["default"], "level": "ERROR"},
#     }
# default_logger_setting =  {"handlers": ["default"], "level": LOG_LEVEL}

# @staticmethod
# def add_logger(name):
#     LogConfig.loggers['name'] = LogConfig.default_logger_setting
