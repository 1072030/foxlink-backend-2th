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
from app.foxlink.db import (
    foxlink_dbs
)
from datetime import datetime, timedelta
import pandas as pd
import numpy as np
import json
import gc

ntust_engine = foxlink_dbs.ntust_db

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
                    # happened = next((i for i in happened_ori_data["data"] if i["event_id"] == result.event.id),None)
                    happened = next((event for sublist in happened_ori_data["data"] for event in sublist if event["event_id"] == result.event.id), None)

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
            # get line real names
            real_name = await foxlink_dbs.get_real_line_names(project.name,line)
            line_name_combine = f"{line}@{real_name}"
            if line_name_combine not in format_data[project.name].keys():
                format_data[project.name][line_name_combine] = {}
        
        # 以機台來查詢事件是否經過預測
        for dvs in devices:
            # 取得所有此機台的事件
            events = dvs.events
            real_name = await foxlink_dbs.get_real_line_names(project.name,dvs.line)
            # for key value
            output_line_format = f"{dvs.line}@{real_name}"
            output_device_format = f"{dvs.name}@{dvs.cname}"
            # 
            allFirstResultData = []
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
            if len(allFirstResultData) != 0:
                for data in allFirstResultData:
                    # 確認此事件是否發生
                    check_happened = None
                    for happened_data in happened_ori_data["data"]:
                        for happened in happened_data:
                            if data.event.id == happened["event_id"]:
                                if happened["happened"] != 0:
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
            else:
                continue
            # 以"機台英文名稱@機台中文名稱"當作key值
            if output_device_format not in format_data[project.name][output_line_format].keys():
                format_data[project.name][output_line_format][output_device_format] = {}

            # 回傳格式
            format_data[project.name][output_line_format][output_device_format] = {
                "event_ids": total_day_stable + total_day_unstable + total_week_stable + total_week_unstable,
                "total_stable": len(total_day_stable) + len(total_week_stable),
                "total_unstable": len(total_day_unstable) + len(total_week_unstable),

                "total_stable_happened": day_stable_happened + week_stable_happened,
                "total_unstable_happened": day_unstable_happened + week_unstable_happened,

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
    #           "線號@實體線號名稱":{
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
    format_data = {"data":{}}

    for i in project_name_list:
        if i in all_projects:
            format_data["data"][i] = home_page_data["data"][i]
    format_data["timestamp"] = home_page_data["timestamp"]
    return format_data

async def GetPredictCompareSearch(project_name: List, select_type: str, line: int, start_time: datetime, end_time: datetime):
    formatData = []
  
    threshold = await Env.objects.filter(key="threshold").get_or_none()
    if threshold is None:
        raise HTTPException(status_code=400, detail="cannot find 'threshold' env settings")


    for project in project_name:
        if line is None:
            project_devices = await Project.objects.prefetch_related("devices__events").filter(name=project).all()
        else:
            project_devices = await Project.objects.prefetch_related("devices__events").filter(name=project, devices__line=line).all()

        if len(project_devices) == 0:
            raise HTTPException(status_code=400, detail="cannot find any events")

        if select_type == "day":
            pred_type = 0
            date_range = pd.date_range(start_time, end_time).astype(str)
        elif select_type == "week":
            pred_type = 1
            date_range = pd.date_range(start_time, end_time, freq='D')[pd.date_range(start_time, end_time, freq='D').dayofweek == 5].astype(str)


        devices = project_devices[0].devices

        # 提前批量查询 PredictResult, ErrorFeature 和 TrainPerformance
        events = [event.id for dvs in devices for event in dvs.events]
        sql = f"""
            SELECT p.*
            FROM predict_results p
            WHERE p.event IN ({','.join(map(str, events))})
            AND p.pred_date IN ({','.join([f"'{d}'" for d in date_range])})  
            AND p.pred_type = {pred_type}
            ORDER BY p.pred_date;
        """

        ntust_engine = foxlink_dbs.ntust_db
        predict_results = pd.read_sql(sql, ntust_engine)


        # predict_results = await PredictResult.objects.filter(event__in=[event.id for dvs in devices for event in dvs.events], pred_date__in=date_range,pred_type=pred_type
                                                                # ).select_related("device").all()
        error_features = await ErrorFeature.objects.filter(event__in=[event.id for dvs in devices for event in dvs.events], date__in=date_range).all()
        train_performances = await TrainPerformance.objects.filter(event__in=[event.id for dvs in devices for event in dvs.events], freq=select_type).all()
        
        predict_results_dict = {(row['event'], row['pred_date']): row for index, row in predict_results.iterrows()}
        predict_results_dict_check = {(row['device'], row['pred_date']): row for index, row in predict_results.iterrows()}

        
        # predict_results_dict_check = {(res.device,res.pred_date): res for res in predict_results}
        error_features_dict = {(err.event.id, err.date): err for err in error_features}
        train_performances_dict = {tp.event.id: tp for tp in train_performances}

        # 根據選擇類型，進行每日或每週處理
        # date_range = dr_day if select_type == "day" else dr_week
        for date_str in date_range:
            date = datetime.strptime(date_str, '%Y-%m-%d')
            total_accuracy = []
            devices_detail = {}
            
            for dvs in devices:
                
                predict_check = predict_results_dict_check.get((dvs.id,date))

                if predict_check is None:
                    continue
                actual_check = []
                predict_check = []
    
                events = dvs.events

                for event in events:
                    
                    data = predict_results_dict.get((event.id, date))
                    error_feature = error_features_dict.get((event.id, date))
                    train_performance = train_performances_dict.get(event.id)

                    # 如果沒有相關數據跳過
                    if data is None or error_feature is None or train_performance is None:
                        continue

                    # 根據 arf 值來判斷 faithful
                    faithful = int(train_performance.arf >= float(threshold.value))

                    if faithful:
                        predict_check.append(1 if data.pred != '0' else 0)
                        actual_check.append(1 if error_feature.happened > train_performance.actual_cutpoint else 0)

                    if dvs.name not in devices_detail:
                        devices_detail[dvs.name] = {"events": [], "device_accuracy": 0, "cname": dvs.cname}
                    
                    # 添加事件細節
                    devices_detail[dvs.name]["events"].append({
                        "category": event.category,
                        "name": event.name,
                        "predict": int(data.pred),
                        "true": error_feature.happened,
                        "faithful": faithful
                    })

                # 計算設備的準確度
                if len(predict_check) > 0 and len(actual_check) > 0:
                    device_accuracy = (np.array(actual_check) == np.array(predict_check)).mean()
                    devices_detail[dvs.name]["device_accuracy"] = device_accuracy
                    total_accuracy.append(device_accuracy)

            # 如果有準確度數據，則添加到結果中
            if len(total_accuracy) != 0:
                avg_accuracy = np.mean(total_accuracy)
                formatData.append({
                    "id": None,
                    "projectName": project,
                    "line": dvs.line if devices else None,
                    "date": date_str,
                    "accuracyDate": avg_accuracy,
                    "devices": devices_detail,
                })

    return formatData


async def GetPredictCompareAnalysis(project_name, line, select_type, start_date, end_date):
    formatData = []
    
    # 提前查询 threshold 数据
    threshold = await Env.objects.filter(key="threshold").get_or_none()
    if threshold is None:
        raise HTTPException(status_code=400, detail="cannot find 'threshold' env settings")
    
    # 获取项目相关设备及事件数据
    data = await Project.objects.filter(name=project_name).select_related("devices__events").filter(devices__line=line).all()

    if len(data) == 0:
        raise HTTPException(status_code=400, detail="cannot find any events")
    
    devices = data[0].devices

    # 根據 select_type 設置 pred_type
    if select_type == "day":
        pred_type = 0
        date_range = pd.date_range(start_date, end_date).astype(str)
    else:
        pred_type = 1
        date_range = pd.date_range(start_date, end_date, freq='D')[pd.date_range(start_date, end_date, freq='D').dayofweek == 5].astype(str)


    # 提前批量查询 PredictResult, ErrorFeature 和 TrainPerformance
    events = [event.id for dvs in devices for event in dvs.events]
    sql = f"""
        SELECT p.*
        FROM predict_results p
        WHERE p.event IN ({','.join(map(str, events))})
        AND p.pred_date IN ({','.join([f"'{d}'" for d in date_range])})  
        AND p.pred_type = {pred_type}
        ORDER BY p.pred_date;
    """

    ntust_engine = foxlink_dbs.ntust_db
    predict_results = pd.read_sql(sql, ntust_engine)

    error_features = await ErrorFeature.objects.filter(
        event__in=[event.id for dvs in devices for event in dvs.events],
        date__in=date_range 
    ).all()

    train_performances = await TrainPerformance.objects.filter(
        event__in=[event.id for dvs in devices for event in dvs.events],
        freq=select_type
    ).all()

    # 组织数据为字典形式，加快查找速度
    predict_results_dict = {(row['event'], row['pred_date']): row for index, row in predict_results.iterrows()}
    predict_results_dict_check = {(row['device'], row['pred_date']): row for index, row in predict_results.iterrows()}

    # predict_results_dict = {(res.event.id, res.pred_date): res for res in predict_results}
    error_features_dict = {(err.event.id, err.date): err for err in error_features}
    train_performances_dict = {tp.event.id: tp for tp in train_performances}

    # 根据选择的时间范围进行逐日或逐周的分析
    for date_str in date_range:
        date = datetime.strptime(date_str, '%Y-%m-%d')
        total_accuracy = []

        for dvs in devices:
            predict_check = predict_results_dict_check.get((dvs.id,date))

            if predict_check is None:
                continue
            actual_check = []
            predict_check = []
            events = dvs.events

            for event in events:
                # 从字典中获取预预测结果、错误特征和训练性能
                data = predict_results_dict.get((event.id, date))
                error_feature = error_features_dict.get((event.id, date))
                train_performance = train_performances_dict.get(event.id)

                # 如果相关数据没有找到，跳过当前事件
                if data is None or error_feature is None or train_performance is None:
                    continue

                # 根据训练性能的 ARF 值判断是否有效
                faithful = int(train_performance.arf >= float(threshold.value))

                if faithful:
                    predict_check.append(1 if data.pred != '0' else 0)
                    actual_check.append(1 if error_feature.happened > train_performance.actual_cutpoint else 0)

            # 计算设备的准确度
            if len(predict_check) > 0 and len(actual_check) > 0:
                device_accuracy = (np.array(actual_check) == np.array(predict_check)).mean()
                total_accuracy.append(device_accuracy)

        # 如果有准确度数据，加入最终结果
        if len(total_accuracy) != 0:
            avg_accuracy = np.mean(total_accuracy)
            formatData.append({
                "date": date_str,
                "value": str(avg_accuracy)
            })

    return formatData

