from typing import List, Dict, Optional, Union
from fastapi.exceptions import HTTPException
from app.core.database import (
    User,
    Device,
    Project,
    PredictResult,
    transaction
)


async def GetPredictResult(project_name:Optional[str] = None, device_name: Optional[str] = None):
    # if project_name is None:
    project_id_list = []
    check_project_name = project_name.split(',')
    single=None
    if len(check_project_name) == 2:
        project_id_list = list(map(int, project_name.split(',')))
    else:
        try:
            single = int(check_project_name[0])
        except:
            print('not single')

    if len(project_id_list) == 2:
        data = await Project.objects.filter(id__in=project_id_list).select_related(['devices']).all()
    else:
        if single is None:
            if device_name is None:
                data = await Project.objects.filter(name=project_name).select_related(['devices']).all()
            else:
                data = await Project.objects.filter(name=project_name).select_related(['devices']).filter(devices__name=device_name).all()
        else:
            data = await Project.objects.filter(id=single).select_related(['devices']).all()

    # devices = data[0].devices
    project_device = [project.devices for project in data]
    devices = []
    for i in project_device:
        for j in i:
            devices.append(j)
    devices_id = [dvs.id for dvs in devices]
    predictResult = await PredictResult.objects.filter(device__in=devices_id).order_by('pred_date').all()
    unique_events = set([result.event.id for result in predictResult])
    getAllFirstResultData = []
    for event in unique_events:
        firstResultData_week = await PredictResult.objects.filter(device__in=devices_id, event=event,pred_type=1).select_related(['event']).order_by('-pred_date').first()
        firstResultData_day = await PredictResult.objects.filter(device__in=devices_id, event=event,pred_type=0).select_related(['event']).order_by('-pred_date').first()
        getAllFirstResultData.append(firstResultData_week)
        getAllFirstResultData.append(firstResultData_day)

    formatData = {}
    for result in getAllFirstResultData:
        for i in devices:
            if result.device.id == i.id:
                dvs_project_name = " ".join(
                    (i.project.name).split(" ")).upper()
                dvs_name = i.name
                if dvs_project_name not in formatData.keys():
                    formatData[dvs_project_name] = {}
                if dvs_name not in formatData[dvs_project_name].keys():
                    formatData[dvs_project_name][dvs_name] = []
                if result.pred_type == 1:
                    pred_type = "週預測"
                else:
                    pred_type = "日預測"
                
                formatData[dvs_project_name][dvs_name].append({
                    'id': result.id,
                    'name': result.event.name,
                    'lightColor': int(result.pred),
                    'date': result.pred_date,
                    'frequency': pred_type,
                    'happenLastTime': True
                })
    return formatData
