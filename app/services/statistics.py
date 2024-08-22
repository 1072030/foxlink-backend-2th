from typing import List, Dict, Optional, Union
from fastapi.exceptions import HTTPException
from app.core.database import (
    User,
    Device,
    Project,
    ProjectEvent,
    PredictResult,
    ErrorFeature,
    TrainPerformance,
    Env,
    get_ntz_now
)
from datetime import datetime, timedelta
import pandas as pd
import numpy as np
import json

async def GetPredictResult(project_name: Optional[str] = None, line:Optional[int] = None, device_name: Optional[str] = None):
    # if project_name is None:
    project_id_list = []
    check_project_name = project_name.split(',')
    single = None
    if len(check_project_name) > 1:
        project_id_list = list(map(int, project_name.split(',')))
    else:
        try:
            single = int(check_project_name[0])
        except:
            print('not single')

    # 多個專案同時query
    if len(project_id_list) >= 2:
        data = await Project.objects.filter(id__in=project_id_list).select_related(['devices', 'devices__events']).all()
    # 單一專案查詢
    else:
        if device_name is not None:
            data = await Project.objects.filter(id=single,devices__line = line,devices__name=device_name).select_related(['devices', 'devices__events']).all()
        elif line is not None:
            data = await Project.objects.filter(id=single,devices__line = line).select_related(['devices', 'devices__events']).all()
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
            checkPredEvent = await PredictResult.objects.filter(device=dvs.id,event=event.id).order_by('-id').limit(1).get_or_none()

            # check
            if checkPredEvent is None:
                continue
            # 不用select_related 是因為query很慢
            firstResultData_week = await PredictResult.objects.filter(device=dvs.id, event=event.id, pred_type=1).order_by('-id').limit(1).get_or_none()
            firstResultData_day = await PredictResult.objects.filter(device=dvs.id, event=event.id, pred_type=0).order_by('-id').limit(1).get_or_none()
            # firstResultData_week = await PredictResult.objects.filter(device=dvs.id, event=event.id, pred_type=1,event__trainperformances__freq="week").select_related(['event','event__trainperformances']).order_by('-pred_date').limit(1).get_or_none()
            # firstResultData_day = await PredictResult.objects.filter(device=dvs.id, event=event.id, pred_type=0,event__trainperformances__freq="day").select_related(['event','event__trainperformances']).order_by('-pred_date').limit(1).get_or_none()
            firstResultData_week_trainperformances = await TrainPerformance.objects.filter(device=dvs.id, event=event.id, freq="week").order_by('-id').limit(1).get_or_none()
            firstResultData_day_trainperformances = await TrainPerformance.objects.filter(device=dvs.id, event=event.id, freq="day").order_by('-id').limit(1).get_or_none()
            
            if firstResultData_week_trainperformances.arf > firstResultData_day_trainperformances.arf:
                getAllFirstResultData.append(firstResultData_week)
            else:
                getAllFirstResultData.append(firstResultData_day)


    threshold = await Env.objects.filter(key="threshold").get_or_none()
    if threshold is None:
        raise HTTPException(status_code=400, detail="cannot find 'threshold' env settings")
    formatData = {}
    with open('happened.json','r') as happened_json:
        happened_ori_data = json.load(happened_json)
        
    for result in getAllFirstResultData:
        if result is None:
            continue
        for i in devices:
            if result.device.id == i.id:
                # project name
                dvs_project_name = " ".join(
                    (i.project.name).split(" ")).upper()
                
                # device name
                dvs_name = i.name
                dvs_line = i.line
                # format output
                # Example output:
                # "D7X E75": { "Device_5":[]}
                if dvs_project_name not in formatData.keys():
                    formatData[dvs_project_name] = {}
                if dvs_name not in formatData[dvs_project_name].keys():
                    formatData[dvs_project_name][dvs_name] = []

                pred_type = "週預測" if result.pred_type == 1 else "日預測"

                try:
                    happened = next((i for i in happened_ori_data["data"] if i["event_id"] == result.event.id),None)
                except:
                    # happened["recently"] = "can not find recently data"
                    # happened["happened"] = 0
                    happened = {
                        "recently":"can not find recently data",
                        "happened": 0
                    }

                # check arf value 
                freq = "week" if result.pred_type == 1 else "day"
                trainperformances = await TrainPerformance.objects.filter(device=result.device.id, event=result.event.id, freq=freq).order_by('-id').limit(1).get_or_none()
                event_data = await ProjectEvent.objects.filter(id=result.event.id).get_or_none()

                formatData[dvs_project_name][dvs_name].append({
                    'id': result.id,
                    'name': event_data.name,
                    'category':event_data.category,
                    'steady': int(result.pred), # steady  
                    'ori_date': result.ori_date.date().strftime("%m-%d"),
                    'pred_date':result.pred_date.date().strftime("%m-%d"),
                    'frequency': pred_type,
                    'happenLastTime': happened["recently"],
                    'happened_times':happened["happened"],
                    'line':dvs_line,
                    'faithful': True if trainperformances.arf > float(threshold.value) else False
                })
    return formatData

