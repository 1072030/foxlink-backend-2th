"""
派工使用，預知保養無用
"""
# from typing import Optional
# from datetime import datetime
# from pydantic import BaseModel
# from app.env import DEBUG,FOXLINK_EVENT_DB_TABLE_POSTFIX

# class FoxlinkEvent(BaseModel):
#     id: int
#     project: str
#     line: str
#     device_name: str
#     category: int
#     start_time: datetime
#     end_time: Optional[datetime]
#     message: Optional[str]
#     start_file_name: Optional[str]
#     end_file_name: Optional[str]

#     @classmethod
#     def from_raw_event(cls,raw_event,table_name=""):
#         return cls(
#             id=raw_event[0],
#             project=(
#                 raw_event[9]
#                 if DEBUG else
#                 table_name[:-len(FOXLINK_EVENT_DB_TABLE_POSTFIX)].upper()
#             ),
#             line=raw_event[1],
#             device_name=raw_event[2],
#             category=raw_event[3],
#             start_time=raw_event[4],
#             end_time=raw_event[5],
#             message=raw_event[6],
#             start_file_name=raw_event[7],
#             end_file_name=raw_event[8]
#         )