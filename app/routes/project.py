from typing import Dict
from fastapi import APIRouter,Depends,status
from fastapi.exceptions import HTTPException
from typing import List,Dict
# from fastapi import Query
from app.core.database import (
    Project,
    ProjectUser,
    User,
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
    checkFoxlinkAuth,
    get_manager_active_user
)
from app.models.schema import NewProjectDto

router = APIRouter(prefix="/project")


@router.get("/", tags=["project"])
async def get_all_project():
    """
    取得所有專案內容
    """
    return await Project.objects.all()

@router.get("/users", tags=["project"])
async def get_all_project(project_id:int):
    """
    取得對應專案內的所有人員
    """
    return await ProjectUser.objects.filter(project=project_id).all()

# @router.post("/", tags=["project"])
# async def add_new_project(project_name:str):
#     """
#     新增專案(僅admin身分可以新增)
#     """
#     return
#     return await AddNewProject(project_name,user)

@router.delete("/", tags=["project"])
async def delete_project(project_id:int,user:User = Depends(get_current_user())):
    """
    刪除專案(僅專案內最高階級人員)
    """
    user = await checkUserProjectPermission(project_id,user,5)
    if user is not None:
        return await DeleteProject(project_id)
    else:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Permission Denied"
        )

@router.post("/add-project-worker", tags=["project"])
async def add_new_workers(project_id:int,user_id:str,permission:int):
    """
    新增專案內人員
    """
    return await AddNewProjectWorker(project_id,user_id,permission)

@router.get("/search-project-devices",tags=["project"])
async def search_project_devices(project_id:str):
    """
    搜尋專案擁有的devices
    """
    return await SearchProjectDevices(project_id)

@router.post("/add-project-events",status_code=200,tags=["project"])
async def add_project_events(dto:NewProjectDto):
    """
    搜尋專案內的所有事件
    """
    # user:User = await checkUserProjectPermission(project_id,user,5)
    return await AddNewProjectEvents(dto)

@router.get("/create_table",tags=["project"])
async def create_table():
    return await CreateTable()
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