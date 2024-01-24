"""
保存dto的地方
"""
from enum import Enum
from typing import Any, Dict, Optional, List
from pydantic import BaseModel
from datetime import datetime, date, timedelta, time
from app.core.database import (
    UserLevel,
    WorkerStatusEnum,
)

# * User


class WorkerAttendance(BaseModel):
    date: date
    login_datetime: datetime
    logout_datetime: Optional[datetime]
    logout_reason: Optional[str]


class WorkerSummary(BaseModel):
    total_accepted_count_this_week: int
    total_accepted_count_this_month: int
    total_rejected_count_this_week: int
    total_rejected_count_this_month: int


class UserBase(BaseModel):
    badge: str
    username: str

class UserPedding(UserBase):
    password: str

class UserCreate(UserBase):
    confirmed:bool


class UserPatch(BaseModel):
    username: Optional[str]
    password: Optional[str]


class UserOut(UserBase):
    workshop: str
    change_pwd: bool


class UserOutWithWorkTimeAndSummary(BaseModel):
    badge: str
    username: str
    level: int
    workshop: Optional[str]
    change_pwd: bool
    at_device: str
    work_time: int
    summary: Optional[WorkerSummary]


class UserChangePassword(BaseModel):
    old_password: str
    new_password: str


class UserStatus(BaseModel):
    status: str
    work_type: str

class UserLoginFoxlink(BaseModel):
    type:str
    user_id:str
    password:str
    system:str

# * Mission


class MissionBase(BaseModel):
    description: Optional[str]


class MissionUpdate(MissionBase):
    name: Optional[str]
    assignees: Optional[List[str]]


class DeviceDto(BaseModel):
    device_id: str
    device_name: str
    device_cname: Optional[str]
    workshop: Optional[str]
    project: str
    process: Optional[str]
    line: Optional[int]


class UserNameDto(BaseModel):
    badge: str
    username: str


class WorkerStatusDto(BaseModel):
    worker_id: str
    worker_name: str
    finish_event_date: datetime
    at_device: Optional[str]
    at_device_cname: Optional[str]
    status: WorkerStatusEnum
    total_dispatches: int
    mission_duration: Optional[float]
    repair_duration: Optional[float]


class WorkerStatus(BaseModel):
    status: str

class NewProjectDto(BaseModel):
    project:str
    line:int
    device:str
    ename:str
    cname:str


class NewUserDto(BaseModel):
    project_id:int
    user_id:str
    permission:int



# class UserOverviewOut(BaseModel):
#     badge: str
#     username: str
#     workshop: Optional[str]
#     level: int
#     shift: Optional[ShiftType]
#     superior: Optional[str]
#     experiences: List[DeviceExp]


# class DayAndNightUserOverview(BaseModel):
#     day_shift: List[UserOverviewOut]
#     night_shift: List[UserOverviewOut]


# class DeviceOut(BaseModel):
#     id: str
#     project: str
#     process: Optional[str]
#     line: Optional[int]
#     device_name: str
#     device_cname: Optional[str]
#     workshop: str
#     x_axis: float
#     y_axis: float
#     is_rescue: bool
#     sop_link: Optional[str]

#     @classmethod
#     def from_device(cls, device: Device):
#         return cls(
#             id=device.id,
#             project=device.project,
#             process=device.process,
#             line=device.line,
#             device_name=device.device_name,
#             device_cname=device.device_cname,
#             workshop=device.workshop.name,
#             sop_link=device.sop_link,
#             x_axis=device.x_axis,
#             y_axis=device.y_axis,
#             is_rescue=device.is_rescue,
#         )


# class CategoryPriorityDeviceInfo(BaseModel):
#     device_id: str
#     project: str
#     line: int
#     device_name: str


# class CategoryPriorityOut(BaseModel):
#     category: int
#     priority: int
#     message: str
#     devices: List[CategoryPriorityDeviceInfo]

#     @classmethod
#     def from_categorypri(cls, pri: CategoryPRI):
#         obj = cls(
#             category=pri.category,
#             priority=pri.priority,
#             message=pri.message,
#             devices=[],
#         )

#         if pri.devices is not None:
#             obj.devices = [
#                 CategoryPriorityDeviceInfo(
#                     device_id=x.id,
#                     project=x.project,
#                     line=x.line,
#                     device_name=x.device_name,
#                 )
#                 for x in pri.devices
#                 if pri.devices is not None
#             ]

#         return obj


class WorkerMissionStats(BaseModel):
    badge: str
    username: str
    count: int


class DeviceStatusEnum(Enum):
    working = 0
    repairing = 1
    halt = 2


class DeviceStatus(BaseModel):
    device_id: str
    x_axis: float
    y_axis: float
    status: DeviceStatusEnum


class WhitelistRecommendDevice(BaseModel):
    day: Dict[str, int]
    night: Dict[str, int]


class DeviceDispatchableWorker(BaseModel):
    badge: str
    username: str


class ShiftDto(BaseModel):
    id: str
    shift_beg_time: time
    shift_end_time: time
