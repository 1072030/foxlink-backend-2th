import requests
from fastapi import FastAPI
import logging
from jose.constants import ALGORITHMS
from jose.exceptions import ExpiredSignatureError
from app.core.database import (
    WorkerStatusEnum,
    get_ntz_now,
    User,
    Project,
    ProjectUser
)
from datetime import datetime, timedelta
from typing import Optional
from pydantic import BaseModel
from jose import jwt
from app.services.user import get_worker_by_badge, pwd_context, PWD_SCHEMA
from fastapi import Depends, HTTPException, status as HTTPStatus
from fastapi.security import OAuth2PasswordBearer
from app.env import (
    JWT_SECRET,
)
from app.core.database import UserLevel
from app.models.schema import (
    UserLoginFoxlink
)


oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/token")


class TokenData(BaseModel):
    badge: Optional[str] = None


def verify_password(user_hashed_password: str, db_hashed_password: str):
    return user_hashed_password == db_hashed_password


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    if expires_delta:
        expire = get_ntz_now() + expires_delta
    else:
        expire = get_ntz_now()
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, JWT_SECRET, algorithm=ALGORITHMS.HS256)
    return encoded_jwt


async def authenticate_user(badge: str, password: str):
    user = await get_worker_by_badge(badge, [])

    if user is None:
        return user

    if not verify_password(password, user.password_hash):
        raise HTTPException(
            status_code=HTTPStatus.HTTP_401_UNAUTHORIZED, detail="密码不正确"
        )

    return user


def get_current_user(light_user=False):
    async def driver(token: str = Depends(oauth2_scheme)):
        expired = False
        try:
            payload = jwt.decode(
                token,
                JWT_SECRET,
                algorithms=["HS256"]
            )
        except ExpiredSignatureError:
            payload = jwt.decode(
                token, 
                JWT_SECRET, 
                algorithms=['HS256'], 
                options={
                    "verify_exp": False,
                    "verify_signature": False
                }
            )
            expired= True

        badge: str = payload.get("sub")
        decode_UUID: str = payload.get("UUID")

        if badge is None:
            raise HTTPException(403, detail='无法验证凭据')

        user = await get_worker_by_badge(badge, [])

        if user is None:
            raise HTTPException(403, detail='无法验证凭据')

        if expired and decode_UUID == user.current_UUID:
            await user.update(current_UUID="0")
            raise HTTPException(403, detail='准证已过期')

        elif user.current_UUID != decode_UUID and user.current_UUID == '0':
            raise HTTPException(403, detail='系统重启，请重新登入')

        # elif user.current_UUID != decode_UUID and user.level == UserLevel.maintainer.value:
        #     raise HTTPException(403, detail='登录另一台设备，请登出')

        return user


    return driver

# 確認取得人員身份
async def get_admin_active_user(project_id:int,active_user: User = Depends(get_current_user())):
    project = await Project.objects.filter(project_id=project_id).get_or_none()
    if project is None:
        raise HTTPException(404, detail='project is not foound')
    project_user = await ProjectUser.objects.filter(
        project_id=project.id,
        user_id=active_user.badge
    ).get_or_none()
    if project_user is None:
        raise HTTPException(404, detail='this user didnt in the project')
    
    if not project_user.permission == UserLevel.admin.value:
        raise HTTPException(
            status_code=HTTPStatus.HTTP_403_FORBIDDEN, detail="Permission Denied"
        )
    # if not active_user.level == UserLevel.admin.value:
    #     raise HTTPException(
    #         status_code=HTTPStatus.HTTP_403_FORBIDDEN, detail="Permission Denied"
    #     )
    return active_user

# 確認取得人員身份
async def get_manager_active_user(
    manager_user: User = Depends(get_current_user()),
):
    if manager_user == "admin":
        raise HTTPException(
            status_code=HTTPStatus.HTTP_403_FORBIDDEN,
            detail="Permission Denied",
        )
    return manager_user


async def set_device_UUID(
    user: User, UUID: str
):
    await user.update(current_UUID=UUID)

async def authenticate_foxlink(dto:UserLoginFoxlink):
    # json_data = {"user" : MrMinty, "pass" : "password"} #json data
    # endpoint = "https://www.testsite.com/api/account_name/?access_token=1234567890" #endpoint
    # print(requests.post(endpoint, json=json_data). content)
    response = await requests.post()
    return

async def checkUserProjectPermission(project_id:int,user:User,permission:int):
    project = await Project.objects.filter(id=project_id).get_or_none()
    if project is None:
        raise HTTPException(404, detail='project is not foound')
    project_user = await ProjectUser.objects.filter(
        project_id=project.id,
        user_id=user.badge
    ).get_or_none()
    if project_user is None:
        raise HTTPException(404, detail='this user didnt in the project')
    
    if not project_user.permission == permission:
        raise HTTPException(
            status_code=HTTPStatus.HTTP_403_FORBIDDEN, detail="Permission Denied"
            )
    
    return user
