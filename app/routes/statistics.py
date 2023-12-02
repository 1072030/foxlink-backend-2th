"""
網頁前端特別顯示內容
"""

from fastapi import APIRouter, Depends, status
from fastapi.exceptions import HTTPException
from typing import List, Dict, Optional, Union
from app.core.database import (
    User,
    Project,
    PredictResult,
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
    GetPredictResult,
    GetPredictCompareSearch,
    GetPredictCompareAnalysis
)
from datetime import datetime
router = APIRouter(prefix="/statistics")


@router.get("/", tags=["statistics"])
async def get_all_project_statistics(user: User = Depends(get_current_user())):
    project_id_list, project_name_list = await checkUserSearchProjectPermission(user, 5)
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
    project_id_list, project_name_list = await checkUserSearchProjectPermission(user, 5)
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


@router.get("/predict-compare-list", tags=["statistics"])
async def get_predict_compare_list(user: User = Depends(get_current_user())):
    project_id_list, project_name_list = await checkUserSearchProjectPermission(user, 5)
    data = await Project.objects.filter(id__in=project_id_list).select_related("devices").all()
    output = []
    for project in data:
        devices = {}
        lines = []
        for dvs in project.devices:
            if dvs.line not in lines:
                lines.append(dvs.line)

        output.append({
            "project_name": project.name,
            "lines": lines
        })
    return output


@router.get("/predict-compare-search", tags=["statistics"])
async def get_predict_compare_search(start_time: datetime, end_time: datetime,select_type:str, project_name: Optional[str] = None,line: Optional[int] = None, user: User = Depends(get_current_user())):
    project_id_list, project_name_list = await checkUserSearchProjectPermission(user, 5)
    start_time = start_time.replace(hour=0,minute=0,second=0,microsecond=0)
    end_time = end_time.replace(hour=0,minute=0,second=0,microsecond=0)
    try:
        if project_name is None:
            return await GetPredictCompareSearch(project_name_list,select_type,line,start_time,end_time)
        else:
            return await GetPredictCompareSearch([project_name],select_type,line,start_time,end_time)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=repr(e)
        )

@router.get("/predict-compare-analysis",tags=["statistics"])
async def get_predict_compare_analysis(project_name:str,line:str,select_type:str,start_date:datetime,end_date:datetime, user: User = Depends(get_current_user())):
    project_id_list, project_name_list = await checkUserSearchProjectPermission(user, 5)
    start_date = start_date.replace(hour=0,minute=0,second=0,microsecond=0)
    end_date = end_date.replace(hour=0,minute=0,second=0,microsecond=0)
    # 選擇對應線號和專案
    try:
        return await GetPredictCompareAnalysis(project_name,line,select_type,start_date,end_date)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=repr(e)
        )
