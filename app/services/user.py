import asyncio
from datetime import datetime, timedelta
from typing import List, Optional, Tuple
import aiohttp
import requests
from fastapi.exceptions import HTTPException
from ormar import NoMatch, or_, and_
from app.env import (
    TIMEZONE_OFFSET,
    WEEK_START,
    PWD_SCHEMA,
    PWD_SALT
)
from app.models.schema import (
    UserCreate,
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

# 取得user資料
async def check_users(user_id:str):
    user = await User.objects.filter(badge = user_id).get_or_none()
    return user


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

async def userupdate():
    url = 'http://172.168.1.242/auth_test/server/server.php'
    myobj = {
            "type":'searchUserBySystem',
            "system": 16
    }
    response = requests.post(url, data=myobj)
    foxlink = response.json()
    foxlink = foxlink.get("data", [])
    bulk_create_user: List[User] = []
    users = await User.objects.all()
    
    for foxlink_user in foxlink:
        user_create = True

        for loc_user in users:
            if foxlink_user["user_id"] == loc_user.badge:
                user_create = False
                if foxlink_user["mail"] != loc_user.email:
                    badge = foxlink_user["user_id"]
                    mail = foxlink_user["mail"]
                    await User.objects.filter(badge=badge).update(email=mail,flag = 1)
                break

        if user_create is True:
            user= User(
                badge=foxlink_user['user_id'],
                username=foxlink_user['user_name'],
                flag=1,
                level = 1
            )
            bulk_create_user.append(user)
    if bulk_create_user:
        await User.objects.bulk_create(bulk_create_user)

    for loc_user in users:
        lock_user = True
        for foxlink_user in foxlink:
            if foxlink_user["user_id"] == loc_user.badge:
                lock_user = False
                break
        if lock_user is True:
            await User.objects.filter(badge=loc_user.badge).update(flag=0)
    return 



# async def delete_user_by_badge(badge: str):
#     affected_row = await User.objects.delete(badge=badge)

#     if affected_row != 1:
#         raise HTTPException(
#             status_code=404, detail="user by this id is not found")
