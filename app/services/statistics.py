from typing import List, Dict, Optional, Union
from fastapi.exceptions import HTTPException
from app.core.database import (
    User,
    Device,
    Project,
    PredictResult,
    ErrorFeature,
    TrainPerformance,
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


async def GetPredictCompareSearch(project_name: List, select_type: str, line: int, start_time: datetime, end_time: datetime):
    formatData = []
    for project in project_name:

        if line is None:
            project_devices = await Project.objects.select_related(["devices", "devices__events"]).filter(name=project).all()
        else:
            project_devices = await Project.objects.select_related(["devices", "devices__events"]).filter(name=project, devices__line=line).all()

        if len(project_devices) == 0:
            raise HTTPException(
                status_code=400, detail="cannot find any events")

        devices = project_devices[0].devices

        dr_day = pd.date_range(start_time, end_time).astype(str)
        dr_week = pd.date_range(start_time, end_time, freq='7D').astype(str)
        if select_type == "day":
            for date in dr_day:
                actual_check = []
                predict_check = []
                total_accuracy = []
                devices_detail = {}
                for dvs in devices:
                    events = dvs.events
                    for event in events:
                        # checkPredEvent = await PredictResult.objects.filter(event=event.id,pred_type=0).order_by('-pred_date').limit(1).get_or_none()

                        # # check
                        # if checkPredEvent is None:
                        #     continue

                        data = await PredictResult.objects.filter(event=event.id, pred_date=date, pred_type=0).select_related("device").order_by('-pred_date').limit(1).get_or_none()
                        if data is None:
                            continue

                        error_feature = await ErrorFeature.objects.filter(event=event.id, date=date).get_or_none()
                        if error_feature is None:
                            continue

                        train_performance = await TrainPerformance.objects.filter(event=event.id).get_or_none()
                        if train_performance is None:
                            continue

                        faithful = 0
                        if train_performance.arf >= 0.6:
                            faithful = 1

                        if faithful:
                            if data.pred == '0':
                                predict_check.append(0)
                            else:
                                predict_check.append(1)

                            if error_feature.happened <= train_performance.actual_cutpoint:
                                actual_check.append(0)
                            else:
                                actual_check.append(1)

                        if dvs.name not in devices_detail.keys():
                            devices_detail[dvs.name] = {
                                "events": [], "device_accuracy": 0}

                        devices_detail[dvs.name]["cname"] = dvs.cname
                        devices_detail[dvs.name]["events"].append({
                            "category": event.category,
                            "name": event.name,
                            "predict": int(data.pred),
                            "true": error_feature.happened,
                            "faithful": faithful
                        })

                    # per day event accuracy
                    device_accuracy = (np.array(actual_check)
                                       == np.array(predict_check)).mean()
                    if len(predict_check) == 0 and len(actual_check) == 0:
                        continue
                    devices_detail[dvs.name]["device_accuracy"] = device_accuracy

                    total_accuracy.append(device_accuracy)

                device_accuracy = (np.array(total_accuracy)).mean()
                if len(predict_check) != 0 and len(actual_check) != 0:
                    formatData.append({
                        "id": None,
                        "projectName": project,
                        "line": dvs.line,
                        "date": date,
                        "accuracyDate": '%.2f' % device_accuracy,
                        "devices": devices_detail,
                    })

        else:
            for date in dr_week:
                year = int(date.split('-')[0])
                month = int(date.split('-')[1])
                day = int(date.split('-')[2])
                next_day = f"{year}-{month}-{day+7}"
                actual_check = []
                predict_check = []
                total_accuracy = []
                devices_detail = {}
                for dvs in devices:
                    events = dvs.events
                    for event in events:
                        data = await PredictResult.objects.filter(event=event.id, ori_date__gte=date,ori_date__lte=next_day, pred_type=1).select_related("device").order_by('-pred_date').limit(1).get_or_none()
                        if data is None:
                            continue

                        error_features = await ErrorFeature.objects.filter(event=event.id, date__gte=date,date__lte=next_day).all()
                        if len(error_features) == 0:
                            continue
                        total_happened = sum([feature.happened for feature in error_features])
                        
                        train_performance = await TrainPerformance.objects.filter(event=event.id,freq=select_type).get_or_none()
                        if train_performance is None:
                            continue

                        faithful = 0
                        if train_performance.arf >= 0.6:
                            faithful = 1

                        if faithful:
                            if data.pred == '0':
                                predict_check.append(0)
                            else:
                                predict_check.append(1)

                            if total_happened <= train_performance.actual_cutpoint:
                                actual_check.append(0)
                            else:
                                actual_check.append(1)

                            if dvs.name not in devices_detail.keys():
                                devices_detail[dvs.name] = {
                                    "events": [], "device_accuracy": 0}

                        actual_predict_date = data.ori_date

                        devices_detail[dvs.name]["cname"] = dvs.cname
                        devices_detail[dvs.name]["events"].append({
                            "category": event.category,
                            "name": event.name,
                            "predict": int(data.pred),
                            "true": total_happened,
                            "faithful": faithful
                        })

                    # per day event accuracy
                    device_accuracy = (np.array(actual_check)
                                       == np.array(predict_check)).mean()
                    if len(predict_check) == 0 and len(actual_check) == 0:
                        continue
                    devices_detail[dvs.name]["device_accuracy"] = device_accuracy

                    total_accuracy.append(device_accuracy)
                device_accuracy = (np.array(total_accuracy)).mean()
                if len(predict_check) != 0 and len(actual_check) != 0:
                    formatData.append({
                        "id": None,
                        "projectName": project,
                        "line": dvs.line,
                        "date": actual_predict_date.date(),
                        "accuracyDate": '%.2f' % device_accuracy,
                        "devices": devices_detail,
                    })

    return formatData


async def GetPredictCompareAnalysis(project_name, line, select_type, start_date, end_date):
    formatData = []
    data = await Project.objects.filter(name=project_name).select_related(["devices", "devices__events"]).filter(devices__line=line).all()

    devices = data[0].devices

    dr_day = pd.date_range(start_date, end_date).astype(str)
    dr_week = pd.date_range(start_date, end_date, freq='7D').astype(str)
    predict_check = []
    actual_check = []
    if select_type == "day":
        for date in dr_day:

            actual_check = []
            predict_check = []
            total_accuracy = []
            devices_detail = {}

            for dvs in devices:
                if dvs.line != int(line):
                    continue
                events = dvs.events
                for event in events:

                    data = await PredictResult.objects.filter(event=event.id, pred_date=date, pred_type=0).select_related("device").order_by('-pred_date').limit(1).get_or_none()
                    if data is None:
                        continue

                    error_feature = await ErrorFeature.objects.filter(event=event.id, date=date).get_or_none()
                    if error_feature is None:
                        continue

                    train_performance = await TrainPerformance.objects.filter(event=event.id,freq=select_type).get_or_none()
                    if train_performance is None:
                        continue

                    faithful = 0
                    if train_performance.arf >= 0.6:
                        faithful = 1

                    if faithful:
                        if data.pred == '0':
                            predict_check.append(0)
                        else:
                            predict_check.append(1)

                        if error_feature.happened <= train_performance.actual_cutpoint:
                            actual_check.append(0)
                        else:
                            actual_check.append(1)

                    if dvs.name not in devices_detail.keys():
                        devices_detail[dvs.name] = {"device_accuracy": 0}

                    devices_detail[dvs.name]["cname"] = dvs.cname

                # per day event accuracy
                device_accuracy = (np.array(actual_check) ==
                                   np.array(predict_check)).mean()
                if len(predict_check) == 0 and len(actual_check) == 0:
                    continue
                devices_detail[dvs.name]["device_accuracy"] = device_accuracy

                total_accuracy.append(device_accuracy)

            device_accuracy = (np.array(total_accuracy)).mean()
            formatData.append({
                "date": date,
                "value": device_accuracy
            })
    else:
        for date in dr_week:
            year = int(date.split('-')[0])
            month = int(date.split('-')[1])
            day = int(date.split('-')[2])
            next_day = f"{year}-{month}-{day+7}"
            actual_check = []
            predict_check = []
            total_accuracy = []
            devices_detail = {}
            for dvs in devices:
                events = dvs.events
                for event in events:
                    data = await PredictResult.objects.filter(event=event.id, ori_date__gte=date,ori_date__lte=next_day, pred_type=1).select_related("device").order_by('-pred_date').limit(1).get_or_none()
                    if data is None:
                        continue

                    error_features = await ErrorFeature.objects.filter(event=event.id, date__gte=date,date__lte=next_day).all()
                    if len(error_features) == 0:
                        continue
                    total_happened = sum([feature.happened for feature in error_features])
                    train_performance = await TrainPerformance.objects.filter(event=event.id,freq=select_type).get_or_none()
                    if train_performance is None:
                        continue

                    faithful = 0
                    if train_performance.arf >= 0.6:
                        faithful = 1

                    if faithful:
                        if data.pred == '0':
                            predict_check.append(0)
                        else:
                            predict_check.append(1)

                        if total_happened <= train_performance.actual_cutpoint:
                            actual_check.append(0)
                        else:
                            actual_check.append(1)

                    # data = await PredictResult.objects.filter(event=event.id, ori_date__gte=date, ori_date__lte=next_day, pred_type=1).select_related("device").order_by('-pred_date').limit(1).get_or_none()

                    actual_predict_date = data.ori_date


                    if dvs.name not in devices_detail.keys():
                        devices_detail[dvs.name] = {"device_accuracy": 0}
                    devices_detail[dvs.name]["cname"] = dvs.cname
                        
                # per day event accuracy
                device_accuracy = (np.array(actual_check) ==
                                   np.array(predict_check)).mean()
                if len(predict_check) == 0 and len(actual_check) == 0:
                    continue
                devices_detail[dvs.name]["device_accuracy"] = device_accuracy

                total_accuracy.append(device_accuracy)
            device_accuracy = (np.array(total_accuracy)).mean()
            formatData.append({
                "date": date,
                "value": device_accuracy
            })
            
    return formatData
