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
# 備份頁面所需資料
async def get_backup_detail(user: User = Depends(get_current_user())):
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
# 完整備份
async def full_backup(path: str = "/app/backup.sql", user: User = Depends(get_current_user())):
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
# 完整備份
async def restore_backup(path: str = '/app/backup.sql', user: User = Depends(get_current_user())):
    user = await checkAdminPermission(user)

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

# 增量備份
# @router.post("/flush-incremental",  tags=["backup"])
# async def flush_incremental_backup():
#     # 使用mysqlbinlog命令备份二进制日志
#     flush_cmd = f"mysqladmin -h {DATABASE_HOST} -u{DATABASE_USER} -pAqqhQ993VNto flush-logs;"

#     # 执行备份命令
#     try:
#         stdout = subprocess.run(flush_cmd, shell=True, check=True,stdout=subprocess.PIPE)
#         output = stdout.stdout.decode('utf-8')
#         return JSONResponse(content={"message": "Incremental backup successful."})
#     except subprocess.CalledProcessError as e:
#         return JSONResponse(content={"error": f"Error: {e}"}, status_code=500)

# @router.post("/incremental",  tags=["backup"])
# async def incremental_backup():
#     # 使用mysqlbinlog命令备份二进制日志
#     backup_cmd = f"mysql -h {DATABASE_HOST} -u{DATABASE_USER} -pAqqhQ993VNto -e 'show binary logs;'"
#     # flush_cmd = f"mysqladmin -h {DATABASE_HOST} -u{DATABASE_USER} -pAqqhQ993VNto flush-logs;"

#     # 执行备份命令
#     try:
#         stdout = subprocess.run(backup_cmd, shell=True, check=True,stdout=subprocess.PIPE)
#         data = stdout.stdout.decode('utf-8')
#         data = data.split('\t')
#         for i in range(len(data)):
#             temp = data[i].split('\n')
#             if len(temp) == 2:
#                 data[i] = temp[1]
#             else:
#                 data[i] = temp[0]
#         output = []
#         for i in range(2,len(data)-1,2):
#             output.append({
#                 "LogName":data[i],
#                 "FileSize":data[i+1]
#             })
#         return output
#     except subprocess.CalledProcessError as e:
#         return JSONResponse(content={"error": f"Error: {e}"}, status_code=500)

# @router.post("/show-status",  tags=["backup"])
# async def showStatus():
#     # 使用mysqlbinlog命令备份二进制日志
#     backup_cmd = f"mysql -h {DATABASE_HOST} -u{DATABASE_USER} -pAqqhQ993VNto -e 'show master status;'"

#     # 执行备份命令
#     try:
#         stdout = subprocess.run(backup_cmd, shell=True, check=True,stdout=subprocess.PIPE)
#         output = stdout.stdout.decode('utf-8')
#         output = output.split('\t')

#         return JSONResponse(content={"message": f"File:{output[4]},Position:{output[5]}"})
#     except subprocess.CalledProcessError as e:
#         return JSONResponse(content={"error": f"Error: {e}"}, status_code=500)

# @router.post("/binlog-events",  tags=["backup"])
# async def incremental_backup(file_num:str = "000004"):
#     # 使用mysqlbinlog命令备份二进制日志
#     backup_cmd = f"mysql -h {DATABASE_HOST} -u{DATABASE_USER} -pAqqhQ993VNto -e 'show binlog events in \"binlog.{file_num}\";'"

#     # 执行备份命令
#     try:
#         stdout = subprocess.run(backup_cmd, shell=True, check=True,stdout=subprocess.PIPE)
#         print(stdout.stdout)
#         return JSONResponse(content={"message": "Incremental backup successful."})
#     except subprocess.CalledProcessError as e:
#         return JSONResponse(content={"error": f"Error: {e}"}, status_code=500)

# @router.post("/restore-binlog",tags=["backup"])
# async def restoreBinglog():
#     backup_cmd=f"mysqlbinlog --read-from-remote-server --host='mysql-test' --port=3306 --user root --pAqqhQ993VNto --result-file=/out.txt /var/lib/mysql/binlog.000002"
#     # mysqlbinlog --read-from-remote-server --host=my.server.rds.amazonaws.com --port=3306  --user foo --password --result-file=/tmp/out.txt mysql-bin-changelog.164974
#     try:
#         stdout = subprocess.run(backup_cmd, shell=True, check=True,stdout=subprocess.PIPE)
#         # output = stdout.stdout.decode('utf-8')
#         # output = output.split('\t')
#         return
#         # return JSONResponse(content={"message": f"File:{output[4]},Position:{output[5]}"})
#     except subprocess.CalledProcessError as e:
#         return JSONResponse(content={"error": f"Error: {e}"}, status_code=500)
