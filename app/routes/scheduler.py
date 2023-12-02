from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.executors.pool import ThreadPoolExecutor, ProcessPoolExecutor
from apscheduler.jobstores.memory import MemoryJobStore
from apscheduler.jobstores.sqlalchemy import SQLAlchemyJobStore
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, status
from fastapi.exceptions import HTTPException
jobstores = {
    # pickle_protocol=2,
    "default": SQLAlchemyJobStore(url=f"mysql+pymysql://root:AqqhQ993VNto@mysql-test:3306/foxlink", tablename="job", engine_options={"pool_recycle": 1500})
}
executors = {
    "default": ThreadPoolExecutor(20),
    "processpool": ProcessPoolExecutor(5),
}
job_defaults = {"coalesce": False, "max_instances": 3}
backgroundScheduler = BackgroundScheduler(
    jobstores=jobstores, executors=executors, job_defaults=job_defaults)
asyncIOScheduler = AsyncIOScheduler(
    jobstores=jobstores, executors=executors, job_defaults=job_defaults)

router = APIRouter(prefix="/scheduler")


def printname():
    print("Mike")


def printTime():
    print("this time")


@router.get("/", tags=["scheduler"])
async def get_all_jobs():
    res = backgroundScheduler.get_jobs()
    # return res.__repr__()

    return [{"id": job.id, "func": job.func_ref, "args": job.args} for job in res]


@router.post("/", tags=["scheduler"])
async def set_daily_job(time: datetime):

    backgroundScheduler.add_job(func=printname, trigger='interval', seconds=3)
    return "Health OK"


@router.delete("/", tags=["scheduler"])
async def delete_job(job_id: str):

    try:
        backgroundScheduler.remove_job(job_id)
        return "Delete Successful"
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=f"PREDICT_FAILED : {repr(e)}"
        )


@router.get("/date", tags=["scheduler"])
async def set_date_job(time: datetime):

    backgroundScheduler.add_job(printname, 'date', seconds=3)
    return "Health OK"


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
async def set_cron_job(time: datetime, select_type: str,description:str):
    time = time + timedelta(hours=-8)

    if select_type == "day":
        task = backgroundScheduler.add_job(id=description, func=printname, trigger='cron',
                                           replace_existing=True, hour=time.hour, minute=time.minute, second=time.second)
    elif select_type == "week":
        task = backgroundScheduler.add_job(func=printname, trigger='cron', day_of_week=time.weekday(
        ), hour=time.hour, minute=time.minute, second=time.second)
    else:
        task = backgroundScheduler.add_job(
            func=printname, trigger='cron', day=time.day, hour=time.hour, minute=time.minute, second=time.second)

    return {"id": task.id, "func": task.func_ref}
