import databases
import ormar
import uuid
import traceback
import sqlalchemy
import asyncio
from datetime import date, timedelta, datetime, time
from typing import Optional, List, ForwardRef
from enum import Enum
from ormar import property_field, pre_update
from pydantic import Json
from sqlalchemy import MetaData, create_engine
from sqlalchemy.sql import func
from app.env import (
    DATABASE_HOST,
    DATABASE_PORT,
    DATABASE_USER,
    DATABASE_PASSWORD,
    DATABASE_NAME,
    PY_ENV,
    TZ,
)
from sqlalchemy.ext.compiler import compiles
from sqlalchemy.types import DateTime
from sqlalchemy.dialects.mysql import DATETIME

DATABASE_URI = f"mysql+aiomysql://{DATABASE_USER}:{DATABASE_PASSWORD}@{DATABASE_HOST}:{DATABASE_PORT}/{DATABASE_NAME}"

api_db = databases.Database(DATABASE_URI, min_size=3, max_size=5, pool_recycle=180)

metadata = MetaData()

ProjectRef = ForwardRef("Project")
AuditLogHeaderRef = ForwardRef("AuditLogHeader")
UserRef = ForwardRef("User")
DeviceRef = ForwardRef("Device")


def generate_uuidv4():
    return str(uuid.uuid4())


def get_ntz_now():
    return datetime.now()


def get_ntz_min():
    return datetime.fromisoformat("1990-01-01 00:00:00.000")

@compiles(DateTime, "mysql")
def compile_datetime_mysql(type_, compiler, **kw):
     return "DATETIME(3)"

def transaction(callback=False):
    def decor(func):
        async def wrapper(*args, **_args):
            try:
                result = None
                if (callback):
                    root = not "handler" in _args
                    if (root):
                        _args["handler"] = []
                    async with api_db.transaction(isolation="serializable"):
                        result = await func(*args, **_args)
                    if (root and len(_args["handler"]) > 0):
                        await asyncio.gather(*_args["handler"])

                else:
                    async with api_db.transaction(isolation="serializable"):
                        result = await func(*args, **_args)
                return result

            except Exception as e:
                print(f"error in transaction: {repr(e)}")
                raise e

        return wrapper
    return decor

# def transaction(force=False):
#     def decor(func):
#         async def wrapper(*args, **_args):
#             try:
#                 _transaction = await api_db.transaction(isolation="serializable",force_rollback=force)
#                 result = None
#                 try:
#                     await _transaction.start()
#                     result = await func(*args, **_args)
#                 except Exception as e:
#                     await _transaction.rollback()
#                     raise e
#                 else:
#                     await _transaction.commit()
#                     return result
#             except Exception as e:
#                 print(f"error in transaction: {repr(e)}")
#                 raise e

#         return wrapper
#     return decor


def transaction_with_logger(logger):
    def decor(func):
        async def wrapper(*args, **_args):

            _transaction = (api_db.transaction(isolation="serializable"))
            result = None
            try:
                if (logger):
                    logger.info("transaction starting")
                await _transaction.start()
                if (logger):
                    logger.info("transaction started successful")
                result = await func(*args, **_args)
            except Exception as e:
                # traceback.print_exc()
                print(f"error in transaction: {repr(e)}")
                await _transaction.rollback()
                if (logger):
                    logger.info("transaction ended failure")
                raise e
            else:
                await _transaction.commit()
                if (logger):
                    logger.info("transaction ended success")
                return result
        return wrapper
    return decor


# class UserLevel(Enum):
#     maintainer = 1  # 維修人員
#     manager = 2  # 線長
#     supervisor = 3  # 組長
#     chief = 4  # 課級
#     admin = 5  # 管理員

class UserLevel(Enum):
    base=1
    manager = 2

    project_owner = 4
    admin = 5

# class ShiftType(Enum):
#     day = 1
#     night = 2


# ShiftInterval = {
#     ShiftType.day: [
#         time.fromisoformat(DAY_SHIFT_BEGIN),
#         time.fromisoformat(DAY_SHIFT_END)
#     ],
#     ShiftType.night: [
#         time.fromisoformat(DAY_SHIFT_END),
#         time.fromisoformat(DAY_SHIFT_BEGIN)
#     ]
# }


class WorkerStatusEnum(Enum):
    working = "Working"
    notice = 'Notice'
    moving = 'Moving'
    idle = "Idle"
    leave = "Leave"


class LogoutReasonEnum(Enum):
    meeting = "Meeting"
    leave = "Leave"
    rest = "Rest"
    offwork = "OffWork"

