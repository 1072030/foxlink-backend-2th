"""
與員工相關
"""
from fastapi import APIRouter, Depends
from fastapi.exceptions import HTTPException
from datetime import timedelta
from app.core.database import (
    get_ntz_now,
    AuditActionEnum,
    LogoutReasonEnum,
    User,
    UserLevel,
    WorkerStatusEnum,
    AuditLogHeader,
    api_db,
    transaction
)
from app.services.auth import (
    get_current_user,
    getFoxlinkUser,
)
from app.services.user import(check_users)

router = APIRouter(prefix="/users")


@router.get("/foxlink", tags=["users"])
async def get_foxlink_user(user_id: str, system_id: int = 16):
    """
    確認人員是否在User表中
    """
    # user = await check_users(user_id)
    # if user is None:
    #     raise HTTPException(400,"User not found")
    # return user.username
    # 打開
    return await getFoxlinkUser(user_id, system_id)

