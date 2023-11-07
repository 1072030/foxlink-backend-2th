"""
儲存資料庫中的環境變數
"""
import logging
import shutil
from app.log import LOGGER_NAME
from fastapi import APIRouter, Depends,Response
from app.services.auth import get_manager_active_user
from app.core.database import Env
from app.core.database import (User,Env,EnvEnum)
from fastapi import HTTPException, status as HTTPStatus
router = APIRouter(prefix="/system", tags=["system"])
# logger = logging.getLogger(LOGGER_NAME)


@router.get("/space")
async def space_statistic(user: User = Depends(get_manager_active_user)) -> str:
    total, used, _ = shutil.disk_usage("/")
    return used/total
# @router.get("/env-get-settings/{key}")
# async def get_auto_rescue(key:str = None,user: User = Depends(get_manager_active_user)):
#     get_env = await Env.objects.filter(key=key).get_or_none()
#     if get_env is None:
#         raise HTTPException(
#             status_code=400, detail="can't find the env key data"
#         )
#     return get_env

# @router.post("/env-update-settings/{key}")
# async def update_env(key:str = None,value:str=None,user: User = Depends(get_manager_active_user)):
#     if key is None:
#         raise HTTPException(
#             status_code=400, detail="no env key input"
#         )
#     if value is None:
#         raise HTTPException(
#             status_code=400, detail="no env value input"
#         )
#     get_env = await Env.objects.filter(
#         key=key
#     ).get_or_none()
#     if get_env is None:
#         raise HTTPException(
#             status_code=400, detail="can't find the env key"
#         )
#     try:
#         await Env.objects.filter(
#             key=get_env.key
#         ).update(
#             value= value
#         )
#         return {
#             "key":key,
#             "value":value
#         }
#     except:
#         raise HTTPException(400, 'cannot update env data')
