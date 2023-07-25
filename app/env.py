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

# MQTT
MQTT_BROKER = get_env("MQTT_BROKER", str)
MQTT_PORT = get_env("MQTT_PORT", int, 1883)
# EMQX default admin account is (username: admin, password: public)
EMQX_USERNAME = get_env("EMQX_USERNAME", str, "admin")
EMQX_PASSWORD = get_env("EMQX_PASSWORD", str, "public")

# Factory related configs
# Day shift: 07:40 ~ 19:40, Night shift: 19:40 ~ 07:40
WORKER_REJECT_AMOUNT_NOTIFY = get_env("WORKER_REJECT_AMOUNT_NOTIFY", int, 2)
MISSION_REJECT_AMOUT_NOTIFY = get_env("MISSION_REJECT_AMOUT_NOTIFY", int, 2)

# DAY_SHIFT_BEGIN = get_env("DAY_SHIFT_BEGIN", str, "07:40")
# DAY_SHIFT_END = get_env("DAY_SHIFT_END", str, "19:40")

MAX_NOT_ALIVE_TIME = get_env("MAX_NOT_ALIVE_TIME", int, 5)  # unit: minutes

# MISSION_WORK_OT_NOTIFY_PYRAMID_MINUTES = get_env(
#     "MISSION_WORK_OT_NOTIFY_PYRAMID_MINUTES", List[float], [20, 30, 30]
# )

# 當員工身處非 Rescue Station 時，若超過此時間，則自動派遣這名員工到 Rescue Station
WORKER_IDLE_OT_RESCUE_MINUTES = get_env("WORKER_IDLE_OT_RESCUE_MINUTES", int, 1)  # unit: minutes")

# 白名單最低故障數建議閥值
WHITELIST_MINIMUM_OCCUR_COUNT = get_env(
    "WHITELIST_MINIMUM_OCCUR_COUNT", int, 0)

# 取消自動派工
DISABLE_FOXLINK_DISPATCH = get_env("DISABLE_FOXLINK_DISPATCH", bool, False)

# 員工被指派沒有反應時間
MISSION_ASSIGN_OT_MINUTES = get_env("MISSION_ASSIGN_OT_MINUTES", float, 3)

# 例行程序參數設定
RECENT_EVENT_PAST_DAYS = get_env("RECENT_EVENT_PAST_DAYS", int, 1)

# 例行程序參數設定
DISABLE_STARTUP_RESCUE_MISSION = get_env("DISABLE_STARTUP_RESCUE_MISSION", bool, True)

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

    if MQTT_BROKER is None:
        logger.error("MQTT_BROKER is not set")
        exit(1)

    if DISABLE_FOXLINK_DISPATCH is True:
        logger.warn("DISABLE_FOXLINK_DISPATCH is set to True, automatic dispatching is disabled!")