class EnvEnum(Enum):
    auto_rescue = "auto_rescue"
    rescue_count = "rescue_count"
    history_record_days = "history_record_days"

class AuditActionEnum(Enum):
    MISSION_CREATED = "MISSION_CREATED"
    MISSION_REJECTED = "MISSION_REJECTED"
    MISSION_ACCEPTED = "MISSION_ACCEPTED"
    MISSION_ASSIGNED = "MISSION_ASSIGNED"
    MISSION_STARTED = "MISSION_STARTED"
    MISSION_FINISHED = "MISSION_FINISHED"
    MISSION_DELETED = "MISSION_DELETED"
    MISSION_UPDATED = "MISSION_UPDATED"
    MISSION_OVERTIME = "MISSION_OVERTIME"
    MISSION_CANCELED = "MISSION_CANCELED"
    MISSION_CURED = "MISSION_CURED"
    MISSION_USER_DUTY_SHIFT = "MISSION_USER_DUTY_SHIFT"
    MISSION_EMERGENCY = "MISSION_EMERGENCY"
    USER_LOGIN = "USER_LOGIN"
    USER_LOGOUT = "USER_LOGOUT"
    USER_MOVE_POSITION = "USER_MOVE_POSITION"
    DATA_IMPORT_FAILED = "DATA_IMPORT_FAILED"
    DATA_IMPORT_SUCCEEDED = "DATA_IMPORT_SUCCEEDED"

    AUTO_RESCUE_GENERATE_SUCCEEDED = "AUTO_RESCUE_GENERATE_SUCCEEDED"
    AUTO_RESCUE_GENERATE_FAILED = "AUTO_RESCUE_GENERATE_FAILED"

    MISSION_ACCEPT_OVERTIME = "MISSION_ACCEPT_OVERTIME"
    NOTIFY_MISSION_NO_WORKER = "NOTIFY_MISSION_NO_WORKER"

    DATA_PREPROCESSING_STARTED = "DATA_PREPROCESSING_STARTED"
    DATA_PREPROCESSING_SUCCEEDED = "DATA_PREPROCESSING_SUCCESS"
    DATA_PREPROCESSING_FAILED = "DATA_PREPROCESSING_FAILED"




class MainMeta(ormar.ModelMeta):
    metadata = metadata
    database = api_db


# class Shift(ormar.Model):
#     class Meta(MainMeta):
#         pass
#     id: int = ormar.Integer(primary_key=True, index=True,
#                             autoincrement=False, choices=list(ShiftType), nullable=False)
#     shift_beg_time = ormar.Time(timezone=True, nullable=False)
#     shift_end_time = ormar.Time(timezone=True, nullable=False)


# class FactoryMap(ormar.Model):
#     class Meta(MainMeta):
#         tablename = "factory_maps"

#     id: int = ormar.Integer(primary_key=True, index=True)
#     name: str = ormar.String(max_length=100, index=True, unique=True)
#     map: Json = ormar.JSON()
#     related_devices: Json = ormar.JSON()
#     image: bytes = ormar.LargeBinary(max_length=5242880, nullable=True)
#     created_date: datetime = ormar.DateTime(default=get_ntz_now, timezone=True)
#     updated_date: datetime = ormar.DateTime(default=get_ntz_now, timezone=True)

#     @staticmethod
#     def heavy_fields(represent="") -> List["str"]:
#         return [
#             field if len(represent) == 0 else f"{represent}__{field}"
#             for field in ["map", "related_devices", "image"]
#         ]

class Env(ormar.Model):
    class Meta(MainMeta):
        tablename="env"
    id: str = ormar.String(max_length=100, primary_key=True, index=True)
    # auto_rescue: bool = ormar.Boolean(server_default="0", nullable=True)
    key:str = ormar.String(max_length=50, nullable=False)
    value:str = ormar.String(max_length=50, nullable=False)

class User(ormar.Model):
    class Meta(MainMeta):
        pass

    badge: str = ormar.String(primary_key=True, max_length=100, index=True)
    username: str = ormar.String(max_length=50, nullable=False)
    # level: int = ormar.SmallInteger(choices=list(UserLevel), nullable=False)
    password_hash: str = ormar.String(max_length=100, nullable=True)
    current_UUID: str = ormar.String(max_length=100, nullable=True)
    ####################
    flag:bool = ormar.Boolean(default=False)
    ####################
    login_date: datetime = ormar.DateTime(default=get_ntz_min, timezone=True)
    logout_date: datetime = ormar.DateTime(default=get_ntz_min, timezone=True)
    updated_date: datetime = ormar.DateTime(default=get_ntz_now, timezone=True)
    created_date: datetime = ormar.DateTime(default=get_ntz_now, timezone=True)
    
    # def User_flag_fetch():
    #     return User.objects.filter(flag=True)


