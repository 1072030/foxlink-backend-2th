import subprocess
from app.env import (
    DATABASE_HOST,
    DATABASE_USER,
    DATABASE_PASSWORD,
    DATABASE_NAME,
    DATABASE_PORT
)
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.executors.pool import ThreadPoolExecutor, ProcessPoolExecutor
from apscheduler.jobstores.sqlalchemy import SQLAlchemyJobStore
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, status
from fastapi.exceptions import HTTPException
from app.core.database import Env

from app.core.database import (
    get_ntz_now,
    AuditActionEnum,
)
from enum import Enum
from app.foxlink.db import foxlink_dbs
import requests
# -- init --
jobstores = {
    # pickle_protocol=2,
    "default": SQLAlchemyJobStore(url=f"mysql+pymysql://{DATABASE_USER}:{DATABASE_PASSWORD}@{DATABASE_HOST}:{DATABASE_PORT}/{DATABASE_NAME}", tablename="job")
}
executors = {
    "default": ThreadPoolExecutor(20),
    "processpool": ProcessPoolExecutor(5),
}
job_defaults = {"coalesce": False, "max_instances": 3}
# backgroundScheduler = BackgroundScheduler(
#     jobstores=jobstores, executors=executors, job_defaults=job_defaults)
asyncIOScheduler = AsyncIOScheduler(
    jobstores=jobstores, executors=executors, job_defaults=job_defaults)
# -- end init --


router = APIRouter(prefix="/scheduler")


class Select_type(Enum):
    Daily = "Daily"
    Weekly = "Weekly"
    Monthly = "Monthly"

def backup(path: str, description: str):
    name = path.split('.')
    name = name[0]+'-'+str(get_ntz_now().date())+'.'+name[1]
    mysqldump_cmd = f"mysqldump -h {DATABASE_HOST} -u {DATABASE_USER} -p{DATABASE_PASSWORD} {DATABASE_NAME} --lock-all-tables > {name}"
    subprocess.run(mysqldump_cmd, shell=True, check=True)
    foxlink_dbs.ntust_db.execute(
        f"INSERT INTO audit_log_headers (action,user,created_date,description) VALUES ('{AuditActionEnum.FULL_BACKUP.value}','admin','{get_ntz_now()}','{description}')")

def pending_task():
    requests.get(url="http://localhost/task")
@router.get("/check-task", tags=["scheduler"])
async def check_task():
    asyncIOScheduler.add_job(pending_task,"interval",seconds=30,replace_existing=True)
    return


@router.get("/", tags=["scheduler"])
async def get_all_jobs():
    res = asyncIOScheduler.get_jobs()
    # return res.__repr__()

    return [{"id": job.id, "func": job.func_ref, "args": job.args, "next_run_time": job.next_run_time + timedelta(hours=8)} for job in res]

@router.delete("/", tags=["scheduler"])
async def delete_job(job_id: str):

    try:
        asyncIOScheduler.remove_job(job_id)
        return "Delete Successful"
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=f"PREDICT_FAILED : {repr(e)}"
        )


@router.post("/date", tags=["scheduler"])
async def set_date_job(time: datetime, description: str = "完整備份"):
    backup_path = await Env.objects.filter(key="backup_path").get_or_none()
    time = time + timedelta(hours=-8)
    if backup_path is None:
        backup_path = 'app/fullbackup.sql'
    else:
        backup_path = backup_path.value
    task = asyncIOScheduler.add_job(id="完整備份", func=backup, trigger='date', args=[
                                    backup_path, description], run_date=time, replace_existing=True)
    return {"id": task.id, "func": task.func_ref, "args": task.args, "next_run_time": task.next_run_time + timedelta(hours=8)}


# cron type
# 格式:* * * * *
# 第一個*代表minute
# 第二個*代表hour
# 第三個*代表day
# 第四個*代表month
# 第五個*代表week (禮拜幾)
# example : 10 23 * * 6
# 結果是: 執行在禮拜六的23點10分

@router.post("/cron", tags=["scheduler"])
async def set_cron_job(time: datetime, select_type: Select_type, description: str = "差異備份"):
    time = time + timedelta(hours=-8)
    diffbackup_path = await Env.objects.filter(key="diffbackup_path").get_or_none()
    if diffbackup_path is None:
        diffbackup_path = "/app/diffbackup/diffbackup.sql"
    else:
        diffbackup_path = diffbackup_path.value
        # args=[backup_path],
    if select_type == Select_type.Daily.value:
        task = asyncIOScheduler.add_job(id=description, func=backup, args=[diffbackup_path, description], trigger='cron',
                                        replace_existing=True, hour=time.hour, minute=time.minute, second=time.second)
    elif select_type == Select_type.Weekly.value:
        task = asyncIOScheduler.add_job(id=description, func=backup, args=[diffbackup_path, description], trigger='cron', day_of_week=time.weekday(
        ), hour=time.hour, minute=time.minute, second=time.second, replace_existing=True)
    else:
        task = asyncIOScheduler.add_job(
            id=description, func=backup, args=[diffbackup_path, description], trigger='cron', day=time.day, hour=time.hour, minute=time.minute, second=time.second, replace_existing=True)

    return {"id": task.id, "func": task.func_ref, "next_run_time": task.next_run_time}
