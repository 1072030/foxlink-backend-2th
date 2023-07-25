from typing import Dict
from fastapi import APIRouter
from fastapi.exceptions import HTTPException
from app.core.database import (
    Project,
    User
)

router = APIRouter(prefix="/project")


@router.get("/", tags=["project"])
async def get_all_project():
    return await Project.objects.all()

@router.post("/", tags=["project"])
async def add_new_project(name:str):
    check_duplicate = await Project.objects.get_or_none(name=name)
    if check_duplicate is None:
        return await Project.objects.create(name=name)
    else:
        raise HTTPException(
            status_code=404, detail="The project name is duplicated.")
    
@router.post("/add-project-worker", tags=["project"])
async def add_new_workers(project_id:str,username:str):
    user = await User.objects.filter(username=username).get_or_none()
    if user is None:
        raise HTTPException(404, 'user is not found')
    
    project = await Project.objects.filter(id=project_id).get_or_none()

    if project is None:
        raise HTTPException(404, 'project is not found')

    if not await Project.objects.filter(id=project_id,workers__username=username).exists():
        await project.workers.add(user)
    else:
        raise HTTPException(400, 'the user already in the project.')