class Project(ormar.Model):
    class Meta(MainMeta):
        tablename="projects"
    id:int = ormar.Integer(primary_key=True,autoincrement=True,nullable=False)
    name:str = ormar.String(max_length=50, nullable=False)
    created_date:datetime = ormar.DateTime(default=get_ntz_now,timezone=True)

class Device(ormar.Model):
    class Meta(MainMeta):
        tablename="devices"
    id:int = ormar.Integer(primary_key=True,autoincrement=True,nullable=False)
    line:int = ormar.Integer(nullable=False)
    device_name:str = ormar.String(max_length=100,nullable=False)
    project:int = ormar.ForeignKey(Project, index=True, nullable=False,ondelete="CASCADE")
    created_date:datetime = ormar.DateTime(default=get_ntz_now,timezone=True)

class ProjectUser(ormar.Model):
    class Meta(MainMeta):
        tablename="project_users"
        
    id:int = ormar.Integer(primary_key=True,autoincrement=True,nullable=False)
    
    project:ProjectRef = ormar.ForeignKey(
        ProjectRef,
        ondelete="CASCADE",
        related_name="project"
    )
    
    user: User = ormar.ForeignKey(User,index=True, nullable=False)
    permission: int = ormar.Integer(choices=list(UserLevel))

class ProjectEvent(ormar.Model):
    class Meta(MainMeta):
        tablename="project_events"
    
    id:int = ormar.Integer(primary_key=True,autoincrement=True,nullable=False)
    
    device:DeviceRef = ormar.ForeignKey(
        DeviceRef,
        index=True,
        ondelete="CASCADE",
        related_name="device"
    )
    name:str = ormar.String(max_length=50, nullable=False)
    created_date:datetime = ormar.DateTime(default=get_ntz_now,timezone=True)

class Aoi_measure(ormar.Model):
    class Meta(MainMeta):
        tablename="aoi_measures"
    id:int = ormar.Integer(primary_key=True,autoincrement=True,nullable=False)
    device:int = ormar.ForeignKey(Device, index=True, nullable=False,ondelete="CASCADE")
    aoi_measure_name:str = ormar.String(max_length=100,index=True)
    created_date:datetime = ormar.DateTime(default=get_ntz_now,timezone=True)

class Hourly_mf(ormar.Model):
    class Meta(MainMeta):
        tablename="hourly_mf"
    id:int = ormar.Integer(primary_key=True,autoincrement=True,nulaoi_measurelable=False)
    date:datetime = ormar.DateTime(timezone=True)
    hour:int = ormar.Integer(nullable=False)
    shift:str = ormar.String(max_length=100,index=True)
    pcs:int = ormar.Integer(nullable=True)
    ng_num:int = ormar.Integer(nullable=True)
    ng_rate:float = ormar.Float(nullable=True)
    first_prod_time:datetime = ormar.DateTime(nullable=True)
    last_prod_time:datetime = ormar.DateTime(nullable=True)
    operation_time:time = ormar.Time(nullable=True)
    device:int = ormar.ForeignKey(Device, index=True, nullable=False,ondelete="CASCADE")
    aoi_measure:int = ormar.ForeignKey(Aoi_measure, index=True, nullable=False,ondelete="CASCADE")
    # created_date:datetime = ormar.DateTime(default=get_ntz_now,timezone=True)

class Dn_mf(ormar.Model):
    class Meta(MainMeta):
        tablename="dn_mf"
    id:int = ormar.Integer(primary_key=True,autoincrement=True,nullable=False)
    date:datetime = ormar.DateTime(timezone=True)
    shift:str = ormar.String(max_length=100,index=True)
    pcs:int = ormar.Integer(nullable=True)
    operation_time:time = ormar.Time(nullable=True)
    device = ormar.ForeignKey(Device, index=True, nullable=False,ondelete="CASCADE")
    aoi_measure:int = ormar.ForeignKey(Aoi_measure, index=True, nullable=False,ondelete="CASCADE")
    # created_date:datetime = ormar.DateTime(default=get_ntz_now,timezone=True)

class Aoi_feature(ormar.Model):
    class Meta(MainMeta):
        tablename="aoi_feature"
    id:int = ormar.Integer(primary_key=True,autoincrement=True,nullable=False)
    date:datetime = ormar.DateTime(timezone=True)
    operation_day:bool=ormar.Boolean(default=False)
    pcs:int = ormar.Integer(nullable=True)
    ng_num:int = ormar.Integer(nullable=True)
    ng_rate:float = ormar.Float(nullable=True)
    
    ct_max:float = ormar.Float(nullable=True)
    ct_mean:float = ormar.Float(nullable=True)
    ct_min:float = ormar.Float(nullable=True)

    device = ormar.ForeignKey(Device, index=True, nullable=False,ondelete="CASCADE")
    aoi_measure:int = ormar.ForeignKey(Aoi_measure, index=True, nullable=False,ondelete="CASCADE")
    # created_date:datetime = ormar.DateTime(default=get_ntz_now,timezone=True)