# 將主畫面所需資料進行處理並存於json檔案中
# 主要是/foxlink/daemon.py 裡面使用的function
async def HomePagePreProcessing():
    # 取得所有專案的資料(devices和events)
    projects = await Project.objects.select_related(["devices","devices__events"]).all()
    # 回傳資料格式
    format_data = {}
    allFirstResultData = []

    # 取得發生次數json file
    with open('happened.json','r') as happened_json:
        happened_ori_data = json.load(happened_json)
    
    # 開始進行資料彙整
    for project in projects:

        # 以專案名稱來當作key值
        if project.name not in format_data.keys():
            format_data[project.name] = {}
        
        # 取得所有不重複的線號
        devices = project.devices
        devices_line = set([device.line for device in devices])
        
        # 以線號當作key值
        for line in devices_line:
            if line not in format_data[project.name].keys():
                format_data[project.name][line] = {}
        
        # 以機台來查詢事件是否經過預測
        for dvs in devices:
            # 取得所有此機台的事件
            events = dvs.events
            for event in events:

                # 確認此事件有被預測
                checkPredEvent = await PredictResult.objects.filter(device=dvs.id,event=event.id).order_by('-id').limit(1).get_or_none()

                # check
                if checkPredEvent is None:
                    continue
                
                # 取得最新的預測資料
                firstResultData_week = await PredictResult.objects.filter(device=dvs.id, event=event.id, pred_type=1).order_by('-id').limit(1).get_or_none()
                firstResultData_day = await PredictResult.objects.filter(device=dvs.id, event=event.id, pred_type=0).order_by('-id').limit(1).get_or_none()
                
                # 取得此事件的訓練內容
                firstResultData_week_trainperformances = await TrainPerformance.objects.filter(device=dvs.id, event=event.id, freq="week").order_by('-id').limit(1).get_or_none()
                firstResultData_day_trainperformances = await TrainPerformance.objects.filter(device=dvs.id, event=event.id, freq="day").order_by('-id').limit(1).get_or_none()
                
                # arf來判斷是該事件為日預測或週預測
                if firstResultData_week_trainperformances.arf > firstResultData_day_trainperformances.arf:
                    allFirstResultData.append(firstResultData_week)
                else:
                    allFirstResultData.append(firstResultData_day)

            if len(allFirstResultData) != 0:
                # -- 儲存資料變數
                total_day_stable = []
                total_day_unstable = []
                total_week_stable = []
                total_week_unstable = []
                # -- 儲存資料變數
                day_stable_happened = 0
                day_unstable_happened = 0
                week_stable_happened = 0
                week_unstable_happened = 0
                # -- 
                for data in allFirstResultData:
                    # 確認此事件是否發生
                    check_happened = None
                    for happened_data in happened_ori_data["data"]:
                        if data.event.id == happened_data["event_id"]:
                            if happened_data["happened"] != 0:
                                check_happened = True
                            else:
                                check_happened = False

                    # 日穩定
                    if data.pred_type == False and data.pred == '0':
                        total_day_stable.append({f"{data.event.id}":check_happened})
                        if check_happened == True:
                            day_stable_happened += 1
                    # 日異常
                    elif data.pred_type == False and data.pred == '1':
                        total_day_unstable.append({f"{data.event.id}":check_happened})
                        if check_happened == True:
                            day_unstable_happened += 1
                    # 週穩定
                    elif data.pred_type == True and data.pred == '0':
                        total_week_stable.append({f"{data.event.id}":check_happened})
                        if check_happened == True:
                            week_stable_happened += 1
                    # 週異常
                    else:
                        total_week_unstable.append({f"{data.event.id}":check_happened})
                        if check_happened == True:
                            week_unstable_happened += 1

            # 以"機台英文名稱@機台中文名稱"當作key值
            if dvs.name not in format_data[project.name][dvs.line].keys():
                format_data[project.name][dvs.line][dvs.name + "@" + dvs.cname] = {}

            # 回傳格式
            format_data[project.name][dvs.line][dvs.name + "@" + dvs.cname] = {
                "event_ids": total_day_stable + total_day_unstable + total_week_stable + total_week_unstable,
                "total_day_stable": len(total_day_stable) + len(total_day_unstable),
                "total_day_happened": day_stable_happened + day_unstable_happened,
                "total_week_stable": len(total_week_stable) + len(total_week_unstable),
                "total_week_happened": week_stable_happened + week_unstable_happened,
                "day_stable": len(total_day_stable),
                "day_stable_happened":day_stable_happened,
                "day_unstable":len(total_day_unstable),
                "day_unstable_happened":day_unstable_happened,
                "week_stable":len(total_week_stable),
                "week_stable_happened":week_stable_happened,
                "week_unstable":len(total_week_unstable),
                "week_unstable_happened" : week_unstable_happened
            }
    # 儲存於homepage.json file
    with open('homepage.json','w') as jsonfile:
        result = {
            "data":format_data,
            "timestamp":f'{get_ntz_now()+timedelta(hours=8)}'
        }
        json.dump(result,jsonfile)

    # 詳細資料可以到homepage.json查看
    # example output:
    # {
    #   "data":{
    #       "專案名稱":{
    #           "線號":{
    #               "機台英文名稱@機台中文名稱":{
    #                   "event_ids": List,
    #                   "total_day_count": int ,
    #                   "total_week_count": int,
    #                   "day_stable": int ,
    #                   "day_unstable":int ,
    #                   "week_stable": int,
    #                   "week_unstable": int
    #               }
    #           }
    #       }
    #   }
    # }
    return

