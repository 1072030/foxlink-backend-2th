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
    getFoxlinkUser
)

router = APIRouter(prefix="/users")


@router.get("/foxlink", tags=["users"])
async def get_foxlink_user(user_id: str, system_id: str):
    """
    暫時無功能
    """
    return await getFoxlinkUser(user_id, system_id)

