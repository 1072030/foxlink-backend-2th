"""
儲存資料庫中的環境變數
"""
import shutil
import json
from fastapi import APIRouter, Depends
from app.services.auth import get_manager_active_user
from app.core.database import Env
from app.core.database import (User, Env)
from fastapi import HTTPException
router = APIRouter(prefix="/system", tags=["system"])
# logger = logging.getLogger(LOGGER_NAME)


@router.get("/space")
async def space_statistic(user: User = Depends(get_manager_active_user)) -> str:
    total, used, _ = shutil.disk_usage("/")
    return used/total

@router.get('/search-timestamp')
async def search_timestamp_statistic() -> str:
    with open('happened.json','r') as jsonfile:
        data = json.load(jsonfile)
        timestamp = data["timestamp"]
        return timestamp

@router.get("/env-settings")
async def get_env_settings(key: str = None, user: User = Depends(get_manager_active_user)):
    get_env = await Env.objects.filter(key=key).get_or_none()
    if get_env is None:
        raise HTTPException(
            status_code=400, detail="can't find the env key data"
        )
    return get_env


@router.post("/update-settings")
async def update_settings(key: str = None, value: str = None, user: User = Depends(get_manager_active_user)):
    if key is None:
        raise HTTPException(
            status_code=400, detail="no env key input"
        )
    if value is None:
        raise HTTPException(
            status_code=400, detail="no env value input"
        )
    get_env = await Env.objects.filter(
        key=key
    ).get_or_none()
    try:
        if get_env is None:
            # raise HTTPException(
            #     status_code=400, detail="can't find the env key"
            # )
            await Env.objects.create(
                key=key,
                value=value
            )
            return "success"
        else:
            await Env.objects.filter(
                key=get_env.key
            ).update(
                value=value
            )
            return "success"
    except:
        raise HTTPException(400, 'cannot update env data')
