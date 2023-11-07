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


# class MissionEventOut(BaseModel):
#     category: int
#     message: str
#     event_beg_date: datetime
#     event_end_date: Optional[datetime]

#     @classmethod
#     def from_missionevent(cls, e: MissionEvent):
#         return cls(
#             category=e.category,
#             message=e.message,
#             event_beg_date=e.event_beg_date,
#             event_end_date=e.event_end_date,
#         )


# class MissionDto(BaseModel):
#     mission_id: int
#     device: DeviceDto
#     name: str
#     description: str
#     worker: Optional[UserNameDto]
#     events: List[MissionEventOut]
#     is_started: bool
#     is_closed: bool
#     is_done: bool
#     is_emergency: bool
#     is_done_cure: bool
#     created_date: datetime
#     updated_date: datetime
#     worker_now_position: str

#     @classmethod
#     def from_mission(cls, m: Mission):
#         return cls(
#             mission_id=m.id,
#             name=m.name,
#             device=DeviceDto(
#                 device_id=m.device.id,
#                 device_name=m.device.device_name,
#                 device_cname=m.device.device_cname,
#                 workshop=m.device.workshop.name,
#                 project=m.device.project,
#                 process=m.device.process,
#                 line=m.device.line,
#             ),
#             description=m.description,
#             worker_now_position="" if m.worker == None else m.worker.at_device.id,
#             # add worker now position
#             is_started=m.is_started,
#             is_closed=m.is_closed,
#             is_done=m.is_done,
#             is_done_cure=m.is_done_cure,
#             is_emergency=m.is_emergency,
#             worker=UserNameDto(
#                 badge=m.worker.badge,
#                 username=m.worker.username
#             ) if m.worker else None,
#             events=[MissionEventOut.from_missionevent(e) for e in m.events],
#             created_date=m.created_date,
#             updated_date=m.updated_date,
#         )


# class MissionInfo(BaseModel):
#     mission_id: int
#     device: DeviceDto
#     name: str
#     description: str
#     badge: str
#     events: List[MissionEventOut]
#     is_started: bool
#     is_closed: bool
#     is_done: bool
#     is_emergency: bool
#     created_date: datetime
#     updated_date: datetime
#     notify_receive_date: str
#     notify_send_date: str
#     worker_now_position: str

#     @classmethod
#     def from_mission(cls, m: Mission):
#         return cls(
#             mission_id=m.id,
#             name=m.name,
#             device=DeviceDto(
#                 device_id=m.device.id,
#                 device_name=m.device.device_name,
#                 device_cname=m.device.device_cname,
#                 workshop=m.device.workshop.name,
#                 project=m.device.project,
#                 process=m.device.process,
#                 line=m.device.line,
#             ),
#             description=m.description,
#             worker_now_position="" if m.worker.at_device.id == None else m.worker.at_device.id,
#             is_started=m.is_started,
#             is_closed=m.is_closed,
#             is_done=m.is_done,
#             is_emergency=m.is_emergency,
#             badge=m.worker.badge if m.worker else None,
#             events=[MissionEventOut.from_missionevent(e) for e in m.events],
#             created_date=m.created_date,
#             updated_date=m.updated_date,
#             notify_receive_date="2000-01-01 00:00:00" if m.notify_recv_date == None else str(
#                 m.notify_recv_date),
#             notify_send_date="2000-01-01 00:00:00" if m.notify_send_date == None else str(
#                 m.notify_send_date)
#         )


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


class ImportDevicesOut(BaseModel):
    device_ids: List[str]
    parameter: Optional[str]


class DeviceExp(BaseModel):
    project: str
    process: Optional[str]
    device_name: str
    line: int
    exp: int

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
