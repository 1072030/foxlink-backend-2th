"""
主要是和登入的認證與權限有關
"""
import asyncio
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from fastapi.security import OAuth2PasswordRequestForm
# from app.mqtt import mqtt_client
from app.services.auth import authenticate_user, create_access_token,checkFoxlinkAuth
from datetime import datetime, timedelta, timezone
from app.core.database import (
    transaction,
    api_db,
    User,
    AuditLogHeader,
    AuditActionEnum,
    UserLevel,
    WorkerStatusEnum
)
from app.core.database import get_ntz_now
from app.utils.utils import AsyncEmitter, BenignObj


class Token(BaseModel):
    access_token: str
    token_type: str


ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24

router = APIRouter(prefix="/auth", tags=["auth"])

# 使用者登入
@router.post("/token", response_model=Token, responses={401: {"description": "Invalid username/password"}})
async def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends()):
    return await login_routine(form_data)

# transaction的用意是在交付一致性
# 全有全無律
@transaction(callback=True)
async def login_routine(form_data, handler=[], checkFoxlink:bool = False):
    user = await authenticate_user(form_data.username, form_data.password)

    if checkFoxlink and user is not None:
        foxlink = await checkFoxlinkAuth(type="login",user_id=user.badge,password=form_data.password,system="001",checkSSH=True)
    elif(user is None):
        raise HTTPException(
            status_code=400, detail="user badge doesnt exist."
        )

    access_token = create_access_token(
        data={
            "sub": user.badge,
            "UUID": form_data.client_id
        },
        expires_delta=timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    )

    changes = BenignObj()
    emitter = AsyncEmitter()

    changes.current_UUID = form_data.client_id
    changes.login_date = get_ntz_now()

    emitter.add(
        AuditLogHeader.objects.create(
            action=AuditActionEnum.USER_LOGIN.value,
            user=user.badge,
        )
    )

    emitter.add(
        user.update(
            **changes.query()
        )
    )

    await emitter.emit()

    return {"access_token": access_token, "token_type": "bearer"}


