"""
主要是和登入的認證與權限有關
"""
import asyncio
from fastapi import APIRouter, Depends
from pydantic import BaseModel
from fastapi.security import OAuth2PasswordRequestForm
from app.services.auth import authenticate_user, create_access_token,get_current_user
from app.services.user import check_users
from datetime import timedelta
from app.core.database import (
    transaction,
    User,
    AuditLogHeader,
    AuditActionEnum,
)
from app.core.database import get_ntz_now
from app.utils.utils import AsyncEmitter, BenignObj


class Token(BaseModel):
    access_token: str
    permission:int
    token_type: str

# TOKEN 過期時間
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24

router = APIRouter(prefix="/auth", tags=["auth"])

# 使用者登入
@router.post("/token", response_model=Token, responses={401: {"description": "Invalid username/password"}})
async def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends()):
    """
    使用者登入
    """
    log_in = await login_routine(form_data)
    return log_in
# 取得使用者的權限
@router.get("/permission")
async def login_for_permission(user_id:str = None,user: User = Depends(get_current_user())):
    user = await check_users(user_id)
    level = user.level
    return level

# transaction的用意是在交付一致性
@transaction(callback=True)
async def login_routine(form_data, handler=[], checkFoxlink:bool = True):
    # 查詢使用者是否存在於本地端資料庫中
    user = await authenticate_user(form_data.username)
    # 製作 token
    access_token = create_access_token(
        data={
            "sub": user.badge,
            "UUID": form_data.client_id
        },
        expires_delta=timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    # dict格式
    changes = BenignObj()
    # 同步一致性
    emitter = AsyncEmitter()

    changes.current_UUID = form_data.client_id
    changes.login_date = get_ntz_now()
    # 新增員工登入log
    emitter.add(
        AuditLogHeader.objects.create(
            action=AuditActionEnum.USER_LOGIN.value,
            user=user.badge,
        )
    )
    # 將修改的資料暫存
    emitter.add(
        user.update(
            **changes.query()
        )
    )
    # 一起進行修改或新增
    await emitter.emit()

    return {"access_token": access_token, "permission":user.level ,"token_type": "bearer"}


