
from fastapi import APIRouter
from datetime import timedelta
from app.core.database import (
    Task,
    TaskAction,
    TaskStatus,
    get_ntz_now
)
from app.services.project import(
    PreprocessingData,
    TrainingData,
)
from typing import List
router = APIRouter(prefix="/task")
@router.get("/", tags=["task"])
async def get_all_task():
    return await Task.objects.all()

@router.post("/redo", tags=["task"])
async def redo_task(id:int,action:TaskAction,args:List[str]):
    task = Task(
        action=action,
        stauts=TaskStatus.Pending.value,
        args=args
    )
    await Task.objects.create(task)

@router.delete("/",tags=["task"])
async def remove_task(dto:List[str]):
    return


@router.get("/checking", tags=["task"])
async def checking_task():
    pending_task = await Task.objects.order_by('id').filter(status=TaskStatus.Pending.value).limit(1).get_or_none()
    processing_task = await Task.objects.order_by('id').filter(status=TaskStatus.Processing.value).limit(1).get_or_none()

    # 運作時間過長
    if processing_task.updated_date >= get_ntz_now() - timedelta(hours=3):
        processing_task.status = TaskStatus.Failure.value
        await processing_task.update()
        return
    # 正在執行
    if processing_task is not None:
        return

    # 沒有任務
    if pending_task is None:
        return
        
        #--- 執行任務
    args = pending_task.args.split(',')
    pending_task.status = TaskStatus.Processing.value
    pending_task.updated_date = get_ntz_now()
    await pending_task.update()
    try:
        if pending_task.action == TaskAction.DATA_PREPROCESSING.value:
            await PreprocessingData(int(args[0]))
        elif pending_task.action == TaskAction.TRAINING_DAY.value:
            await TrainingData(int(args[0]),args[1])
        elif pending_task.action == TaskAction.TRAINING_WEEK.value:
            await TrainingData(int(args[0]),args[1])
        pending_task.status = TaskStatus.Succeeded.value
        pending_task.updated_date = get_ntz_now()
        await pending_task.update()
    except Exception as e:
        pending_task.status = TaskStatus.Failure.value
        await pending_task.update()
    return