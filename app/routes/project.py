from typing import Dict
from fastapi import APIRouter,Depends
from fastapi.exceptions import HTTPException

from app.core.database import (
    Project,
    User,
)
from app.services.project import(
    AddNewProject,
    AddNewProjectWorker,
    SearchProjectDevices,
    AddNewProjectDevices,
    CreateTable
)
from app.services.auth import (
    get_admin_active_user
)

router = APIRouter(prefix="/project")


@router.get("/", tags=["project"])
async def get_all_project():
    return await Project.objects.all()

@router.post("/", tags=["project"])
async def add_new_project(project_name:str):
    return await AddNewProject(project_name)
    
@router.post("/add-project-worker", tags=["project"])
async def add_new_workers(project_id:int,user_id:str,permission:int):
    return await AddNewProjectWorker(project_id,user_id,permission)

@router.get("/search-project-devices",tags=["project"])
async def search_project_devices(project_id:str):
    return await SearchProjectDevices(project_id)

@router.get("/add-project-devices",tags=["project"])
async def add_project_devices(project_id:str):
    return await AddNewProjectDevices()

@router.get("/create_table",tags=["project"])
async def create_table():
    return await CreateTable()