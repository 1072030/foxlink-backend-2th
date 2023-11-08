"""
網頁前端特別顯示內容
"""

from fastapi import APIRouter, Depends, status
from fastapi.exceptions import HTTPException
from typing import List, Dict, Optional, Union
from app.core.database import (
    User,
    Project,
    transaction
)
from app.services.auth import (
    get_current_user,
    checkUserProjectPermission,
    checkUserSearchProjectPermission,
    checkAdminPermission,
    checkFoxlinkAuth,
    get_manager_active_user
)
from app.services.statistics import (
    GetPredictResult
)

router = APIRouter(prefix="/statistics")


@router.get("/", tags=["statistics"])
async def get_all_project_statistics(user: User = Depends(get_current_user())):
    project_id_list = await checkUserSearchProjectPermission(user, 5)
    # await GetAllProjectStatistics()
    data = await Project.objects.filter(id__in=project_id_list).select_related(["devices"]).all()
    formatData = []
    for i in data:
        temp = {}
        temp['project_name'] = i.name.upper()
        temp['devices'] = [device.name for device in i.devices]
        formatData.append(temp)
    return formatData


@router.get("/predict_result", tags=["statistics"])
async def get_predict_result(project_name: Optional[str] = None, device_name: Optional[str] = None, user: User = Depends(get_current_user())):
    project_id_list = await checkUserSearchProjectPermission(user, 5)
    project = []
    if project_name is not None:
        project = project_name.split('+')
    else:
        project_name = ','.join([f'{dvs}' for dvs in project_id_list])
    if len(project) == 2:
        project_name = ' '.join(project)
    try:
        return await GetPredictResult(project_name, device_name)
    except Exception as e:
        # await AuditLogHeader.objects.create(
        #     action=AuditActionEnum.DATA_PREPROCESSING_FAILED.value,
        #     user=user.badge
        # )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=repr(e)
        )

    return
