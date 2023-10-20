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
    User,
    AuditLogHeader,
    AuditActionEnum
)
import subprocess
from fastapi.responses import JSONResponse
from app.env import (
    DATABASE_HOST,
    DATABASE_USER,
    DATABASE_PASSWORD,
    DATABASE_NAME,
)
router = APIRouter(prefix="/backup")


@router.post("/",  tags=["backup"])
# 完整備份
async def full_backup(path:str,name:str,user:User = Depends(get_current_user())):
    mysqldump_cmd = f"mysqldump -h {DATABASE_HOST} -u {DATABASE_USER} -p{DATABASE_PASSWORD} {DATABASE_NAME} > {name}.sql"
    try:
        subprocess.run(mysqldump_cmd, shell=True, check=True)
        await AuditLogHeader.objects.create(
            action=AuditActionEnum.FULL_BACKUP.value,
            user=user.badge
        )
        return JSONResponse(content={"message": "Database backup successful."})
    except subprocess.CalledProcessError as e:
        print(f"Error: {e}")
    return

# 差異備份
@router.post("/diff",  tags=["backup"])
async def incremental_backup():
    # 使用mysqlbinlog命令备份二进制日志
    backup_cmd = f"mysqlbinlog --read-from-remote-server -h {DATABASE_HOST} -u {DATABASE_USER} -p{DATABASE_PASSWORD} --raw backup.log"

    # 执行备份命令
    try:
        subprocess.run(backup_cmd, shell=True, check=True)
        return JSONResponse(content={"message": "Incremental backup successful."})
    except subprocess.CalledProcessError as e:
        return JSONResponse(content={"error": f"Error: {e}"}, status_code=500)

# 備份還原