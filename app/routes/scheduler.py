from apscheduler.schedulers.background import BackgroundScheduler
from typing import Dict
from fastapi import APIRouter
from datetime import datetime

backgroundScheduler = BackgroundScheduler()
router = APIRouter(prefix="/scheduler")

def printname():
    print("Mike")


@router.get("/", tags=["scheduler"])
async def set_job(func:str,time:datetime,loop:bool = False):

    backgroundScheduler.add_job(printname,'interval',seconds=3)
    return "Health OK"

@router.get("/jobs", tags=["scheduler"])
async def get_all_jobs():
    res = backgroundScheduler.get_jobs()
    return res.__repr__()



