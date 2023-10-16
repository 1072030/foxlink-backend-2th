import asyncio
from datetime import datetime, timedelta
from typing import List, Optional, Tuple
import aiohttp
from fastapi.exceptions import HTTPException
from ormar import NoMatch, or_, and_
from app.env import (
    EMQX_PASSWORD,
    EMQX_USERNAME,
    MQTT_BROKER,
    TIMEZONE_OFFSET,
    WEEK_START,
    PWD_SCHEMA,
    PWD_SALT
)
from app.models.schema import (
    # DayAndNightUserOverview,
    DeviceExp,
    UserCreate,
    # UserOverviewOut,
    WorkerAttendance,
    WorkerStatusDto,
    WorkerStatus,
    WorkerSummary,
    UserPedding
)
from passlib.context import CryptContext
from app.core.database import (
    get_ntz_now,
    AuditActionEnum,
    AuditLogHeader,
    User,
    PendingApproval,
    UserLevel,
    WorkerStatusEnum,
    api_db,
)


pwd_context = CryptContext(schemes=[PWD_SCHEMA], deprecated="auto")


def get_password_hash(password: str):
    return pwd_context.hash(password, salt=PWD_SALT, rounds=10000)


async def get_users() -> List[User]:
    # need flag
    return await User.objects().all()


async def add_pending_user(dto: UserPedding) -> User:
    if dto.password is None or dto.password == "":
        raise HTTPException(
            status_code=400, detail="password can not be empty")

    pw_hash = get_password_hash(dto.password)

    new_dto = dto.dict()
    del new_dto["password"]
    new_dto["password_hash"] = pw_hash

    user_duplicate = await User.objects.filter(badge=new_dto["badge"]).get_or_none()
    approvals_duplicate = await PendingApproval.objects.filter(badge=new_dto["badge"]).get_or_none()
    if approvals_duplicate is not None or user_duplicate is not None:
        raise HTTPException(
            status_code=400, detail="User account already exist")

    if dto.badge is None or dto.badge == "":
        raise HTTPException(
            status_code=400, detail="User account can not be empty")
    
    if dto.username is None or dto.username == "":
        raise HTTPException(
            status_code=400, detail="Username can not be empty")
    
    user = PendingApproval(
        badge=new_dto["badge"],
        username=new_dto["username"],
        password_hash=new_dto["password_hash"]
    )

    try:
        return await user.save()
    except Exception as e:
        raise HTTPException(
            status_code=400, detail="cannot add user:" + str(e))


async def get_worker_by_badge(
    badge,
    select_fields: List[str] = [
        "workshop",
        "superior",
        "at_device",
        "start_position"
    ]
) -> Optional[User]:
    worker = (
        # need flag
        await User.objects
        .filter(badge=badge)
        .get_or_none()
    )

    return worker


async def delete_user_by_badge(badge: str):
    affected_row = await User.objects.delete(badge=badge)

    if affected_row != 1:
        raise HTTPException(
            status_code=404, detail="user by this id is not found")