class Error_featur(ormar.Model):
    class Meta(MainMeta):
        tablename="error_feature"
    id:int = ormar.Integer(primary_key=True,autoincrement=True,nullable=False)
    date:datetime = ormar.DateTime(timezone=True)
    device = ormar.ForeignKey(Device, index=True, nullable=False)
    event = ormar.ForeignKey(ProjectEvent,index=True,nullable=False,ondelete="CASCADE")
    category = ormar.Integer(nullable=True)
    operation_day:bool=ormar.Boolean(default=False)
    happend:int = ormar.Integer(nullable=True)
    dur_max:int = ormar.Integer(nullable=True)
    dur_mean:float = ormar.Float(nullable=True)
    dur_min:int = ormar.Integer(nullable=True)
    last_time_max:int = ormar.Integer(nullable=True)
    last_time_min:int = ormar.Integer(nullable=True)


# class Device(ormar.Model):
#     class Meta(MainMeta):
#         tablename = "devices"

#     id: str = ormar.String(max_length=100, primary_key=True, index=True)
#     project: str = ormar.String(max_length=50, nullable=False)
#     process: str = ormar.String(max_length=50, nullable=True)
#     line: int = ormar.Integer(nullable=True)
#     device_name: str = ormar.String(max_length=20, nullable=False)
#     device_cname: str = ormar.String(max_length=100, nullable=True)
#     x_axis: float = ormar.Float(nullable=False)
#     y_axis: float = ormar.Float(nullable=False)
#     is_rescue: bool = ormar.Boolean(default=False)
#     flag:bool = ormar.Boolean(default=False)
#     workshop: FactoryMap = ormar.ForeignKey(FactoryMap, index=True, nullable=False)
#     sop_link: str = ormar.String(max_length=128, nullable=True)
#     created_date: datetime = ormar.DateTime(default=get_ntz_now, timezone=True)
#     updated_date: datetime = ormar.DateTime(default=get_ntz_now, timezone=True)
#     def Device_flag_fetch():
#         return Device.objects.fielter(flag=True)


# class UserDeviceLevel(ormar.Model):
#     class Meta(MainMeta):
#         tablename = "user_device_levels"
#         constraints = [ormar.UniqueColumns("device", "user")]

#     id: int = ormar.Integer(primary_key=True, index=True)
#     user: User = ormar.ForeignKey(
#         User, index=True,
#         ondelete="CASCADE",
#         related_name="device_levels"
#     )
#     device: Device = ormar.ForeignKey(Device, index=True, ondelete="CASCADE")
#     level: int = ormar.SmallInteger(minimum=0, default=0)
#     created_date: datetime = ormar.DateTime(default=get_ntz_now, timezone=True)
#     updated_date: datetime = ormar.DateTime(default=get_ntz_now, timezone=True)


# class MissionEvent(ormar.Model):
#     class Meta(MainMeta):
#         tablename = "mission_events"
#         constraints = [ormar.UniqueColumns(
#             "event_id", "table_name", "mission")]

#     id: int = ormar.Integer(primary_key=True)

#     mission: MissionRef = ormar.ForeignKey(
#         MissionRef,
#         index=True,
#         ondelete="CASCADE",
#         related_name="events"
#     )

#     event_id: int = ormar.Integer(nullable=False)
#     category: int = ormar.Integer(nullable=False)
#     message: str = ormar.String(max_length=100, nullable=True)
#     host: str = ormar.String(max_length=50, nullable=False)
#     table_name: str = ormar.String(max_length=50, nullable=False)
#     event_beg_date: datetime = ormar.DateTime(nullable=True)
#     event_end_date: datetime = ormar.DateTime(nullable=True)
#     created_date: datetime = ormar.DateTime(default=get_ntz_now, timezone=True)
#     updated_date: datetime = ormar.DateTime(default=get_ntz_now, timezone=True)


# class Mission(ormar.Model):

#     class Meta(MainMeta):
#         tablename = "missions"

