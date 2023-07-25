import asyncio
from fastapi import APIRouter, Depends, HTTPException
import datetime
from typing import List
from pydantic import BaseModel
from app.core.database import AuditActionEnum, AuditLogHeader, User
from typing import Optional

from app.services.auth import get_manager_active_user

router = APIRouter(prefix="/logs")


class LogValueOut(BaseModel):
    field: str
    previous_value: str
    new_value: str

    @classmethod
    def from_logvalue(cls, logvalue):
        return cls(
            field=logvalue.field_name,
            previous_value=logvalue.previous_value,
            new_value=logvalue.new_value,
        )


class LogOut(BaseModel):
    id: int
    action: AuditActionEnum
    table_name: str
    record_pk: Optional[str]
    values: List[LogValueOut]
    badge: Optional[str]
    description: Optional[str]
    created_date: datetime.datetime


class LogResponse(BaseModel):
    logs: List[LogOut]
    page: int  # current page
    limit: int  # current page limit
    total: int  # total amount of logs


@router.get("/", response_model=LogResponse, tags=["logs"])
async def get_logs(
    action: Optional[AuditActionEnum] = None,
    limit: int = 20,
    page: int = 1,
    start_date: Optional[datetime.datetime] = None,
    badge: Optional[str] = None,
    end_date: Optional[datetime.datetime] = None,
    user: User = Depends(get_manager_active_user),
):
    if limit <= 0:
        raise HTTPException(400, "limit must be greater than 0")

    if page <= 0:
        raise HTTPException(400, "page must be greater than 0")

    params = {
        "created_date__gte": start_date,
        "created_date__lte": end_date,
        "user__badge": badge,
    }

    if action is not None:
        params["action"] = action.value  # type: ignore

    params = {k: v for k, v in params.items() if v is not None}

    logs = await AuditLogHeader.objects.filter(**params).select_all().paginate(page, limit).order_by("-created_date").all()  # type: ignore
    total_count = await AuditLogHeader.objects.filter(**params).count()  # type: ignore

    return LogResponse(
        page=page,
        limit=limit,
        total=total_count,
        logs=[
            LogOut(
                id=log.id,
                action=log.action,
                table_name=log.table_name,
                record_pk=log.record_pk,
                values=[LogValueOut.from_logvalue(v) for v in log.logvalues],
                badge=log.user.badge if log.user is not None else None,
                description=log.description,
                created_date=log.created_date,
            )
            for log in logs
        ],
    )
