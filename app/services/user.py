import asyncio
from datetime import datetime, timedelta
from typing import List, Optional, Tuple
import aiohttp
from fastapi.exceptions import HTTPException
from ormar import NoMatch, or_, and_
from app.env import (
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
    UserLevel,
    WorkerStatusEnum,
    api_db,
)


pwd_context = CryptContext(schemes=[PWD_SCHEMA], deprecated="auto")


async def get_users() -> List[User]:
    # need flag
    return await User.objects().all()


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
