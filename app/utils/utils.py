import pytz
import asyncio
import os,json
from pickle import TUPLE
from typing import Tuple
from fastapi import BackgroundTasks
from app.core.database import (
    get_ntz_now,
    # ShiftType,
    # Shift
)
from datetime import datetime, timedelta, time
from app.env import (
    TZ
)
def change_file_name(filename:str,position:str)->str:
    Readfile = open(os.getcwd()+'/filename.json','r',encoding="utf-8")
    data = json.load(Readfile)
    data[position] = filename
    Writefile = open(os.getcwd()+'/filename.json','w',encoding="utf-8")
    json.dump(data,Writefile,ensure_ascii=False)
    return data


# async def get_current_shift_details() -> Tuple[ShiftType, datetime, datetime]:
#     # 台灣時間
#     now = get_ntz_now().astimezone(TZ)
#     # 標準時間
#     now_time = now.time()
#     # 換班時間
#     shifts = await Shift.objects.all()
#     for shift in shifts:
#         # 台灣時間
#         tz_now = now.astimezone(TZ)

#         # due to the timezone specification problem,
#         # which is the timezone for shift time is set to TZ,
#         # but the system uses datetime without timezones,
#         # therefore need to convert the time setting from shift to non-timezoned format
#         period_beg = (
#             tz_now
#             .replace(
#                 hour=shift.shift_beg_time.hour,
#                 minute=shift.shift_beg_time.minute,
#                 second=0
#             )
#             .astimezone(None)
#             .replace(tzinfo=None)
#         )

#         period_end = (
#             tz_now
#             .replace(
#                 hour=shift.shift_end_time.hour,
#                 minute=shift.shift_end_time.minute,
#                 second=0
#             )
#             .astimezone(None)
#             .replace(tzinfo=None)
#         )
#         shift_type = ShiftType(shift.id)
#         # 晚班 time.max = 23:59:59.999999
#         if shift.shift_beg_time > shift.shift_end_time:
#             if (now_time > shift.shift_beg_time and now_time < time.max):
#                 return (
#                     shift_type,
#                     period_beg,
#                     period_end + timedelta(days=1)
#                 )
#             elif(now_time < shift.shift_end_time):
#                 return (
#                     shift_type,
#                     period_beg - timedelta(days=1),
#                     period_end
#                 )

#         else:
#             # 日班
#             if (now_time > shift.shift_beg_time and now_time < shift.shift_end_time):
#                 return (
#                     shift_type,
#                     period_beg,
#                     period_end
#                 )


# async def get_current_shift_type() -> (ShiftType):
#     return (await get_current_shift_details())[0]


# async def get_current_shift_time_interval() -> Tuple[datetime, datetime]:
#     shift_type = await get_current_shift_type()
#     now_time = get_ntz_now()

#     day_begin = datetime.strptime(DAY_SHIFT_BEGIN, "%H:%M")
#     day_end = datetime.strptime(DAY_SHIFT_END, "%H:%M")

#     if shift_type == ShiftType.day:
#         shift_start = now_time.replace(hour=day_begin.hour, minute=day_begin.minute, second=0)
#         shift_end = now_time.replace(hour=day_end.hour, minute=day_end.minute, second=0)
#     else:
#         shift_start = now_time.replace(hour=day_end.hour, minute=day_end.minute, second=1)
#         shift_end = now_time.replace(hour=day_begin.hour, minute=day_begin.minute, second=59)
#         shift_end -= timedelta(minutes=1)

#         if now_time.time() < day_begin.time():
#             shift_start -= timedelta(days=1)
#         elif now_time.time() >= day_end.time():
#             shift_end += timedelta(days=1)

#     return shift_start.astimezone(pytz.utc), shift_end.astimezone(pytz.utc)


# def get_previous_shift_time_interval():
#     now_time = get_ntz_now()

#     day_begin = datetime.strptime(DAY_SHIFT_BEGIN, "%H:%M")
#     day_end = datetime.strptime(DAY_SHIFT_END, "%H:%M")

#     day_shift_start = now_time.replace(hour=day_begin.hour, minute=day_begin.minute, second=0)
#     day_shift_end = now_time.replace(hour=day_end.hour, minute=day_end.minute, second=0)

#     # if now_time.time() < day_end.time():
#     #     day_shift_start -= timedelta(days=1)
#     #     day_shift_end -= timedelta(days=1)

#     night_shift_start = now_time.replace(hour=day_end.hour, minute=day_end.minute, second=1)
#     night_shift_end = now_time.replace(hour=day_begin.hour, minute=day_begin.minute, second=59)

#     if now_time.time() < night_shift_end.time():
#         night_shift_end -= timedelta(days=1)
#         night_shift_start -= timedelta(days=2)
#     else:
#         night_shift_start -= timedelta(days=1)

#     return day_shift_start.astimezone(pytz.utc), day_shift_end.astimezone(pytz.utc), night_shift_start.astimezone(pytz.utc), night_shift_end.astimezone(pytz.utc)


class BenignObj(object):
    def query(self):
        result = self.__dict__
        result["_columns"] = [key for key in self.__dict__.keys()]
        return result

# 這我也不知道幹嘛的 應該是處理多個同時執行
class AsyncEmitter:
    def __init__(self):
        self.jobs = []

    def add(self, *coroutines):
        self.jobs += coroutines

    async def emit(self):
        return await asyncio.gather(
            *self.jobs
        )


class DTO:
    def __init__(self, in_dict):
        for key, val in in_dict.items():
            if (isinstance(val, (list, tuple))):
                setattr(self, key, [DTO(x) if isinstance(x, dict)else x for x in val])
            else:
                setattr(self, key, DTO(val) if isinstance(val, dict) else val)


# def time_within_period(at: time, beg: time,end: time):
#     if beg > end:
#         if(at > beg or at < end):
#             return True
#     else:
#         if(at > beg and at < end):
#             return True

# async def check_date_in_current_shift(date: datetime,shift: ShiftType):
#     now = get_ntz_now()
#     shift = await Shift.objects.filter(shift.value).get_or_none()
#     return time_within_period(
#         time(hour=date.hour,minute=date.minute),
#         shift.shift_beg_time,
#         shift.shift_end_time
#     )
