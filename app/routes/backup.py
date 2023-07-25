from typing import List, Optional
from os import system
import subprocess
import os
import time
from fastapi import APIRouter, Depends, Form, HTTPException
from app.models.schema import (
    # CategoryPriorityOut,
    DeviceDispatchableWorker,
    WhitelistRecommendDevice
)
from app.services.auth import (
    get_manager_active_user,
    get_current_user
)
from app.core.database import (
    # CategoryPRI,
    api_db,
    User,
    UserLevel,
)

router = APIRouter(prefix="/backup")


@router.get("/",  tags=["backup"])
# 完整備份
async def full_backup():
    
    return
# 差異備份

# 備份還原