async def GetHomePageData(project_name_list:List):
    with open('homepage.json','r') as home_page_data:
        home_page_data = json.load(home_page_data)     

    all_projects = home_page_data["data"].keys()
    format_data = {}

    for i in project_name_list:
        if i in all_projects:
            format_data[i] = home_page_data["data"][i]
    return format_data

async def GetPredictCompareSearch(project_name: List, select_type: str, line: int, start_time: datetime, end_time: datetime):
    formatData = []
    threshold = await Env.objects.filter(key="threshold").get_or_none()
    if threshold is None:
        raise HTTPException(status_code=400, detail="cannot find 'threshold' env settings")
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
                # actual_check = []
                # predict_check = []
                total_accuracy = []
                devices_detail = {}
                for dvs in devices:
                    actual_check = []
                    predict_check = []
                    events = dvs.events
                    for event in events:
                        # checkPredEvent = await PredictResult.objects.filter(event=event.id,pred_type=0).order_by('-pred_date').limit(1).get_or_none()

                        # # check
                        # if checkPredEvent is None:
                        #     continue

                        data = await PredictResult.objects.filter(event=event.id, pred_date=date, pred_type=0).select_related("device").order_by('-pred_date').limit(1).get_or_none()
                        if data is None:
                            continue

                        error_feature = await ErrorFeature.objects.filter(event=event.id, date=date).order_by('-date').limit(1).get_or_none()
                        if error_feature is None:
                            continue

                        train_performance = await TrainPerformance.objects.filter(event=event.id,freq=select_type).get_or_none()
                        if train_performance is None:
                            continue

                        faithful = 0
                        if train_performance.arf >= float(threshold.value):
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
                    # print(predict_check)
                    # print(actual_check)
                    device_accuracy = (np.array(actual_check)
                                       == np.array(predict_check)).mean()
                    if len(predict_check) == 0 and len(actual_check) == 0:
                        continue
                    devices_detail[dvs.name]["device_accuracy"] = device_accuracy

                    total_accuracy.append(device_accuracy)

                device_accuracy = (np.array(total_accuracy)).mean()
                if len(total_accuracy) != 0:
                    formatData.append({
                        "id": None,
                        "projectName": project,
                        "line": dvs.line,
                        "date": date,
                        "accuracyDate": device_accuracy,
                        "devices": devices_detail,
                    })

        else:
            for date in dr_week:
                date_check = datetime.strptime(date,"%Y-%m-%d")
                next_day = (date_check + timedelta(days=7)).strftime("%Y-%m-%d")
                # actual_check = []
                # predict_check = []
                total_accuracy = []
                devices_detail = {}
                for dvs in devices:
                    actual_check = []
                    predict_check = []
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
                        if train_performance.arf >= float(threshold.value):
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
                if len(total_accuracy) != 0:
                    formatData.append({
                        "id": None,
                        "projectName": project,
                        "line": dvs.line,
                        "date": actual_predict_date.date(),
                        "accuracyDate": device_accuracy,
                        "devices": devices_detail,
                    })
                    
    return formatData


