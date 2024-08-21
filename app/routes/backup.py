"""
主要與資料庫的備份有關
"""
import subprocess
from fastapi import APIRouter, Depends, HTTPException
from app.services.auth import (
    get_current_user,
    checkAdminPermission
)
from app.core.database import (
    User,
    AuditLogHeader,
    AuditActionEnum,
)
import subprocess
from fastapi.responses import JSONResponse
from app.env import (
    DATABASE_HOST,
    DATABASE_USER,
    DATABASE_PASSWORD,
    DATABASE_NAME,
)
from app.services.backup import FullBackup

router = APIRouter(prefix="/backup")


@router.get("/statistics",  tags=["backup"])
# 備份前端頁面所需資料
async def get_backup_detail(user: User = Depends(get_current_user())):
    # 確認使用者權限
    user = await checkAdminPermission(user)

    text = ["手動備份", "差異備份", "完整備份"]
    logs = []
    try:
        for i in text:
            log = await AuditLogHeader.objects.filter(action=AuditActionEnum.FULL_BACKUP.value, description=i).order_by("-created_date").limit(1).get_or_none()
            if log is not None:
                logs.append({"name": log.description, "date": str(log.created_date)[:19]})
        return logs
    # try:
    #     for i in text:
    #         log = await AuditLogHeader.objects.filter(action=AuditActionEnum.FULL_BACKUP.value, description=i).order_by("-created_date").limit(1).get_or_none()
    #         if log is not None:
    #             logs.append(log)

    #     return [{"name": data.description, "date": data.created_date} for data in logs]
    except Exception as e:
        raise HTTPException(status_code=200, detail=e.__repr__())

@router.post("/",  tags=["backup"])
# 手動完整備份功能
async def full_backup(path: str = "/app/backup.sql", user: User = Depends(get_current_user())):
    # 確認使用者權限
    user = await checkAdminPermission(user)

    try:
        res = await FullBackup(path)
        await AuditLogHeader.objects.create(
            action=AuditActionEnum.FULL_BACKUP.value,
            user=user.badge,
            description="手動備份"
        )
        return res
    except Exception as e:
        return JSONResponse(content={"error": f"Error: {e}"}, status_code=500)


@router.post("/restore-backup",  tags=["backup"])
# 備份還原功能
async def restore_backup(path: str = '/app/backup.sql', user: User = Depends(get_current_user())):
    # 確認使用者權限
    user = await checkAdminPermission(user)
    # .sql檔案還原指令
    mysqldump_cmd = f"mysql -h {DATABASE_HOST} -u {DATABASE_USER} -p{DATABASE_PASSWORD} {DATABASE_NAME} < {path}"
    try:
        subprocess.run(mysqldump_cmd, shell=True, check=True)
        await AuditLogHeader.objects.create(
            action=AuditActionEnum.BACKUP_RESTORE.value,
            user=user.badge,
            description="資料庫還原"
        )
        return JSONResponse(content={"message": "Database backup successful."})
    except subprocess.CalledProcessError as e:
        return JSONResponse(content={"error": f"Error: {e}"}, status_code=500)