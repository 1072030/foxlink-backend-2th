"""
主要適用於取得Log資訊
"""
import asyncio
from fastapi import APIRouter, Depends, HTTPException
import datetime
from typing import List
from pydantic import BaseModel
from app.core.database import AuditActionEnum, AuditLogHeader, User,Project
from typing import Optional
from app.services.log import convert_project_name
from app.services.auth import get_manager_active_user
from datetime import timedelta
router = APIRouter(prefix="/logs")


# class LogValueOut(BaseModel):
#     field: str
#     previous_value: str
#     new_value: str

#     @classmethod
#     def from_logvalue(cls, logvalue):
#         return cls(
#             field=logvalue.field_name,
#             previous_value=logvalue.previous_value,
#             new_value=logvalue.new_value,
#         )

# log 接收格式
class LogOut(BaseModel):
    id: int
    action: AuditActionEnum
    # table_name: str
    # record_pk: Optional[str]
    # values: List[LogValueOut]
    badge: Optional[str]
    username: Optional[str]
    description: Optional[str]
    project: Optional[str]
    created_date: datetime.datetime

# log 回傳格式
class LogResponse(BaseModel):
    logs: List[LogOut]
    page: int  # current page
    limit: int  # current page limit
    total: int  # total amount of logs

"""
action : 依照AuditActionEnum類別接收
limit : 預設一頁顯示內容
page : 預設顯示頁數
badge : 員工工號
username : 員工姓名
projectName : 專案名稱
start_date : 起始日期
end_date : 結束日期
user : 一般用於確認操作者是誰
"""
@router.get("/", response_model=LogResponse, tags=["logs"])
async def get_logs(
    action: Optional[AuditActionEnum] = None,
    limit: int = 20,
    page: int = 1,
    badge: Optional[str] = None,
    username: Optional[str] = None,
    projectName: Optional[str] = None,
    start_date: Optional[datetime.datetime] = None,
    end_date: Optional[datetime.datetime] = None,
    user: User = Depends(get_manager_active_user),
):
    
    if limit <= 0:
        raise HTTPException(400, "limit must be greater than 0")

    if page <= 0:
        raise HTTPException(400, "page must be greater than 0")

    params = {
        "created_date__gte": start_date,
        "created_date__lte": end_date.replace(hour=23,minute=59,second=59),
        "user__badge": badge,
        "user__username": username
    }

    if projectName is not None:
        projectName = projectName.upper()
        project = await Project.objects.filter(name=projectName).get_or_none()
        params["project"] = project.id

    if action is not None:
        params["action"] = action.value  # type: ignore

    params = {k: v for k, v in params.items() if v is not None}
    logs = await AuditLogHeader.objects.select_all().filter(**params).paginate(page, limit).order_by("-created_date").all()  # type: ignore

    # type: ignore
    total_count = await AuditLogHeader.objects.filter(**params).count()
    # print(logs)
    return LogResponse(
        page=page,
        limit=limit,
        total=total_count,
        logs=[
            LogOut(
                id=log.id,
                action=log.action,
                badge=log.user.badge,
                username=log.user.username,
                # user=log.user if log.user is not None else None,
                project =await convert_project_name(log.project),
                description=log.description,
                created_date=(log.created_date + timedelta(hours=8)).strftime('%Y-%m-%d %H:%M:%S'),
            )
            for log in logs
        ],
    )
