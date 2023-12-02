"""
和專案有關係
"""
from fastapi import APIRouter,Depends,status
from fastapi.exceptions import HTTPException
from typing import List
# from fastapi import Query
from app.core.database import (
    Project,
    ProjectUser,
    User,
    AuditActionEnum,
    AuditLogHeader,
    transaction
)
from app.services.project import(
    AddNewProjectWorker,
    SearchProjectDevices,
    AddNewProjectEvents,
    DeleteProject,
    RemoveProjectWorker,
    PreprocessingData,
    UpdatePreprocessingData,
    TrainingData,
    PredictData,
    HappenedCheck
)
from app.services.auth import (
    get_current_user,
    checkUserProjectPermission,
    checkUserSearchProjectPermission,
    checkAdminPermission,
    checkFoxlinkAuth,
    get_manager_active_user
)
from app.models.schema import NewProjectDto,NewUserDto
from datetime import datetime
router = APIRouter(prefix="/project")


@router.get("/", tags=["project"])
async def get_all_project(user:User = Depends(get_current_user())):
    """
    取得所有專案內容(當前使用者權限內所有的專案)
    """
    project_id_list,project_name_list = await checkUserSearchProjectPermission(user,5)
    if len(project_id_list) != 0:
        return await (Project.objects.filter(
            id__in=project_id_list
        ).all())

@router.get("/users", tags=["project"])
async def get_all_project(project_id:int,user:User = Depends(get_current_user())):
    """
    取得對應專案內的所有人員(當前使用者權限內的專案)
    """
    user = await checkUserProjectPermission(project_id,user,5)

    try:
        user =  await ProjectUser.objects.select_related(['user']).filter(project=project_id).all()
        format_data = []
        for i in user:
            format_data.append({
                'badge':i.user.badge,
                'username':i.user.username,
                'permission':i.permission
            })
        return format_data
    except:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Permission Denied"
        )
    

@router.delete("/", tags=["project"])
async def delete_project(project_id:int,user:User = Depends(get_current_user())):
    """
    刪除專案(僅專案內最高階級人員)
    """
    user = await checkUserProjectPermission(project_id,user,5)
    if user is not None:
        project_name = await DeleteProject(project_id)
        await AuditLogHeader.objects.create(
            action=AuditActionEnum.DELECT_PROJECT.value,
            user=user.badge,
            description=f"{project_name}"
        )
        return
    else:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Permission Denied"
        )


@router.post("/add-project-worker", tags=["project"])
async def add_new_workers(dto:NewUserDto,user:User = Depends(get_current_user())):
    """
    新增專案內人員(會確認新增者權限)
    """
    user = await checkUserProjectPermission(dto.project_id,user,5)
    if user is not None:
        await AddNewProjectWorker(dto.project_id,dto.user_id,dto.permission)
        await AuditLogHeader.objects.create(
            action=AuditActionEnum.ADD_PROJECT_WORKER.value,
            user=user.badge,
            description=f"{dto.user_id}"
        )
        return
    else:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Permission Denied"
        )

@router.delete("/remove-project-worker", tags=["project"])
async def delete_workers(project_id:int,user_id:str,user:User = Depends(get_current_user())):
    """
    新增專案內人員(會確認新增者權限)
    """
    user = await checkUserProjectPermission(project_id,user,5)
    if user is not None:
        await RemoveProjectWorker(project_id,user_id)
        await AuditLogHeader.objects.create(
            action=AuditActionEnum.DELECT_PROJECT_WORKER.value,
            user=user.badge,
            description=f"{user_id}"
        )
        return
    else:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Permission Denied"
        )
    

@router.get("/search-project-devices",tags=["project"])
async def search_project_devices(project_name:str):
    """
    搜尋專案擁有的devices
    """
    return await SearchProjectDevices(project_name)


@router.post("/add-project-events",status_code=200,tags=["project"])
async def add_project_and_events(dto:List[NewProjectDto],user:User = Depends(get_current_user())):
    """
    搜尋專案內的所有事件(會確認新增者權限 = admin)
    """
    user = await checkAdminPermission(user)
    if user is not None:
        await AddNewProjectEvents(dto)
        await AuditLogHeader.objects.create(
            action=AuditActionEnum.ADD_NEW_PROJECT.value,
            user=user.badge,
            description=f"{dto[0].project}"
        )
        return
    else:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Permission Denied"
        )
    # user:User = await checkUserProjectPermission(project_id,user,5)

@router.get("/preprocessing-data",tags=["project"])
async def preprocessing_data(project_id:int,user:User = Depends(get_current_user())):
    
    await AuditLogHeader.objects.create(
            action=AuditActionEnum.DATA_PREPROCESSING_STARTED.value,
            user=user.badge
        )
    try:
        await PreprocessingData(project_id)
        await AuditLogHeader.objects.create(
            action=AuditActionEnum.DATA_PREPROCESSING_SUCCEEDED.value,
            user=user.badge
        )
        return
    except Exception as e:
        await AuditLogHeader.objects.create(
            action=AuditActionEnum.DATA_PREPROCESSING_FAILED.value,
            user=user.badge
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=f"DATA_PREPROCESSING_FAILED : {repr(e)}"
        )

@router.get("/update-preprocessing-data",tags=["project"])
async def update_preprocessing_data(project_id:int,user:User = Depends(get_current_user())):
    await AuditLogHeader.objects.create(
            action=AuditActionEnum.DAILY_PREPROCESSING_STARTED.value,
            user=user.badge
        )
    try:
        await UpdatePreprocessingData(project_id)
        await AuditLogHeader.objects.create(
            action=AuditActionEnum.DAILY_PREPROCESSING_SUCCEEDED.value,
            user=user.badge
        )
    except Exception as e:
        await AuditLogHeader.objects.create(
            action=AuditActionEnum.DAILY_PREPROCESSING_FAILED.value,
            user=user.badge
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=f"DAILY_PREPROCESSING_FAILED : {repr(e)}"
        )
    return

@router.get("/training-data",tags=["project"])
async def training_data(project_id:int,select_type:str,user:User = Depends(get_current_user())):
    
    try:
        await TrainingData(project_id,select_type)
        await AuditLogHeader.objects.create(
            action=AuditActionEnum.TRAINING_SUCCEEDED.value,
            user=user.badge
        )
    except Exception as e:
        await AuditLogHeader.objects.create(
            action=AuditActionEnum.TRAINING_FAILED.value,
            user=user.badge,
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=f"TRAINING_FAILED : {repr(e)}"
        )
    return

@router.get("/predict-data",tags=["project"])
async def predict_data(project_id:int,pred_type:str,user:User = Depends(get_current_user())):

    try:
        await PredictData(project_id,pred_type)
        await AuditLogHeader.objects.create(
            action=AuditActionEnum.PREDICT_SUCCEEDED.value,
            user=user.badge
        )
    except Exception as e:
        await AuditLogHeader.objects.create(
            action=AuditActionEnum.PREDICT_FAILED.value,
            user=user.badge
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=f"PREDICT_FAILED : {repr(e)}"
        )
    return

# @router.get("/happened-check",tags=["project"])
# async def happened_check(project_id:int,start_time:datetime,select_type:str):
#     await HappenedCheck(project_id,start_time,select_type)
#     return


@router.get("/testssh")
async def sshconnect():
    return await checkFoxlinkAuth(True)
    
