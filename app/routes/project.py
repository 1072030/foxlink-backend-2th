from typing import Dict
from fastapi import APIRouter,Depends,status
from fastapi.exceptions import HTTPException
from typing import List,Dict
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
    CreateTable
)
from app.services.auth import (
    get_current_user,
    checkUserProjectPermission,
    checkUserSearchProjectPermission,
    checkAdminPermission,
    checkFoxlinkAuth,
    get_manager_active_user
)
from app.models.schema import NewProjectDto

router = APIRouter(prefix="/project")


@router.get("/", tags=["project"])
async def get_all_project(user:User = Depends(get_current_user())):
    """
    取得所有專案內容(當前使用者權限內所有的專案)
    """
    project_id_list = await checkUserSearchProjectPermission(user,5)
    if len(project_id_list) != 0:
        return await (Project.objects.filter(
            id__in=project_id_list
        ).all())
    else:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Permission Denied"
        )

@router.get("/users", tags=["project"])
async def get_all_project(project_id:int,user:User = Depends(get_current_user())):
    """
    取得對應專案內的所有人員(當前使用者權限內的專案)
    """
    user = await checkUserProjectPermission(project_id,user,5)
    if user is not None:
        return await ProjectUser.objects.filter(project=project_id).fields(['user']).values()
    else:
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
            action=AuditActionEnum.ADD_PROJECT_WORKER.value,
            user=user.badge,
            description=f"{project_name}"
        )
        return
    else:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Permission Denied"
        )

@router.post("/add-project-worker", tags=["project"])
async def add_new_workers(project_id:int,user_id:str,permission:int,user:User = Depends(get_current_user())):
    """
    新增專案內人員(會確認新增者權限)
    """
    user = await checkUserProjectPermission(project_id,user,5)
    if user is not None:
        return await AddNewProjectWorker(project_id,user_id,permission)
        await AuditLogHeader.objects.create(
            action=AuditActionEnum.ADD_PROJECT_WORKER.value,
            user=user.badge,
            description=f"{user_id}"
        )
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
        return await AddNewProjectEvents(dto)
        await AuditLogHeader.objects.create(
            action=AuditActionEnum.ADD_NEW_PROJECT.value,
            user=user.badge,
            description=f"{dto[0].project}"
        )
    else:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Permission Denied"
        )
    # user:User = await checkUserProjectPermission(project_id,user,5)

@router.get("/create_table",tags=["project"])
async def create_table(project_id:int,user:User = Depends(get_current_user())):
    await AuditLogHeader.objects.create(
            action=AuditActionEnum.DATA_PREPROCESSING_STARTED.value,
            user=user.badge
        )
    try:
        await CreateTable(project_id)
        await AuditLogHeader.objects.create(
            action=AuditActionEnum.DATA_PREPROCESSING_SUCCEEDED.value,
            user=user.badge
        )
        return 
    except:
        await AuditLogHeader.objects.create(
            action=AuditActionEnum.DATA_PREPROCESSING_FAILED.value,
            user=user.badge
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="DATA_PREPROCESSING_FAILED"
        )

# @router.get("/testssh")
# async def sshconnect():
#     return await checkFoxlinkAuth()
    

# from fastapi import APIRouter, Depends, File, UploadFile
# import pandas as pd
# import os
# from fastapi.responses import FileResponse
# @router.post("/env-update-settings/execl_test")
# async def import_devices_from_excel(file: UploadFile = File(...),cols:str=""):
#     if file.filename.split(".")[1] != "xlsx":
#         raise HTTPException(415)
#     try:
#         # 將字串切為陣列
#         cols = cols.split(",") 
#         # 將字串改為數字
#         cols = [eval(i) for i in cols]
#         # 讀excel欄位為cols的參數
#         frame: pd.DataFrame = pd.read_excel(await file.read(), sheet_name=0,usecols=cols)
#         # 將欄位儲存到本地端
#         frame.to_excel(os.getcwd()+'/'+file.filename)
#         # 將header更改為回傳type
#         header = {
#             "Content-Type":"application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
#         }
#         return FileResponse(os.getcwd()+'/'+file.filename,filename=file.filename,headers=header)
#         # return ImportDevicesOut(device_ids=device_ids, parameter=params.to_csv())
#     except Exception as e:
#         raise HTTPException(status_code=400, detail=repr(e))