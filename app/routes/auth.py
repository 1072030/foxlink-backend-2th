"""
主要是和登入的認證與權限有關
"""
import asyncio
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from fastapi.security import OAuth2PasswordRequestForm
from app.services.auth import authenticate_user, create_access_token,checkFoxlinkAuth,getFoxlinkUser,get_current_user,searchUserBySystem
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

@router.get("/user")
async def user():
    bulk_create_user: List[User] = []
    users = await User.objects.all()

    foxlink = searchUserBySystem()
    foxlink = foxlink.get("data", [])
    
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

    return users

# # transaction的用意是在交付一致性
@transaction(callback=True)
async def login_routine(form_data, handler=[], checkFoxlink:bool = True):
    # 查詢使用者是否存在於本地端資料庫中
    user = await authenticate_user(form_data.username)
    # 製作 token
    flag = user.flag
    if flag == False:
        raise HTTPException(
            status_code=400, detail="user doesnt exist in foxlink dbs."
        )
    else:
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


# # 打開
# # transaction的用意是在交付一致性
# # 全有全無律
# @transaction(callback=True)
# async def login_routine(form_data, handler=[], checkFoxlink:bool = True):
    
    
#     foxlink = await checkFoxlinkAuth(type="login",user_id=form_data.username,user_password=form_data.password,system="16")
#     user = await authenticate_user(form_data.username)
#     print(user)
#     print(foxlink)
#     if foxlink['data']['code'] == 1:

#         if user is None:
#             await User.objects.create(
#                 badge=foxlink['data']['data']['user_id'],
#                 username=foxlink['data']['data']['user_name'],
#                 current_UUID=form_data.client_id,
#                 flag=1,
#                 level = 1
#             )
#             user = await authenticate_user(form_data.username)
#             print(user)

#             await AuditLogHeader.objects.create(
#                 action=AuditActionEnum.USER_LOGIN.value,
#                 user=user.badge
#             )

#         else:
#             flag = user.flag
#             if flag == True:
#                 changes = BenignObj()
#                 emitter = AsyncEmitter()

#                 changes.current_UUID = form_data.client_id
#                 changes.login_date = get_ntz_now()

#                 emitter.add(
#                     AuditLogHeader.objects.create(
#                         action=AuditActionEnum.USER_LOGIN.value,
#                         user=user.badge,
#                     )
#                 )

#                 emitter.add(
#                     user.update(
#                         **changes.query()
#                     )
#                 )

#                 await emitter.emit()

#             else:
#                 raise HTTPException(
#             status_code=400, detail="user doesnt exist in foxlink dbs."
#         )
#     else:
#        raise HTTPException(
#             status_code=400, detail="user doesnt exist in foxlink dbs."
#         )

#     access_token = create_access_token(
#         data={
#             "sub": user.badge,
#             "UUID": form_data.client_id
#         },
#         expires_delta=timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
#     )

#     return {"access_token": access_token, "permission":user.level ,"token_type": "bearer"}


