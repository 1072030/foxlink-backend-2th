import logging
import os
import pytz
import time
from app.log import logging
from dotenv import load_dotenv
from typing import List, TypeVar, Optional, Type

from ast import literal_eval

T = TypeVar("T")


def get_env(key: str, dtype: Type[T], default: Optional[T] = None) -> T:
    val = os.getenv(key)

    if val is None:
        if default is not None:
            return default
        else:
            if os.environ.get("USE_ALEMBIC") is None:
                raise KeyError(f"{key} is not set")
            else:
                return None  # type: ignore
    else:
        if dtype in [List[int], List[str], List[float]]:
            return literal_eval(val)
        elif dtype is bool:
            return dtype(int(val))  # type: ignore
        else:
            return dtype(val)  # type: ignore

logger = logging.getLogger('environ')

# Debug mode
DEBUG = get_env("DEBUG", bool, False)

if(DEBUG):
    load_dotenv("/app/.env",override=True)
    logger.warn("ENTER DEBUG MODE, LOADING /app/.env VARIABLES....")

TIMEZONE_OFFSET = 8
WEEK_START = 1  # the week should start on Sunday or Monday or even else.

DATABASE_HOST = get_env("DATABASE_HOST", str)
DATABASE_PORT = get_env("DATABASE_PORT", int)
DATABASE_USER = get_env("DATABASE_USER", str)
DATABASE_PASSWORD = get_env("DATABASE_PASSWORD", str)
DATABASE_NAME = get_env("DATABASE_NAME", str)

PY_ENV = get_env("PY_ENV", str, "production")

FOXLINK_EVENT_DB_HOSTS = get_env("FOXLINK_EVENT_DB_HOSTS", List[str])
FOXLINK_EVENT_DB_USER = get_env("FOXLINK_EVENT_DB_USER", str)
FOXLINK_EVENT_DB_PWD = get_env("FOXLINK_EVENT_DB_PWD", str)
FOXLINK_EVENT_DB_NAME = get_env("FOXLINK_EVENT_DB_NAME", List[str])
FOXLINK_EVENT_DB_TABLE_POSTFIX = get_env("FOXLINK_EVENT_DB_TABLE_POSTFIX", str)

FOXLINK_DEVICE_DB_HOST = get_env("FOXLINK_DEVICE_DB_HOST", str)
FOXLINK_DEVICE_DB_USER = get_env("FOXLINK_DEVICE_DB_USER", str)
FOXLINK_DEVICE_DB_PWD = get_env("FOXLINK_DEVICE_DB_PWD", str)
FOXLINK_DEVICE_DB_NAME = get_env("FOXLINK_DEVICE_DB_NAME", str)

FOXLINK_RESCUE_COUNT = get_env("FOXLINK_RESCUE_COUNT",int,3)
DURATION_AVAILABLE = get_env("DURATION_AVAILABLE",List[int],[20,4800])
UPLOAD_FILES_PATH = get_env("UPLOAD_FILES_PATH",str,"/app/uploaded")

JWT_SECRET = get_env("JWT_SECRET", str, "secret")


# PASSWORDS
PWD_SCHEMA = get_env("PWD_SCHEMA", str, "sha256_crypt")

PWD_SALT = get_env("PWD_SALT", str, "F0XL1NKPWDHaSH")



# 時區
TZ = pytz.timezone("Asia/Taipei")


if os.environ.get("USE_ALEMBIC") is None:
    if PY_ENV not in ["production", "dev"]:
        logger.error("PY_ENV env should be either production or dev!")
        exit(1)

    if PY_ENV == "production" and JWT_SECRET == "secret":
        logger.warn(
            "For security, JWT_SECRET is highly recommend to be set in production environment!!"
        )

    if len(FOXLINK_EVENT_DB_HOSTS) == 0:
        logger.error("FOXLINK_EVENT_DB_HOSTS env should not be empty!")
        exit(1)


