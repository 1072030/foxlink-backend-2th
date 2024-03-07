"""
網頁前端特別顯示內容
"""

from fastapi import APIRouter, Depends, status
from fastapi.exceptions import HTTPException
from typing import Optional
from app.core.database import (
    UserLevel,
    User,
    Project,
)
from app.services.auth import (
    get_current_user,
    checkUserSearchProjectPermission,
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
    """
    給前端請求伺服器資料列表
    """
    project_id_list, project_name_list = await checkUserSearchProjectPermission(user, UserLevel.project_worker.value)
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
    """
    儀表板內容和機況預測api
    """
    project_id_list, project_name_list = await checkUserSearchProjectPermission(user, UserLevel.project_worker.value)
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
    """
    給前端請求的資料內容
    """
    project_id_list, project_name_list = await checkUserSearchProjectPermission(user, UserLevel.project_worker.value)
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
async def get_predict_compare_search(start_time: datetime, end_time: datetime, select_type: str, project_name: Optional[str] = None, line: Optional[int] = None, user: User = Depends(get_current_user())):
    """
    機況比較api
    """
    project_id_list, project_name_list = await checkUserSearchProjectPermission(user, UserLevel.project_worker.value)
    start_time = start_time.replace(hour=0, minute=0, second=0, microsecond=0)
    end_time = end_time.replace(hour=0, minute=0, second=0, microsecond=0)
    try:
        if project_name is None:
            return await GetPredictCompareSearch(project_name_list, select_type, line, start_time, end_time)
        else:
            return await GetPredictCompareSearch([project_name], select_type, line, start_time, end_time)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=repr(e)
        )


@router.get("/predict-compare-analysis", tags=["statistics"])
async def get_predict_compare_analysis(project_name: str, line: str, select_type: str, start_date: datetime, end_date: datetime, user: User = Depends(get_current_user())):
    """
    比較圖表
    """
    project_id_list, project_name_list = await checkUserSearchProjectPermission(user, UserLevel.project_worker.value)
    start_date = start_date.replace(hour=0, minute=0, second=0, microsecond=0)
    end_date = end_date.replace(hour=0, minute=0, second=0, microsecond=0)
    # 選擇對應線號和專案
    try:
        return await GetPredictCompareAnalysis(project_name, line, select_type, start_date, end_date)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=repr(e)
        )