async def GetPredictCompareAnalysis(project_name, line, select_type, start_date, end_date):
    formatData = []
    threshold = await Env.objects.filter(key="threshold").get_or_none()
    if threshold is None:
        raise HTTPException(status_code=400, detail="cannot find 'threshold' env settings")
    data = await Project.objects.filter(name=project_name).select_related(["devices", "devices__events"]).filter(devices__line=line).all()

    devices = data[0].devices

    dr_day = pd.date_range(start_date, end_date).astype(str)
    dr_week = pd.date_range(start_date, end_date, freq='7D').astype(str)
    predict_check = []
    actual_check = []
    if select_type == "day":
        for date in dr_day:

            # actual_check = []
            # predict_check = []
            total_accuracy = []
            devices_detail = {}

            for dvs in devices:
                if dvs.line != int(line):
                    continue
                events = dvs.events
                actual_check = []
                predict_check = []                
                for event in events:

                    data = await PredictResult.objects.filter(event=event.id, pred_date=date, pred_type=0).select_related("device").order_by('-pred_date').limit(1).get_or_none()
                    if data is None:
                        continue

                    # error_feature = await ErrorFeature.objects.filter(event=event.id, date=date).get_or_none()
                    error_feature = await ErrorFeature.objects.filter(event=event.id, date=date).order_by('-date').limit(1).get_or_none()
                    if error_feature is None:
                        continue

                    train_performance = await TrainPerformance.objects.filter(event=event.id,freq=select_type).get_or_none()
                    if train_performance is None:
                        continue

                    faithful = 0
                    if train_performance.arf >= float(threshold.value):
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
                "value": str(device_accuracy)
                # "value": '%.2f' % device_accuracy,
            })
    else:
        for date in dr_week:
            # year = int(date.split('-')[0])
            # month = int(date.split('-')[1])
            # day = int(date.split('-')[2])
            # print(date)
            date_check = datetime.strptime(date,"%Y-%m-%d")
            next_day = (date_check + timedelta(days=7)).strftime("%Y-%m-%d")
            # actual_check = []
            # predict_check = []
            total_accuracy = []
            devices_detail = {}
            for dvs in devices:
                events = dvs.events
                actual_check = []
                predict_check = []
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
                    if train_performance.arf >= float(threshold.value):
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
                # "date": date,
                # "value": str(device_accuracy)
                # "date": actual_predict_date,
                "date": date,
                "value": str(device_accuracy),
            })
            
    return formatData
