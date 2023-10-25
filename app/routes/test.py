from datetime import datetime
from typing import List, Optional
from fastapi import APIRouter, Depends ,Response
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
    get_manager_active_user,
    verify_password,
    get_admin_active_user,
)


router = APIRouter(prefix="/test")

@router.get("/", tags=["test"])
async def getUser():
    return await User.objects.all()

@router.post("/", tags=["test"])
async def NewUser(user_id:str,user_name:str):
    return await User.objects.create(badge=user_id,username=user_name)