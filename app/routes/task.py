
from fastapi import APIRouter
from datetime import timedelta
from app.core.database import (
    Task,
    TaskAction,
    TaskStatus,
    AuditLogHeader,
    AuditActionEnum,
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
    """
    取得所有的task
    """
    return await Task.objects.all()

@router.delete("/",tags=["task"])
async def remove_task(dto:List[str]):
    """
    刪除task 目前無作用
    """
    return

@router.post("/redo", tags=["task"])
async def redo_task(id:int,action:TaskAction,args:List[str]):
    """
    重新執行task
    """
    task = Task(
        action=action,
        stauts=TaskStatus.Pending.value,
        args=args
    )
    await Task.objects.create(task)

@router.get("/check-task", tags=["task"])
async def checking_task():
    """
    task queue的api
    """
    pending_task = await Task.objects.order_by('id').filter(status=TaskStatus.Pending.value).limit(1).get_or_none()
    processing_task = await Task.objects.order_by('id').filter(status=TaskStatus.Processing.value).limit(1).get_or_none()

    # 正在執行
    if processing_task is not None:
        # 運作時間過長
        # if processing_task.updated_date >= get_ntz_now() - timedelta(hours=3):
        #     processing_task.status = TaskStatus.Failure.value
        #     await processing_task.update()
        return
    
    # 沒有任務
    if pending_task is None:
        return
        
        #--- 執行任務
    args = pending_task.args.split(',')
    pending_task.status = TaskStatus.Processing.value
    pending_task.updated_date = get_ntz_now()
    await pending_task.update()
    
    if pending_task.action == TaskAction.DATA_PREPROCESSING.value:
            await AuditLogHeader.objects.create(
                action=AuditActionEnum.DATA_PREPROCESSING_STARTED.value,
                user='admin',
                description=args[0]
            )
            try:
                await PreprocessingData(int(args[0]))
                await AuditLogHeader.objects.create(
                    action=AuditActionEnum.DATA_PREPROCESSING_SUCCEEDED.value,
                    user='admin',
                    description=args[0]
                )

                pending_task.status = TaskStatus.Succeeded.value
                pending_task.updated_date = get_ntz_now()
                await pending_task.update()

            except Exception as e:
                await AuditLogHeader.objects.create(
                    action=AuditActionEnum.DATA_PREPROCESSING_FAILED.value,
                    user='admin',
                    description=f'{args[0]} detail:{e}'
                )

                pending_task.status = TaskStatus.Failure.value
                await pending_task.update()

        # 日預測
    elif pending_task.action == TaskAction.TRAINING_DAY.value:
            await AuditLogHeader.objects.create(
                action=AuditActionEnum.TRAINING_STARTED_DAILY.value,
                user='admin',
                description=args[0]
            )
            try:
                await TrainingData(int(args[0]),args[1])
                await AuditLogHeader.objects.create(
                    action=AuditActionEnum.TRAINING_SUCCEEDED_DAILY.value,
                    user='admin',
                    description=args[0]
                )

                pending_task.status = TaskStatus.Succeeded.value
                pending_task.updated_date = get_ntz_now()
                await pending_task.update()

            except Exception as e:
                await AuditLogHeader.objects.create(
                    action=AuditActionEnum.TRAINING_FAILED_DAILY.value,
                    user='admin',
                    description=f'{args[0]} detail:{e}'
                )
                pending_task.status = TaskStatus.Failure.value
                await pending_task.update()


        # 週預測
    elif pending_task.action == TaskAction.TRAINING_WEEK.value:
            await AuditLogHeader.objects.create(
                action=AuditActionEnum.TRAINING_STARTED_WEEKLY.value,
                user='admin',
                description=args[0]
            )
            try:
                await TrainingData(int(args[0]),args[1])
                await AuditLogHeader.objects.create(
                    action=AuditActionEnum.TRAINING_SUCCEEDED_WEEKLY.value,
                    user='admin',
                    description=args[0]
                )

                pending_task.status = TaskStatus.Succeeded.value
                pending_task.updated_date = get_ntz_now()
                await pending_task.update()

            except Exception as e:
                await AuditLogHeader.objects.create(
                    action=AuditActionEnum.TRAINING_FAILED_WEEKLY.value,
                    user='admin',
                    description=f'{args[0]} detail:{e}'
                )

                pending_task.status = TaskStatus.Failure.value
                await pending_task.update()

    return