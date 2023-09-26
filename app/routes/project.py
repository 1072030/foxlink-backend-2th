from typing import Dict
from fastapi import APIRouter,Depends,status
from fastapi.exceptions import HTTPException
from typing import List,Dict
# from fastapi import Query
from app.core.database import (
    Project,
    User,
)
from app.services.project import(
    AddNewProject,
    AddNewProjectWorker,
    SearchProjectDevices,
    AddNewProjectEvents,
    DeleteProject,
    CreateTable
)
from app.services.auth import (
    get_current_user,
    checkUserProjectPermission
)
from app.models.schema import NewProjectDto

router = APIRouter(prefix="/project")


@router.get("/", tags=["project"])
async def get_all_project():
    return await Project.objects.all()

@router.post("/", tags=["project"])
async def add_new_project(project_name:str,user:User = Depends(get_current_user())):
    return await AddNewProject(project_name,user)

@router.delete("/", tags=["project"])
async def delete_project(project_id:int,user:User = Depends(get_current_user())):
    # print(user)
    user = await checkUserProjectPermission(project_id,user,5)
    if user is not None:
        return await DeleteProject(project_id)
    else:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Permission Denied"
        )

@router.post("/add-project-worker", tags=["project"])
async def add_new_workers(project_id:int,user_id:str,permission:int):
    return await AddNewProjectWorker(project_id,user_id,permission)

@router.get("/search-project-devices",tags=["project"])
async def search_project_devices(project_id:str):
    return await SearchProjectDevices(project_id)

@router.post("/add-project-events",status_code=200,tags=["project"])
async def add_project_events(dto:NewProjectDto):
    # user:User = await checkUserProjectPermission(project_id,user,5)
    return await AddNewProjectEvents(dto)

@router.get("/create_table",tags=["project"])
async def create_table():
    return await CreateTable()