
from fastapi import APIRouter
from app.core.database import (
    Task,
    TaskAction,
    TaskStatus
)
from app.services.project import(
    PreprocessingData,
    TrainingData,
)
router = APIRouter(prefix="/task")
@router.get("/", tags=["task"])
async def task():
    pending_task = await Task.objects.order_by('id').filter(status=TaskStatus.Pending.value).limit(1).get_or_none()
    processing_task = await Task.objects.order_by('id').filter(status=TaskStatus.Processing.value).limit(1).get_or_none()

    # 正在執行
    if processing_task is not None:
        return

    # 沒有任務
    if pending_task is None:
        return
        
        #--- 執行任務
    args = pending_task.args.split(',')
    pending_task.status = TaskStatus.Processing.value
    await pending_task.update()
    try:
        if pending_task.action == TaskAction.DATA_PREPROCESSING.value:
            await PreprocessingData(int(args[0]))
        elif pending_task.action == TaskAction.TRAINING_DAY.value:
            await TrainingData(int(args[0]),args[1])
        elif pending_task.action == TaskAction.TRAINING_WEEK.value:
            await TrainingData(int(args[0]),args[1])
        pending_task.status = TaskStatus.Succeeded.value
        await pending_task.update()
    except Exception as e:
        pending_task.status = TaskStatus.Failure.value
        await pending_task.update()
    return