#     id: int = ormar.Integer(primary_key=True, index=True)
#     name: str = ormar.String(max_length=100, nullable=False)
#     device: Device = ormar.ForeignKey(Device, ondelete="CASCADE", nullable=False)
#     worker: User = ormar.ForeignKey(User, ondelete="SET NULL", related_name="assigned_missions", nullable=True)
#     rejections: Optional[List[User]] = ormar.ManyToMany(User, related_name="rejected_missions")
#     description: str = ormar.String(max_length=256, nullable=False)

#     is_done: bool = ormar.Boolean(default=False, nullable=True)
#     is_done_cure: bool = ormar.Boolean(default=False, nullable=True)
#     # if mission complete due to shifting
#     is_done_shift: bool = ormar.Boolean(default=False, nullable=True)
#     is_done_cancel: bool = ormar.Boolean(default=False, nullable=True)
#     is_done_finish: bool = ormar.Boolean(default=False, nullable=True)

#     # if no worker could be assigned
#     is_lonely: bool = ormar.Boolean(default=False, nullable=True)
#     is_emergency: bool = ormar.Boolean(default=False, nullable=True)

#     overtime_level: int = ormar.Integer(default=0, nullable=True)

#     notify_send_date: datetime = ormar.DateTime(nullable=True)
#     notify_recv_date: datetime = ormar.DateTime(nullable=True)

#     accept_recv_date: datetime = ormar.DateTime(nullable=True)

#     repair_beg_date: datetime = ormar.DateTime(nullable=True)
#     repair_end_date: datetime = ormar.DateTime(nullable=True)

#     created_date: datetime = ormar.DateTime(default=get_ntz_now, timezone=True)
#     updated_date: datetime = ormar.DateTime(default=get_ntz_now, timezone=True)

#     @property_field
#     def mission_duration(self) -> timedelta:
#         if self.repair_end_date:
#             return self.repair_end_date - self.created_date
#         else:
#             return get_ntz_now() - self.created_date

#     @property_field
#     def repair_duration(self) -> Optional[timedelta]:
#         if self.repair_beg_date is not None:
#             if self.repair_end_date is not None:
#                 return self.repair_end_date - self.repair_beg_date
#             else:
#                 return get_ntz_now() - self.repair_beg_date
#         else:
#             return None

#     @property_field
#     def assign_duration(self) -> Optional[timedelta]:
#         if self.notify_send_date is not None:
#             if self.repair_beg_date is not None:
#                 return self.repair_beg_date - self.notify_send_date
#             else:
#                 return get_ntz_now() - self.notify_send_date
#         else:
#             return None

#     @property_field
#     def accept_duration(self) -> Optional[timedelta]:
#         if self.notify_send_date is not None:
#             if self.accept_recv_date is not None:
#                 return self.accept_recv_date - self.notify_send_date
#             else:
#                 return get_ntz_now() - self.notify_send_date
#         else:
#             return None

#     @property_field
#     def is_accepted(self) -> bool:
#         return self.accept_recv_date is not None

#     @property_field
#     def is_started(self) -> bool:
#         return self.repair_beg_date is not None

#     @property_field
#     def is_closed(self) -> bool:
#         return not self.repair_end_date == None or self.is_done


class AuditLogHeader(ormar.Model):

    class Meta(MainMeta):
        tablename = "audit_log_headers"

    id: int = ormar.Integer(primary_key=True, index=True)
    action: str = ormar.String(
        max_length=50, nullable=False, index=True, choices=list(AuditActionEnum)
    )
    user: str = ormar.String(max_length=30, index=True, nullable=True)
    created_date: datetime = ormar.DateTime(default=get_ntz_now, timezone=True)
    description: str = ormar.String(max_length=256, nullable=True)


# class WhitelistDevice(ormar.Model):

#     class Meta(MainMeta):
#         tablename = "whitelist_devices"

#     id: int = ormar.Integer(primary_key=True)
#     device: Device = ormar.ForeignKey(
#         Device, unique=True, ondelete='CASCADE', nullable=False)
#     workers: List[User] = ormar.ManyToMany(User, related_name="whitelist_devices")
#     created_date: datetime = ormar.DateTime(default=get_ntz_now, timezone=True)
#     updated_date: datetime = ormar.DateTime(default=get_ntz_now, timezone=True)

ProjectUser.update_forward_refs()
ProjectEvent.update_forward_refs()
User.update_forward_refs()


def unset_nullables(obj, model):
    if (isinstance(obj, model)):
        obj = model(
            **{
                k: v
                for k, v in obj.dict().items()
                if (
                    k in model.__fields__ and (
                        k == obj.pk_column.name or
                        model.__fields__[k].required
                    )

                )
            }
        )
    return obj


@pre_update([User])
async def before_update(sender, instance, **kwargs):
    instance.updated_date = get_ntz_now()
