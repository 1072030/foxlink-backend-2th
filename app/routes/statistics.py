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
    GetPredictCompareSearch
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
        for dvs in project.devices:
            
            if dvs.name not in devices.keys():
                devices[dvs.name] = []
            devices[dvs.name].append(dvs.line)
        

        output.append({
            "project_name": project.name,
            "devices": devices
        })
    return output


@router.get("/predict-compare-search", tags=["statistics"])
async def get_predict_compare_search(start_time: datetime, end_time: datetime,select_type:str, project_name: Optional[str] = None,device:Optional[str] = None, line: Optional[int] = None, user: User = Depends(get_current_user())):
    project_id_list, project_name_list = await checkUserSearchProjectPermission(user, 5)
    start_time = start_time.replace(hour=0,minute=0,second=0,microsecond=0)
    end_time = end_time.replace(hour=0,minute=0,second=0,microsecond=0)
    try:
        if project_name is None:
            return await GetPredictCompareSearch(project_name_list,device,select_type,line,start_time,end_time)
        else:
            return await GetPredictCompareSearch([project_name],device,select_type,line,start_time,end_time)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=repr(e)
        )
    
@router.get("/predict-compare-detail",tags=["statistics"])
async def get_predict_compare_detail(project_name:str,device_name:str,line:int,date:datetime,select_type:str):
    
    data = await Project.objects.select_related(["devices","devices__events"]).filter(name=project_name,devices__name=device_name,devices__line=line).all()
    devices = data[0].devices
    formatData = {}
    if select_type == "day":
        for dvs in devices:
            for event in dvs.events:
                checkPredEvent = await PredictResult.objects.filter(event=event.id,pred_type=0).order_by('-pred_date').limit(1).get_or_none()

                # check
                if checkPredEvent is None:
                    continue
                            
                data = await PredictResult.objects.filter(event=event.id,pred_date=date,pred_type=0).select_related("device").order_by('-pred_date').limit(1).get_or_none()
                if data is None:
                    continue

                if project_name not in formatData.keys():
                    formatData[project_name] = {}
                if dvs.name not in formatData[project_name].keys():
                    formatData[project_name][dvs.name] = []
                
                if data.last_happened is None:
                    acutal = 0
                else:
                    acutal = 1
                formatData[project_name][dvs.name].append({
                    "name":event.name,
                    "true": acutal,
                    "predict":int(data.pred)
                })

    else:
        for dvs in devices:
            for event in dvs.events:
                checkPredEvent = await PredictResult.objects.filter(event=event.id,pred_type=1).order_by('-pred_date').limit(1).get_or_none()

                # check
                if checkPredEvent is None:
                    continue
                            
                data = await PredictResult.objects.filter(event=event.id,pred_date=date,pred_type=1).select_related("device").order_by('-pred_date').limit(1).get_or_none()
                if data is None:
                    continue
                
                if project_name not in formatData.keys():
                    formatData[project_name] = {}
                if dvs.name not in formatData[project_name].keys():
                    formatData[project_name][dvs.name] = []
                
                if data.last_happened is None:
                    acutal = 0
                else:
                    acutal = 1
                formatData[project_name][dvs.name].append({
                    "name":event.name,
                    "true": acutal,
                    "predict":int(data.pred)
                })

    return formatData

@router.get("/predict-compare-analysis",tags=["statistics"])
async def get_predict_compare_analysis(project_name:str,device_name:str,line:str,start_date:datetime,end_date:datetime):
    return
