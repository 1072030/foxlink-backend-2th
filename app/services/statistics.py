from typing import List, Dict, Optional, Union
from fastapi.exceptions import HTTPException
from app.core.database import (
    User,
    Device,
    Project,
    PredictResult,
    transaction
)
from datetime import datetime, timedelta
import pandas as pd
import numpy as np


async def GetPredictResult(project_name: Optional[str] = None, device_name: Optional[str] = None):
    # if project_name is None:
    project_id_list = []
    check_project_name = project_name.split(',')
    single = None
    if len(check_project_name) == 2:
        project_id_list = list(map(int, project_name.split(',')))
    else:
        try:
            single = int(check_project_name[0])
        except:
            print('not single')

    if len(project_id_list) == 2:
        data = await Project.objects.filter(id__in=project_id_list).select_related(['devices', 'devices__events']).all()
    else:
        if single is None:
            if device_name is None:
                data = await Project.objects.filter(name=project_name).select_related(['devices', 'devices__events']).all()
            else:
                data = await Project.objects.filter(name=project_name).select_related(['devices', 'devices__events']).filter(devices__name=device_name).all()
        else:
            data = await Project.objects.filter(id=single).select_related(['devices', 'devices__events']).all()

    # devices = data[0].devices
    project_device = [project.devices for project in data]
    devices = []
    for i in project_device:
        for j in i:
            devices.append(j)
    # devices_id = [dvs.id for dvs in devices]
    getAllFirstResultData = []
    for dvs in devices:

        events = dvs.events
        for event in events:
            checkPredEvent = await PredictResult.objects.filter(event=event.id).order_by('-pred_date').limit(1).get_or_none()

            # check
            if checkPredEvent is None:
                continue

            firstResultData_week = await PredictResult.objects.filter(device=dvs.id, event=event, pred_type=1).select_related(['event']).order_by('-pred_date').limit(1).get_or_none()
            firstResultData_day = await PredictResult.objects.filter(device=dvs.id, event=event, pred_type=0).select_related(['event']).order_by('-pred_date').limit(1).get_or_none()
            getAllFirstResultData.append(firstResultData_week)
            getAllFirstResultData.append(firstResultData_day)

    formatData = {}
    for result in getAllFirstResultData:
        if result is None:
            continue
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


async def GetPredictCompareSearch(project_name: List, device_name: str,select_type:str, line: int, start_time: datetime, end_time: datetime):
    formatData = []
    for project in project_name:
        if device_name is None:
            project_devices = await Project.objects.select_related(["devices", "devices__events"]).filter(name=project).all()

        else:
            if line is None:
                project_devices = await Project.objects.select_related(["devices", "devices__events"]).filter(name=project, devices__name=device_name).all()
            else:
                project_devices = await Project.objects.select_related(["devices", "devices__events"]).filter(name=project, devices__name=device_name, devices__line=line).all()

        devices = project_devices[0].devices
        # dr = pd.date_range(
        # first_data_date, datetime.datetime.now().date(), freq='2M').astype(str)
        dr_day = pd.date_range(start_time, end_time).astype(str)
        dr_week = pd.date_range(start_time, end_time,freq='7D').astype(str)
        if select_type == "day":
            for date in dr_day:
                actual_check = []
                predict_check = []
                for dvs in devices:
                    events = dvs.events
                    for event in events:
                        checkPredEvent = await PredictResult.objects.filter(event=event.id,pred_type=0).order_by('-pred_date').limit(1).get_or_none()

                        # check
                        if checkPredEvent is None:
                            continue
                        
                        data = await PredictResult.objects.filter(event=event.id,pred_date=date,pred_type=0).select_related("device").order_by('-pred_date').limit(1).get_or_none()
                        if data is None:
                            continue
                        if data.last_happened_check is True:
                            if data.pred == '0':
                                predict_check.append(0)
                            else:
                                predict_check.append(1)
                            if data.last_happened is None:
                                actual_check.append(0)
                            else:
                                actual_check.append(1)
                    accuracy = (np.array(actual_check) == np.array(predict_check)).mean()
                    if len(predict_check) != 0 and len(actual_check) != 0 :
                        formatData.append({
                            "id":data.id,
                            "projectName":project,
                            "deviceName":dvs.name,
                            "line":dvs.line,
                            "date":date,
                            "accuracyDate": accuracy,
                            "trend":"查看"
                        })

        else:
            for date in dr_week:
                actual_check = []
                predict_check = []
                for dvs in devices:
                    events = dvs.events
                    for event in events:
                        checkPredEvent = await PredictResult.objects.filter(event=event.id,pred_type=1).order_by('-pred_date').limit(1).get_or_none()

                        # check
                        if checkPredEvent is None:
                            continue
                        
                        data = await PredictResult.objects.filter(event=event.id,pred_date=date,pred_type=1).select_related("device").order_by('-pred_date').limit(1).get_or_none()
                        if data is None:
                            raise HTTPException(status_code=400,detail=f"can not find data")
                        if data.last_happened_check is True:
                            if data.pred == '0':
                                predict_check.append(0)
                            else:
                                predict_check.append(1)
                            if data.last_happened is None:
                                actual_check.append(0)
                            else:
                                actual_check.append(1)
                    accuracy = (np.array(actual_check) == np.array(predict_check)).mean()
                    if len(predict_check) != 0 and len(actual_check) != 0 :
                        formatData.append({
                            "id":data.id,
                            "projectName":project,
                            "deviceName":dvs.name,
                            "line":dvs.line,
                            "date":date,
                            "accuracyWeek": accuracy,
                            "trend":"查看"
                        })
    return formatData
