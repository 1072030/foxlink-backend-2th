from typing import List
from fastapi.exceptions import HTTPException
from datetime import date, datetime, timedelta
import pandas as pd
import numpy as np
from app.models.schema import NewProjectDto
from sqlalchemy import create_engine
from sqlalchemy.exc import SQLAlchemyError
from app.core.database import (
    transaction,
    get_ntz_now,
    User,
    Project,
    ProjectUser,
    ProjectEvent,
    UserLevel,
    Device,
    AoiMeasure,
    AoiFeature,
    PredictResult,
    AuditLogHeader,
    AuditActionEnum
)
from app.env import (
    FOXLINK_EVENT_DB_HOSTS,
    FOXLINK_EVENT_DB_USER,
    FOXLINK_EVENT_DB_PWD,
    FOXLINK_EVENT_DB_NAME,
    DATABASE_HOST,
    DATABASE_PORT,
    DATABASE_USER,
    DATABASE_PASSWORD,
    DATABASE_NAME
)
from app.foxlink.db import foxlink_dbs
from app.foxlink.train import foxlink_train
from app.foxlink.predict import foxlink_predict
import datetime
from natsort import natsort_keygen
from sqlalchemy import create_engine
# ----
from tqdm import tqdm
import joblib
# ----

FOXLINK_AOI_DATABASE = FOXLINK_EVENT_DB_HOSTS[0]+"@"+FOXLINK_EVENT_DB_NAME[0]
ntust_engine = foxlink_dbs.ntust_db
foxlink_engine = foxlink_dbs.foxlink_db

async def DeleteProject(project_id: int):
    project = await Project.objects.filter(id=project_id).get_or_none()
    if project is None:
        raise HTTPException(404, 'user is not found')
    try:
        await project.delete()
        return project.name
    except:
        raise HTTPException(400, 'project can not delete')


async def AddNewProjectWorker(project_id: int, user_id: str, permission: int = UserLevel):
    user = await User.objects.filter(badge=user_id).get_or_none()
    if user is None:
        raise HTTPException(404, 'user is not found')

    project = await Project.objects.filter(id=project_id).get_or_none()

    if project is None:
        raise HTTPException(404, 'project is not found')

    check_duplicate = await ProjectUser.objects.filter(
        project=project_id, user=user_id
    ).get_or_none()

    if check_duplicate is None:
        await ProjectUser.objects.create(
            project=project_id,
            user=user.badge,
            permission=permission
        )
        return True
    else:
        raise HTTPException(400, 'this user is already in the project')


async def RemoveProjectWorker(project_id: int, user_id: str):
    user = await User.objects.filter(badge=user_id).get_or_none()
    if user is None:
        raise HTTPException(404, 'user is not found')

    project = await Project.objects.filter(id=project_id).get_or_none()

    if project is None:
        raise HTTPException(404, 'project is not found')

    check_duplicate = await ProjectUser.objects.filter(
        project=project_id, user=user_id
    ).get_or_none()

    if check_duplicate is not None:
        await ProjectUser.objects.filter(
            project=project_id,
            user=user.badge,
        ).delete()
        return True
    else:
        raise HTTPException(
            400, 'can not delete this user in this project with some error')


async def SearchProjectDevices(project_name: str):

    return await foxlink_dbs.get_device_names(project_name=project_name)
    # project = await Project.objects.filter(name = project_name).select_related(["devices"]).get_or_none()
    # if project is None:
    #     return data
    # else:
    #     devices = [i.name for i in project.devices]
    #     for i in data:
    #         if i["device"] in devices:
    #             i["selected"] = True
    #     return data

@transaction()
async def AddNewProjectEvents(dto: List[NewProjectDto]):
    project_name = dto[0].project.upper()
    # check selected devices
    if len(dto) == 0:
        raise HTTPException(
            status_code=400, detail="please select devices")

    # foxlink db project select
    stmt = (
        f"SELECT Device_Name , Measure_Workno FROM aoi.measure_info WHERE Project = '{project_name}'"
    )
    try:
        # check query project
        await foxlink_dbs[FOXLINK_AOI_DATABASE].connect()
        device = await foxlink_dbs[FOXLINK_AOI_DATABASE].fetch_all(query=stmt)
    except:
        raise HTTPException(
            status_code=400, detail="cant query foxlink database")

    dvs_aoi = {}
    for device, measure in device:
        if device not in dvs_aoi.keys():
            dvs_aoi[device] = dvs_aoi.get(device, [])
        dvs_aoi[device].append(measure.lower())

    # check project in system duplicated
    project = await Project.objects.select_related(["devices"]).get_or_none(name=project_name)

    if len(device) != 0:
        if project is None:
            project_create = await Project.objects.create(name=project_name)
            # add admin into project
            admin = await User.objects.filter(badge='admin').get_or_none() 
            await ProjectUser.objects.create(project=project_create.id, user=admin.badge, permission=4)
        else:
            device_name_in_project = [dvs.name for dvs in project.devices]
            for i in dto:
                if i.device in device_name_in_project:
                    dto.remove(i)

            # raise HTTPException(
            #     status_code=400, detail="The project name duplicated.")
    else:
        raise HTTPException(
            status_code=400, detail="The project name is not existed.")


    event_data = {}
    for selected in dto:
        stmt = (
            f"""
            SELECT DISTINCT Device_Name,Line ,Message,Category FROM aoi.`{project_name}_event`
            where 
                Device_Name = '{selected.device}' and
                Line = {selected.line} and
                (Category >= 1 AND Category <= 199)
            ORDER BY ID DESC
            """
        )
        try:
            foxlink = await foxlink_dbs[FOXLINK_AOI_DATABASE].fetch_all(query=stmt)
            
            check_category_duplicate = []
            for i in foxlink:
                # remove dumplicate name with same category
                if i.Category not in check_category_duplicate:
                    check_category_duplicate.append(i.Category)
                else:
                    continue
                name = i.Device_Name + "-" + i.Line + "-" + selected.cname
                if name not in event_data.keys():
                    event_data[name] = event_data.get(
                        name, [{"message": i.Message, "category": i.Category}])
                else:
                    event_data[name].append(
                        {"message": i.Message, "category": i.Category})
        except:
            raise HTTPException(
                status_code=400, detail="can not connect foxlink database or sql parameter is wrong")

    # add devices and events in project
    bulk_create_device: List[Device] = []
    bulk_create_events: List[ProjectEvent] = []
    bulk_create_aoi_measure: List[AoiMeasure] = []

    for content in event_data.keys():
        device = Device(
            name=content.split('-')[0],
            line=content.split('-')[1],
            cname=content.split('-')[2],
            project=project.id,
            flag=False
        )
        bulk_create_device.append(device)

    # bulk create device
    await Device.objects.bulk_create(bulk_create_device)

    # get device detail
    new_devices = await Device.objects.filter(
        project=project.id,
        flag=0
    ).all()

    for device in new_devices:
        # check selected events
        for events in event_data[device.name + '-' + str(device.line) + '-' + device.cname]:
            event = ProjectEvent(
                device=device.id,
                name=events['message'],
                category=events['category']
            )
            bulk_create_events.append(event)

    # bulk create events
    await ProjectEvent.objects.bulk_create(bulk_create_events)

    for device in new_devices:
        for aoi_measures in dvs_aoi[device.name]:
            aoi_measure = AoiMeasure(
                device=device.id,
                name=aoi_measures,
            )
            bulk_create_aoi_measure.append(aoi_measure)

    await AoiMeasure.objects.bulk_create(bulk_create_aoi_measure)

    return project

@transaction()
async def PreprocessingData(project_id: int):

    # 工作日期 (現在時間於10/9 07:40:00 ~ 10/10 07:39:59之間，工作日期為 10/9)
    now_workday = (get_ntz_now() - pd.Timedelta(hours=7, minutes=40)).date()
    # 前一個工作日期的結束時間 (即 10/8 工作日的結束時間 : 10/9 07:40:00)
    yesterday_workday_endtime = pd.to_datetime(
        now_workday) + pd.Timedelta(hours=7, minutes=40)
    project = await Project.objects.filter(id=project_id).select_related(
        ["devices", "devices__aoimeasures"]
    ).filter(
        devices__flag=False
    ).all()

    if len(project) == 0:
        raise HTTPException(
            status_code=400, detail="this project doesnt existed.")

    hourly_mf = pd.DataFrame()
    dn_mf = pd.DataFrame()
    operation_day = {}
    aoi_feature = pd.DataFrame()

    with ntust_engine.connect() as conn:
        trans = conn.begin()
        try:
            for dvs in project[0].devices:
                for measure in dvs.aoimeasures:
                    
                    aoi = pd.DataFrame()
                    # 資料表第一筆資料

                    sql = f"SELECT * FROM `{project[0].name}_{measure.name}_data` LIMIT 1;"
                    first_data_date = await foxlink_dbs[FOXLINK_AOI_DATABASE].fetch_one(query=sql)
                    # [5] = Code3

                    # get keys
                    # print(first_data_date._fields)
                    first_data_date = first_data_date['Code3']

                    dr = pd.date_range(
                        first_data_date, datetime.datetime.now().date(), freq='2M').astype(str)

                    print(
                        f"{get_ntz_now()} : starting query {dvs.name} {measure.name} {first_data_date} to {dr[0]}")
                    sql = f"""
                            SELECT ID,Code1,Code2,Code3,Code4,Code6 FROM `{project[0].name}_{measure.name}_data`
                            WHERE 
                                (Code3 = '{str(first_data_date)}' AND Code4 >= '07:40:00') OR
                                (Code3 > '{str(first_data_date)}' AND Code3 < '{dr[0]}') OR
                                (Code3 = '{dr[0]}' AND Code4 <= '07:40:00')
                                AND Code2 < 3 ;
                            """
                    # tmp_data = await foxlink_dbs[FOXLINK_AOI_DATABASE].fetch_all(query=sql)
                    # tmp_data = foxlink_dbs.FormatDataFrame(tmp_data._fields, tmp_data)
                    tmp_data = pd.read_sql(sql, foxlink_engine)
                    aoi = aoi.append(tmp_data)

                    # 先測試三個月的 之後再進行到1年
                    for index in range(1, len(dr)):
                        sql = f"""
                            SELECT ID,Code1,Code2,Code3,Code4,Code6 FROM `{project[0].name}_{measure.name}_data`
                            WHERE 
                                (Code3 = '{dr[index-1]}' AND Code4 >= '07:40:00') OR
                                (Code3 > '{dr[index-1]}' AND Code3 < '{dr[index]}') OR
                                (Code3 = '{dr[index]}' AND Code4 <= '07:40:00')
                                AND Code2 < 3 ;
                            """
                        print(
                            f"{get_ntz_now()} : starting query {index} {dvs.name} {measure.name} {dr[index - 1]} to {dr[index]}")
                        tmp_data = pd.read_sql(sql, foxlink_engine)
                        if len(tmp_data) != 0:
                            aoi = aoi.append(tmp_data)
                    aoi = aoi[(aoi['Code2'] < 3)]

                    aoi['MF_Time'] = pd.to_datetime(aoi['Code3']) + aoi['Code4']
                    print(aoi.head())
                    aoi["Time_shift"] = aoi["MF_Time"] - \
                        pd.Timedelta(hours=7, minutes=40)  # 將早班開始時間(7:40)平移置0:00
                    # 以班別為基礎的工作日期 如2022-01-02 為 2022-01-02 7:40(早班開始) 到 2023-01-03 7:40(晚班結束)
                    aoi['date'] = aoi['Time_shift'].dt.date
                    aoi['hour'] = aoi['Time_shift'].dt.hour + \
                        1  # 工作日期的第幾個小時 1~12為早班 13~24為晚班
                    aoi['shift'] = pd.cut(aoi['hour'], bins=[0, 12, 24], labels=[
                                        'D', 'N'])  # 班別 1~12為早班(D) 13~24為晚班(N)

                    # 每小時生產資訊
                    hourly_dvs_mf = pd.DataFrame()
                    hourly_dvs_mf['time'] = pd.date_range(
                        aoi['date'].min(), now_workday, freq='h', closed='left')
                    hourly_dvs_mf['date'] = hourly_dvs_mf['time'].dt.date
                    hourly_dvs_mf['hour'] = hourly_dvs_mf['time'].dt.hour+1
                    hourly_dvs_mf['shift'] = pd.cut(hourly_dvs_mf['hour'], bins=[
                                                    0, 12, 24], labels=['D', 'N'])
                    hourly_dvs_mf.drop('time', axis=1, inplace=True)

                    hourly_dvs_mf = pd.merge(hourly_dvs_mf, aoi.groupby(['date', 'hour']).ID.count(
                    ).reset_index().rename(columns={'ID': 'pcs'}), on=['date', 'hour'], how='outer')  # 生產量
                    hourly_dvs_mf = pd.merge(hourly_dvs_mf, aoi[aoi['Code2'] == 0].groupby(['date', 'hour']).ID.count(
                    ).reset_index().rename(columns={'ID': 'ng_num'}), on=['date', 'hour'], how='outer')  # 不良品量
                    hourly_dvs_mf['pcs'].fillna(0, inplace=True)
                    hourly_dvs_mf['ng_num'].fillna(0, inplace=True)
                    hourly_dvs_mf['ng_rate'] = hourly_dvs_mf['ng_num'] / \
                        hourly_dvs_mf['pcs'] * 100  # 不良率

                    hourly_dvs_mf = pd.merge(hourly_dvs_mf, aoi.drop_duplicates(['date', 'hour'], keep='first')[['date', 'hour', 'Time_shift']].rename(
                        columns={'Time_shift': 'first_prod_time'}), on=['date', 'hour'], how='outer')  # 各小時第一筆生產時間
                    hourly_dvs_mf = pd.merge(hourly_dvs_mf, aoi.drop_duplicates(['date', 'hour'], keep='last')[['date', 'hour', 'Time_shift']].rename(
                        columns={'Time_shift': 'last_prod_time'}), on=['date', 'hour'], how='outer')  # 各小時最後一筆生產時間
                    hourly_dvs_mf['operation_time'] = hourly_dvs_mf['last_prod_time'] - \
                        hourly_dvs_mf['first_prod_time']
                    hourly_dvs_mf['operation_time'].fillna(
                        pd.Timedelta(0), inplace=True)
                    
                    temp = hourly_dvs_mf['operation_time']

                    hourly_dvs_mf['operation_time'] = (datetime.datetime.combine(
                        date.today(), datetime.time(0, 0, 0)) + hourly_dvs_mf['operation_time'])
                    hourly_dvs_mf['operation_time'] = hourly_dvs_mf['operation_time'].map(
                        lambda x: x.time())

                    hourly_dvs_mf['device'] = dvs.id
                    hourly_dvs_mf['aoi_measure'] = measure.id

                    hourly_dvs_mf['pcs'] = hourly_dvs_mf['pcs'].astype(int)
                    hourly_dvs_mf['ng_num'] = hourly_dvs_mf['ng_num'].astype(int)

                    print("starting input hourly_mf...")
                    print(hourly_dvs_mf)
                    print(hourly_dvs_mf.info())
                    hourly_dvs_mf.to_sql(
                            con=conn, name="hourly_mf", if_exists='append', index=False)


                    hourly_mf = hourly_mf.append(hourly_dvs_mf)

                    # 日夜班 生產量 運作時間
                    hourly_dvs_mf['operation_time'] = temp

                    dn_dvs_mf = hourly_dvs_mf.groupby(
                        ['date', 'shift']).pcs.sum().reset_index()  # 生產量
                    dn_dvs_mf = pd.merge(dn_dvs_mf, hourly_dvs_mf.groupby(['date', 'shift'])[
                                        'operation_time'].sum().reset_index(), on=['date', 'shift'], how='outer')
                    dn_dvs_mf['pcs'] = dn_dvs_mf['pcs'].astype(int)

                    dn_dvs_mf['device'] = dvs.id
                    dn_dvs_mf['aoi_measure'] = measure.id

                    temp_operation = dn_dvs_mf['operation_time']
                    dn_dvs_mf['operation_time'] = (datetime.datetime.combine(
                        date.today(), datetime.time(0, 0, 0)) + dn_dvs_mf['operation_time'])
                    dn_dvs_mf['operation_time'] = dn_dvs_mf['operation_time'].map(
                        lambda x: x.time())

                    # to sql
                    
                    print("starting input dn_mf...")
                    print(dn_dvs_mf)
                    print(dn_dvs_mf.info())
                    dn_dvs_mf.to_sql(con=conn, name="dn_mf",
                                         if_exists='append', index=False)
                   
                    dn_dvs_mf['operation_time'] = temp_operation
                    dn_mf = dn_mf.append(dn_dvs_mf)

                    # 計算operation day
                    working = dn_dvs_mf[dn_dvs_mf['pcs'] > 0]
                    dtime = working[working['shift'] == 'D']['operation_time']
                    ntime = working[working['shift'] == 'N']['operation_time']
                    dpcs = working[working['shift'] == 'D']['pcs']
                    npcs = working[working['shift'] == 'N']['pcs']

                    d_timelower = np.percentile(
                        dtime, 25) - 1.5*(np.percentile(dtime, 75)-np.percentile(dtime, 25))  # 25%-1.5IQR
                    n_timelower = np.percentile(
                        ntime, 25) - 1.5*(np.percentile(ntime, 75)-np.percentile(ntime, 25))  # 25%-1.5IQR
                    d_pcslower = np.percentile(
                        dpcs, 25) - 1.5*(np.percentile(dpcs, 75)-np.percentile(dpcs, 25))  # 25%-1.5IQR
                    n_pcslower = np.percentile(
                        npcs, 25) - 1.5*(np.percentile(npcs, 75)-np.percentile(npcs, 25))  # 25%-1.5IQR

                    dvs_operation_day = (
                        set(dn_mf[(dn_mf['shift'] == 'D') & (
                            (dn_mf['operation_time'] >= d_timelower) | (dn_mf['pcs'] >= d_pcslower))]['date'])
                        & set(dn_mf[(dn_mf['shift'] == 'N') & ((dn_mf['operation_time'] >= n_timelower) | (dn_mf['pcs'] >= n_pcslower))]['date'])
                    )
                    operation_day[dvs.name] = dvs_operation_day
                    op_day = pd.DataFrame()
                    op_day['date'] = sorted(list(dvs_operation_day))
                    op_day['operation_day'] = 1

                    # AOI 特徵 (每天)
                    aoi_fea = pd.DataFrame()
                    aoi_fea['date'] = pd.date_range(
                        aoi['date'].min(), now_workday, closed='left')
                    aoi_fea['date'] = aoi_fea['date'].dt.date
                    aoi_fea['device'] = dvs.id
                    aoi_fea['aoi_measure'] = measure.id
                    aoi_fea = pd.merge(aoi_fea, op_day, on='date', how='outer')

                    aoi_fea = pd.merge(aoi_fea, aoi.groupby(['date']).ID.count(
                    ).reset_index().rename(columns={'ID': 'pcs'}), on='date', how='outer')
                    aoi_fea = pd.merge(aoi_fea, aoi[aoi['Code2'] == 0].groupby(['date']).ID.count(
                    ).reset_index().rename(columns={'ID': 'ng_num'}), on='date', how='outer')
                    aoi_fea['ng_rate'] = aoi_fea['ng_num'] / aoi_fea['pcs'] * 100

                    aoi_fea = pd.merge(aoi_fea, aoi.groupby(['date']).Code6.max().reset_index(
                    ).rename(columns={'Code6': 'ct_max'}), on='date', how='outer')
                    aoi_fea = pd.merge(aoi_fea, aoi.groupby(['date']).Code6.mean().reset_index(
                    ).rename(columns={'Code6': 'ct_mean'}), on='date', how='outer')
                    aoi_fea = pd.merge(aoi_fea, aoi.groupby(['date']).Code6.min().reset_index(
                    ).rename(columns={'Code6': 'ct_min'}), on='date', how='outer')
                    aoi_fea.fillna(0, inplace=True)

                    aoi_fea['pcs'] = aoi_fea['pcs'].astype(int)
                    aoi_fea['ng_num'] = aoi_fea['ng_num'].astype(int)
                    aoi_fea['operation_day'] = aoi_fea['operation_day'].astype(int)

                    print("starting input aoi_feature...")
                    print(aoi_fea)
                    print(aoi_fea.info())
                    aoi_fea.to_sql(con=conn, name="aoi_feature",
                                       if_exists='append', index=False)
                    aoi_feature = aoi_feature.append(aoi_fea)




            def target_label(x):  # 用operation day中發生異常天數比例 判斷目標
                error = dvs_event[dvs_event['Message'] == x['Message']]
                error_happen = error.groupby('date').ID.count().reset_index()
                op_day_err_happen = error_happen[error_happen['date'].isin(
                    operation_day[dvs])]

                # 若發生異常天數少於正常運作天數10%，則非預知維修目標(0)
                if len(op_day_err_happen) / len(operation_day[dvs]) <= 0.1:
                    return 0
                # 正崴指定排除之異常事件(2)
                elif x['Message'] in ['轴2-IM送料马达故障', 'IM插入站故障', '轴4马达故障', '轴7马达故障', '1#插针站故障', '2#插针站故障', '轴7-Shell 送料马达故障', 'Bracket组装站故障']:
                    return 2
                else:  # 預知維修目標(1)
                    return 1

            # testTime = datetime.datetime(2023,9,30,7,40)

            df = pd.DataFrame()
            dvs_name = [dvs.name for dvs in project[0].devices]
            for dvs in project[0].devices:
                sql = f"""
                    SELECT * FROM aoi.`{project[0].name}_event` 
                    WHERE 
                        Category < 200 AND 
                        (Start_Time < '{yesterday_workday_endtime}') AND 
                        Device_Name = '{dvs.name}' AND
                        Line= {dvs.line};
                    """
                temp = pd.read_sql(sql, foxlink_engine)  # 讀取異常事件歷史資料
                df = pd.concat([temp, df], ignore_index=True)
            df_auto = df[(df["START_FILE_NAME"] == "auto") | (
                df["END_FILE_NAME"] == "auto")].reset_index(drop=True)
            # 合併有 auto 的 event
            df_auto_merge = pd.DataFrame()  # 儲存處理後的event
            print("Starting sorting df...")
            while len(df_auto) != 0:
                st = df_auto.iloc[0]  # 取第一個row
                if st["END_FILE_NAME"] != "auto":  # 排除開班 auto 並完成的事件
                    df_auto_merge = pd.concat(
                        [df_auto_merge, st.to_frame().T], ignore_index=1)  # 最後判斷完，另存起來
                    df_auto = df_auto.drop(0).reset_index(drop=True)  # 移除掉~, 重新排序index
                    continue  # 重新while 開始檢查
                for j in range(1, len(df_auto)):
                    ed = df_auto.loc[j]  # 關鍵
                    if (st[["Line", "Device_Name", "Category", "Message"]] == ed[["Line", "Device_Name", "Category", "Message"]]).all():  # 找到相同的項目
                        # 注意是否有雙 auto ，代表 event 又跨一個班別
                        if (ed[["START_FILE_NAME", "END_FILE_NAME"]] == "auto").all():
                            st.at["End_Time"] = ed["End_Time"]  # 更新 st 的 End_Time
                            df_auto = df_auto.drop(j)  # 移除該row；但不需重新排序index
                            continue  # 繼續往後檢查有沒有
                        st["End_Time"] = ed["End_Time"]
                        st["END_FILE_NAME"] = ed["END_FILE_NAME"]
                        df_auto = df_auto.drop(j).reset_index(
                            drop=True)  # 移除該 row, 重新排序index
                        break  # 結束
                df_auto = df_auto.drop(0).reset_index(drop=True)  # 最後判斷完，移除掉第一row
                df_auto_merge = pd.concat(
                    [df_auto_merge, st.to_frame().T], ignore_index=1)  # 最後判斷完，另存起來
            # 排除"原"有 auto 的項目
            df = df[~((df["START_FILE_NAME"] == "auto")
                    | (df["END_FILE_NAME"] == "auto"))]
            # 處理好的 auto 合併回去，重新排序
            df_new_logs = pd.concat([df, df_auto_merge]).sort_values(
                by=["Start_Time"]).reset_index(drop=True)
            event = df_new_logs
            event['Start_Time'] = pd.to_datetime(event['Start_Time'])
            event['End_Time'] = pd.to_datetime(event['End_Time'])
            event['duration'] = event['End_Time'] - event['Start_Time']
            event["Time_shift"] = event["Start_Time"] - \
                pd.Timedelta(hours=7, minutes=40)  # 將早班開始時間(7:40)平移置0:00
            # 以班別為基礎的工作日期 如2022-01-02 為 2022-01-02 7:40(早班開始) 到 2023-01-03 7:40(晚班結束)
            event['date'] = event['Time_shift'].dt.date
            event['hour'] = event['Time_shift'].dt.hour + \
                1  # 工作日期的第幾個小時 1~12為早班 13~24為晚班
            event['shift'] = pd.cut(event['hour'], bins=[0, 12, 24], labels=[
                                    'D', 'N'])  # 班別 1~12為早班(D) 13~24為晚班(N)
            event.sort_values('Start_Time', inplace=True)
            pred_target = pd.DataFrame()
            error_feature = pd.DataFrame()
            for dvs in dvs_name:

                # 判斷預知維修目標
                op_day = pd.DataFrame()
                op_day['date'] = sorted(list(operation_day[dvs]))
                op_day['operation_day'] = 1

                dvs_event = event[event['Device_Name'] == dvs]

                dcm = dvs_event.drop_duplicates(['Device_Name', 'Category', 'Message'])[['Device_Name', 'Category', 'Message']].sort_values([
                    'Device_Name', 'Category'], key=natsort_keygen()).reset_index(drop=True)
                dcm['target'] = dcm.apply(lambda x: target_label(x), axis=1)

                dcm_id = await Device.objects.filter(name=dvs, project=project_id).get_or_none()
                if dcm_id is None:
                    raise HTTPException(
                        status_code=400, detail="cant find dcm device")
                # format data columns
                dcm = dcm.rename(
                    columns={'Device_Name': 'device', 'Category': 'category', 'Message': 'message'})
                dcm['device'] = dcm_id.id

                pred_target_evnets = await ProjectEvent.objects.filter(device=dcm_id).all()
                events_id = []
                for index, row in dcm.iterrows():
                    for i in pred_target_evnets:
                        if row['message'] == i.name and row['category'] == i.category:
                            events_id.append(i.id)

                # 異常每天發生次數(預知維修目標)
                target = dcm[dcm['target'] == 1]
                dcm = dcm.drop(['category', 'message'], axis=1)
                dcm['event'] = events_id

                pred_target = pred_target.append(dcm)
                for row in target.itertuples():
                    message = row.message
                    category = row.category

                    error = dvs_event[dvs_event['Message'] == message]
                    error['duration'] = error['duration'].dt.total_seconds()
                    error['happened_last_time'] = (
                        error['Start_Time'] - error['End_Time'].shift(1)).dt.total_seconds()
                    error['happened_last_time'].fillna(
                        error['happened_last_time'].median(), inplace=True)

                    err_fea = pd.DataFrame()

                    dvs_id = await Device.objects.filter(name=dvs,project=project_id).get_or_none()

                    if dvs_id is None:
                        raise HTTPException(
                            status_code=400, detail="cant find this device")
                    err_fea['date'] = pd.date_range(
                        aoi_feature[aoi_feature['device'] == dvs_id.id].date.min(), now_workday, closed='left')
                    err_fea['date'] = err_fea['date'].dt.date
                    err_fea['device'] = dvs_id.id
                    err_fea['project'] = project_id
                    # err_fea['message'] = message
                    # err_fea['category'] = category
                    err_fea = pd.merge(err_fea, op_day, on='date', how='outer')
                    err_fea = pd.merge(err_fea, error.groupby('date').ID.count().reset_index(
                    ).rename(columns={'ID': 'happened'}), on='date', how='outer')
                    err_fea = pd.merge(err_fea, error.groupby('date').duration.max().reset_index(
                    ).rename(columns={'duration': 'dur_max'}), on='date', how='outer')
                    err_fea = pd.merge(err_fea, round(error.groupby('date').duration.mean(), 1).reset_index(
                    ).rename(columns={'duration': 'dur_mean'}), on='date', how='outer')
                    err_fea = pd.merge(err_fea, error.groupby('date').duration.min().reset_index(
                    ).rename(columns={'duration': 'dur_min'}), on='date', how='outer')
                    err_fea = pd.merge(err_fea, error.groupby('date').happened_last_time.max().reset_index(
                    ).rename(columns={'happened_last_time': 'last_time_max'}), on='date', how='outer')
                    err_fea = pd.merge(err_fea, round(error.groupby('date').happened_last_time.mean(), 1).reset_index(
                    ).rename(columns={'happened_last_time': 'last_time_mean'}), on='date', how='outer')
                    err_fea = pd.merge(err_fea, error.groupby('date').happened_last_time.min().reset_index(
                    ).rename(columns={'happened_last_time': 'last_time_min'}), on='date', how='outer')

                    err_fea.fillna(0, inplace=True)

                    err_fea['operation_day'] = err_fea['operation_day'].astype(int)
                    err_fea['happened'] = err_fea['happened'].astype(int)
                    err_fea['dur_max'] = err_fea['dur_max'].astype(int)
                    err_fea['dur_min'] = err_fea['dur_min'].astype(int)
                    err_fea['last_time_max'] = err_fea['last_time_max'].astype(int)
                    err_fea['last_time_min'] = err_fea['last_time_min'].astype(int)

                    err_fea = err_fea[err_fea['project'] != 0]
                    target_event = await ProjectEvent.objects.filter(device=dvs_id, name=message, category=category).get()
                    err_fea['event'] = target_event.id

                    print(err_fea)
                    print(err_fea.info())
                    err_fea.to_sql(con=conn, name="error_feature",
                                if_exists='append', index=False)

            print("starting input pred_target...")
            print(pred_target)
            print(pred_target.info())
            pred_target.to_sql(con=conn, name="pred_targets",
                            if_exists='append', index=False)
            
            # bulk_update_devices : List[Device] = []
            devices = await Device.objects.filter(project=project_id,flag=False).all()
            for dvs in devices:
                temp_device = await Device.objects.get(id=dvs.id)
                temp_device.flag=True
                await temp_device.save()

            trans.commit()
            conn.close()
        except Exception as e:
            trans.rollback()
            raise HTTPException(
                status_code=400, detail=e)
    return


async def UpdatePreprocessingData(project_id: int,user:str):
    # now = datetime.datetime(2023,2,1,7,39)
    await AuditLogHeader.objects.create(
        action=AuditActionEnum.DAILY_PREPROCESSING_STARTED.value,
        user=user,
        description=project_id
    )
    now = get_ntz_now()  # 更新資料時間
    update_workday = (now - pd.Timedelta(hours=7, minutes=40)
                      ).date()  
    print(update_workday)
    # 更新資料的工作日期
    update_workday_endtime = pd.to_datetime(
        update_workday) + pd.Timedelta(hours=7, minutes=40)

    project = await Project.objects.filter(id=project_id).select_related(
        ["devices", "devices__aoimeasures"]
    ).all()
    if project is None:
        raise HTTPException(
            status_code=400, detail="this project doesnt existed.")

    hourly_mf = pd.DataFrame()
    dn_mf = pd.DataFrame()
    aoi_feature = pd.DataFrame()
    try:
        with ntust_engine.connect() as conn:
            trans = conn.begin()
            for dvs in project[0].devices:
                for measure in dvs.aoimeasures:

                    sql = f"""
                        SELECT ID,Code1,Code2,Code3,Code4,Code6 FROM `{project[0].name}_{measure.name}_data`
                        WHERE 
                            (Code3 = '{update_workday}' AND Code4 >= '07:40:00') OR
                            (Code3 = '{update_workday+pd.Timedelta(days=1)}' AND Code4 < '07:40:00')
                            AND Code2 < 3 ;
                        """
                    aoi = pd.read_sql(sql, foxlink_engine)

                    if aoi.empty:  # 沒有新的資料

                        # 小時
                        hourly_dvs_mf = pd.DataFrame(columns=['date', 'hour', 'shift', 'pcs', 'ng_num', 'ng_rate',
                                                    'first_prod_time', 'last_prod_time', 'operation_time', 'device', 'aoi_measure'])
                        hourly_dvs_mf['time'] = pd.date_range(
                            update_workday, update_workday + pd.Timedelta(days=1), freq='h', closed='left')
                        hourly_dvs_mf['date'] = hourly_dvs_mf['time'].dt.date
                        hourly_dvs_mf['hour'] = hourly_dvs_mf['time'].dt.hour+1
                        hourly_dvs_mf['shift'] = pd.cut(hourly_dvs_mf['hour'], bins=[
                                                        0, 12, 24], labels=['D', 'N'])
                        hourly_dvs_mf.drop('time', axis=1, inplace=True)

                        hourly_dvs_mf['pcs'].fillna(0, inplace=True)
                        hourly_dvs_mf['ng_num'].fillna(0, inplace=True)
                        hourly_dvs_mf['operation_time'].fillna(
                            pd.Timedelta(0), inplace=True)
                        hourly_dvs_mf['device'] = dvs.id
                        hourly_dvs_mf['aoi_measure'] = measure.id
                        hourly_mf = hourly_mf.append(hourly_dvs_mf)

                        # 早晚班
                        dn_dvs_mf = hourly_dvs_mf.groupby(
                            ['date', 'shift']).pcs.sum().reset_index()  # 生產量
                        dn_dvs_mf = pd.merge(dn_dvs_mf, hourly_dvs_mf.groupby(['date', 'shift'])[
                                            'operation_time'].sum().reset_index(), on=['date', 'shift'], how='outer')
                        dn_dvs_mf['pcs'] = dn_dvs_mf['pcs'].astype(int)

                        dn_dvs_mf['device'] = dvs.id
                        dn_dvs_mf['aoi_measure'] = measure.id
                        dn_mf = dn_mf.append(dn_dvs_mf)

                        # 日
                        aoi_fea = pd.DataFrame(columns=['date', 'device', 'aoi_measure', 'operation_day',
                                            'pcs', 'ng_num', 'ng_rate', 'ct_max', 'ct_mean', 'ct_min'])
                        aoi_fea['date'] = [update_workday]
                        aoi_fea['device'] = dvs.id
                        aoi_fea['aoi_measure'] = measure.id
                        aoi_fea.fillna(0, inplace=True)
                        aoi_feature = aoi_feature.append(aoi_fea)

                    else:
                        aoi['MF_Time'] = pd.to_datetime(aoi['Code3']) + aoi['Code4']
                        aoi["Time_shift"] = aoi["MF_Time"] - \
                            pd.Timedelta(hours=7, minutes=40)  # 將早班開始時間(7:40)平移置0:00
                        # 以班別為基礎的工作日期 如2022-01-02 為 2022-01-02 7:40(早班開始) 到 2023-01-03 7:40(晚班結束)
                        aoi['date'] = aoi['Time_shift'].dt.date
                        aoi['hour'] = aoi['Time_shift'].dt.hour + \
                            1  # 工作日期的第幾個小時 1~12為早班 13~24為晚班
                        aoi['shift'] = pd.cut(aoi['hour'], bins=[0, 12, 24], labels=[
                                            'D', 'N'])  # 班別 1~12為早班(D) 13~24為晚班(N)

                        # 每小時生產資訊
                        hourly_dvs_mf = pd.DataFrame()
                        hourly_dvs_mf['time'] = pd.date_range(
                            update_workday, update_workday + pd.Timedelta(days=1), freq='h', closed='left')
                        hourly_dvs_mf['date'] = hourly_dvs_mf['time'].dt.date
                        hourly_dvs_mf['hour'] = hourly_dvs_mf['time'].dt.hour+1
                        hourly_dvs_mf['shift'] = pd.cut(hourly_dvs_mf['hour'], bins=[
                                                        0, 12, 24], labels=['D', 'N'])
                        hourly_dvs_mf.drop('time', axis=1, inplace=True)

                        hourly_dvs_mf = pd.merge(hourly_dvs_mf, aoi.groupby(['date', 'hour']).ID.count(
                        ).reset_index().rename(columns={'ID': 'pcs'}), on=['date', 'hour'], how='outer')  # 生產量
                        hourly_dvs_mf = pd.merge(hourly_dvs_mf, aoi[aoi['Code2'] == 0].groupby(['date', 'hour']).ID.count(
                        ).reset_index().rename(columns={'ID': 'ng_num'}), on=['date', 'hour'], how='outer')  # 不良品量
                        hourly_dvs_mf['pcs'].fillna(0, inplace=True)
                        hourly_dvs_mf['ng_num'].fillna(0, inplace=True)
                        hourly_dvs_mf['ng_rate'] = hourly_dvs_mf['ng_num'] / \
                            hourly_dvs_mf['pcs'] * 100  # 不良率

                        hourly_dvs_mf = pd.merge(hourly_dvs_mf, aoi.drop_duplicates(['date', 'hour'], keep='first')[['date', 'hour', 'Time_shift']].rename(
                            columns={'Time_shift': 'first_prod_time'}), on=['date', 'hour'], how='outer')  # 各小時第一筆生產時間
                        hourly_dvs_mf = pd.merge(hourly_dvs_mf, aoi.drop_duplicates(['date', 'hour'], keep='last')[['date', 'hour', 'Time_shift']].rename(
                            columns={'Time_shift': 'last_prod_time'}), on=['date', 'hour'], how='outer')  # 各小時最後一筆生產時間
                        hourly_dvs_mf['operation_time'] = hourly_dvs_mf['last_prod_time'] - \
                            hourly_dvs_mf['first_prod_time']
                        hourly_dvs_mf['operation_time'].fillna(
                            pd.Timedelta(0), inplace=True)

                        hourly_dvs_mf['device'] = dvs.id
                        hourly_dvs_mf['aoi_measure'] = measure.id

                        hourly_dvs_mf['pcs'] = hourly_dvs_mf['pcs'].astype(int)
                        hourly_dvs_mf['ng_num'] = hourly_dvs_mf['ng_num'].astype(int)

                        hourly_mf = hourly_mf.append(hourly_dvs_mf)

                        # 日夜班 生產量 運作時間
                        dn_dvs_mf = hourly_dvs_mf.groupby(
                            ['date', 'shift']).pcs.sum().reset_index()  # 生產量
                        dn_dvs_mf = pd.merge(dn_dvs_mf, hourly_dvs_mf.groupby(['date', 'shift'])[
                                            'operation_time'].sum().reset_index(), on=['date', 'shift'], how='outer')
                        dn_dvs_mf['pcs'] = dn_dvs_mf['pcs'].astype(int)

                        dn_dvs_mf['device'] = dvs.id
                        dn_dvs_mf['aoi_measure'] = measure.id

                        dn_mf = dn_mf.append(dn_dvs_mf)

                        # 計算operation day (讀取之前的紀錄計算合格運作的條件)
                        # sql = f"""
                        #     SELECT * FROM d7x_e75_dn_mf
                        #     WHERE date < '{update_workday}' AND
                        #     Device_Name = '{dvs}' AND
                        #     pcs > 0 ;
                        #     """
                        sql = f"""
                            SELECT * FROM dn_mf
                            WHERE date < '{update_workday}' AND
                            device = {dvs.id} AND
                            pcs > 0
                        """
                        working = pd.read_sql(sql, ntust_engine)

                        dtime = working[working['shift'] == 'D']['operation_time']
                        ntime = working[working['shift'] == 'N']['operation_time']
                        dpcs = working[working['shift'] == 'D']['pcs']
                        npcs = working[working['shift'] == 'N']['pcs']

                        d_timelower = np.percentile(
                            dtime, 25) - 1.5*(np.percentile(dtime, 75)-np.percentile(dtime, 25))  # 25%-1.5IQR
                        n_timelower = np.percentile(
                            ntime, 25) - 1.5*(np.percentile(ntime, 75)-np.percentile(ntime, 25))  # 25%-1.5IQR
                        d_pcslower = np.percentile(
                            dpcs, 25) - 1.5*(np.percentile(dpcs, 75)-np.percentile(dpcs, 25))  # 25%-1.5IQR
                        n_pcslower = np.percentile(
                            npcs, 25) - 1.5*(np.percentile(npcs, 75)-np.percentile(npcs, 25))  # 25%-1.5IQR
                        if ((dn_dvs_mf[dn_dvs_mf['shift'] == 'D']['operation_time'].iloc[0] >= d_timelower) | (dn_dvs_mf[dn_dvs_mf['shift'] == 'D']['pcs'].iloc[0] >= d_pcslower)) & ((dn_dvs_mf[dn_dvs_mf['shift'] == 'N']['operation_time'].iloc[0] >= n_timelower) | (dn_dvs_mf[dn_dvs_mf['shift'] == 'N']['pcs'].iloc[0] >= n_pcslower)):
                            operation = 1
                        else:
                            operation = 0
                        aoi_fea = pd.DataFrame()
                        aoi_fea['date'] = [update_workday]
                        aoi_fea['device'] = dvs.id
                        aoi_fea['aoi_measure'] = measure.id
                        aoi_fea['operation_day'] = operation

                        aoi_fea = pd.merge(aoi_fea, aoi.groupby(['date']).ID.count(
                        ).reset_index().rename(columns={'ID': 'pcs'}), on='date', how='outer')
                        aoi_fea = pd.merge(aoi_fea, aoi[aoi['Code2'] == 0].groupby(['date']).ID.count(
                        ).reset_index().rename(columns={'ID': 'ng_num'}), on='date', how='outer')
                        aoi_fea['ng_rate'] = aoi_fea['ng_num'] / \
                            aoi_fea['pcs'] * 100

                        aoi_fea = pd.merge(aoi_fea, aoi.groupby(['date']).Code6.max().reset_index(
                        ).rename(columns={'Code6': 'ct_max'}), on='date', how='outer')
                        aoi_fea = pd.merge(aoi_fea, aoi.groupby(['date']).Code6.mean().reset_index(
                        ).rename(columns={'Code6': 'ct_mean'}), on='date', how='outer')
                        aoi_fea = pd.merge(aoi_fea, aoi.groupby(['date']).Code6.min().reset_index(
                        ).rename(columns={'Code6': 'ct_min'}), on='date', how='outer')
                        aoi_fea.fillna(0, inplace=True)

                        aoi_fea['pcs'] = aoi_fea['pcs'].astype(int)
                        aoi_fea['ng_num'] = aoi_fea['ng_num'].astype(int)
                        aoi_fea['operation_day'] = aoi_fea['operation_day'].astype(int)

                        aoi_feature = aoi_feature.append(aoi_fea)
                        hourly_mf['operation_time'] = hourly_mf['operation_time'].astype(
                            str).apply(lambda x: x[7:])
                        dn_mf['operation_time'] = dn_mf['operation_time'].astype(
                            str).apply(lambda x: x[7:])

            # with ntust_engine.begin() as conn:
            print('import houly_mf')
            print(hourly_mf)
            hourly_mf.to_sql(name='hourly_mf', con=conn,
                            if_exists='append', index=False)
            print('import dn_mf')
            print(dn_mf)
            dn_mf.to_sql(name='dn_mf', con=conn,
                        if_exists='append', index=False)
            print('import aoi_feature')
            print(aoi_feature)
            aoi_feature.to_sql(name='aoi_feature', con=conn,
                            if_exists='append', index=False)


            df = pd.DataFrame()
            dvs_name = [dvs.name for dvs in project[0].devices]
            print(dvs_name)
            for dvs in project[0].devices:
                sql = f"""
                SELECT * FROM aoi.`{project[0].name}_event` 
                WHERE 
                    Category < 200 AND 
                    (Start_Time >= '{update_workday_endtime}') AND
                    (Start_Time < '{update_workday_endtime + pd.Timedelta(days=1)}') AND
                    Device_Name = '{dvs.name}' AND
                    Line= {dvs.line};
                """
                temp = pd.read_sql(sql, foxlink_engine)  # 讀取異常事件歷史資料
                df = pd.concat([temp, df], ignore_index=True)
            df_auto = df[(df["START_FILE_NAME"] == "auto") | (df["END_FILE_NAME"] == "auto")].reset_index(drop=True)
            # 合併有 auto 的 event
            df_auto_merge = pd.DataFrame()  # 儲存處理後的event
            while len(df_auto) != 0:
                st = df_auto.iloc[0]  # 取第一個row
                if st["END_FILE_NAME"] != "auto":  # 排除開班 auto 並完成的事件
                    df_auto_merge = pd.concat(
                        [df_auto_merge, st.to_frame().T], ignore_index=1)  # 最後判斷完，另存起來
                    df_auto = df_auto.drop(0).reset_index(drop=True)  # 移除掉~, 重新排序index
                    continue  # 重新while 開始檢查
                for j in range(1, len(df_auto)):
                    ed = df_auto.loc[j]  # 關鍵
                    if (st[["Line", "Device_Name", "Category", "Message"]] == ed[["Line", "Device_Name", "Category", "Message"]]).all():  # 找到相同的項目
                        # 注意是否有雙 auto ，代表 event 又跨一個班別
                        if (ed[["START_FILE_NAME", "END_FILE_NAME"]] == "auto").all():
                            st.at["End_Time"] = ed["End_Time"]  # 更新 st 的 End_Time
                            df_auto = df_auto.drop(j)  # 移除該row；但不需重新排序index
                            continue  # 繼續往後檢查有沒有
                        st["End_Time"] = ed["End_Time"]
                        st["END_FILE_NAME"] = ed["END_FILE_NAME"]
                        df_auto = df_auto.drop(j).reset_index(
                            drop=True)  # 移除該 row, 重新排序index
                        break  # 結束
                df_auto = df_auto.drop(0).reset_index(drop=True)  # 最後判斷完，移除掉第一row
                df_auto_merge = pd.concat(
                    [df_auto_merge, st.to_frame().T], ignore_index=1)  # 最後判斷完，另存起來
            df = df[~((df["START_FILE_NAME"] == "auto")
                    | (df["END_FILE_NAME"] == "auto"))]
            # 處理好的 auto 合併回去，重新排序
            df_new_logs = pd.concat([df, df_auto_merge]).sort_values(
                by=["Start_Time"]).reset_index(drop=True)
            event = df_new_logs
            event['Start_Time'] = pd.to_datetime(event['Start_Time'])
            event['End_Time'] = pd.to_datetime(event['End_Time'])
            event['duration'] = event['End_Time'] - event['Start_Time']
            event["Time_shift"] = event["Start_Time"] - \
                pd.Timedelta(hours=7, minutes=40)  # 將早班開始時間(7:40)平移置0:00
            # 以班別為基礎的工作日期 如2022-01-02 為 2022-01-02 7:40(早班開始) 到 2023-01-03 7:40(晚班結束)
            event['date'] = event['Time_shift'].dt.date
            event['hour'] = event['Time_shift'].dt.hour + \
                1  # 工作日期的第幾個小時 1~12為早班 13~24為晚班
            event['shift'] = pd.cut(event['hour'], bins=[0, 12, 24], labels=[
                                    'D', 'N'])  # 班別 1~12為早班(D) 13~24為晚班(N)
            event.sort_values('Start_Time', inplace=True)
            error_feature = pd.DataFrame()
            for dvs in dvs_name:
                dvs_event = event[event['Device_Name'] == dvs]
                dvs_data = await Device.objects.filter(name=dvs, project=project_id).get()

                # operation = (await AoiFeature.objects.filter(
                #     device=dvs_data.id,
                #     date__gte=update_workday
                # ).all())
                aoi_operation = aoi_feature[aoi_feature["device"] == dvs_data.id]["operation_day"].iloc[:1]
                sql = f"""
                SELECT pt.device,pt.target,pt.event,pe.name,pe.category FROM pred_targets as pt
                JOIN project_events as pe
                ON pe.id = pt.event
                WHERE 
                    pt.device = {dvs_data.id} AND
                    pt.target = 1 ;
                """
                target = pd.read_sql(sql, ntust_engine)  # 預知維修目標

                for row in target.itertuples():
                    print(row)
                    message = row.name

                    error = dvs_event[dvs_event['Message'] == message]
                    error['duration'] = error['duration'].dt.total_seconds()
                    error['happened_last_time'] = (
                        error['Start_Time'] - error['End_Time'].shift(1)).dt.total_seconds()
                    error['happened_last_time'].fillna(
                        error['happened_last_time'].median(), inplace=True)

                    err_fea = pd.DataFrame()
                    err_fea['date'] = [update_workday]
                    err_fea['project'] = project_id
                    err_fea['device'] = row.device
                    err_fea['event'] = row.event
                    err_fea['operation_day'] = aoi_operation
                    err_fea = pd.merge(err_fea, error.groupby('date').ID.count().reset_index(
                    ).rename(columns={'ID': 'happened'}), on='date', how='outer')
                    err_fea = pd.merge(err_fea, error.groupby('date').duration.max().reset_index(
                    ).rename(columns={'duration': 'dur_max'}), on='date', how='outer')
                    err_fea = pd.merge(err_fea, round(error.groupby('date').duration.mean(), 1).reset_index(
                    ).rename(columns={'duration': 'dur_mean'}), on='date', how='outer')
                    err_fea = pd.merge(err_fea, error.groupby('date').duration.min().reset_index(
                    ).rename(columns={'duration': 'dur_min'}), on='date', how='outer')
                    err_fea = pd.merge(err_fea, error.groupby('date').happened_last_time.max().reset_index(
                    ).rename(columns={'happened_last_time': 'last_time_max'}), on='date', how='outer')
                    err_fea = pd.merge(err_fea, round(error.groupby('date').happened_last_time.mean(), 1).reset_index(
                    ).rename(columns={'happened_last_time': 'last_time_mean'}), on='date', how='outer')
                    err_fea = pd.merge(err_fea, error.groupby('date').happened_last_time.min().reset_index(
                    ).rename(columns={'happened_last_time': 'last_time_min'}), on='date', how='outer')
                    err_fea.fillna(0, inplace=True)

                    err_fea['operation_day'] = err_fea['operation_day'].astype(int)
                    err_fea['happened'] = err_fea['happened'].astype(int)
                    err_fea['dur_max'] = err_fea['dur_max'].astype(int)
                    err_fea['dur_min'] = err_fea['dur_min'].astype(int)
                    err_fea['last_time_max'] = err_fea['last_time_max'].astype(int)
                    err_fea['last_time_min'] = err_fea['last_time_min'].astype(int)
                    error_feature = error_feature.append(err_fea)
                # with ntust_engine.begin() as conn:
            print('import error_feature')
            print(error_feature)
            error_feature.to_sql(name='error_feature',
                                    con=conn, if_exists='append', index=False)
            trans.commit()
            conn.close()
            await AuditLogHeader.objects.create(
                    action=AuditActionEnum.DAILY_PREPROCESSING_SUCCEEDED.value,
                    user=user,
                    description=project_id
            )
    except Exception as e:
        await AuditLogHeader.objects.create(
            action=AuditActionEnum.DAILY_PREPROCESSING_FAILED.value,
            user=user,
            description=project_id
        )
        print(f"{repr(e)}")
        trans.rollback()
        raise e

    return

@transaction()
async def TrainingData(project_id: int, select_type: str):
    input_data_dict = await foxlink_train.data_preprocessing_from_sql(project_id=project_id)
    every_error_performance = {}
    timenow = get_ntz_now().strftime("%Y%m%d%H%M")
    devices = await Device.objects.filter(project=project_id).all()
    with ntust_engine.connect() as conn:
        trans = conn.begin()
        try:
            for dv in input_data_dict:
                for events in tqdm(input_data_dict[dv]):
                    temp = []
                    count = 0
                    for t in foxlink_train.Threshold:
                        count += 1
                        print(dv + ' '+events + ' T = ', t)
                        df = input_data_dict[dv][events]
                        if select_type == "week" and count == 1:
                            df['date'] = pd.to_datetime(df['date'])
                            df.set_index('date', inplace=True)
                            # df = df.resample('W').sum()
                            df = df.resample('W').agg(
                                {col: foxlink_train.choose_agg_func(col) for col in df.columns})
                        # 透過device與Message去Map出Category
                        for i in devices:
                            if dv == i.name:
                                device_id = i.id
                        event = await ProjectEvent.objects.filter(name=events, device=device_id).get()
                        ca = foxlink_train.map_category(device_id, event.id)
                        try:
                            # 貼標
                            df, lights, cutting_point = foxlink_train.light_labeling(
                                df, events=events, Threshold=t)
                            # 把欄位提取出來
                            used_col = df.columns.to_list()
                            used_col.remove('light')
                            # 訓練模型前的最後資料前處理
                            foxlink_train.training_data_preprocessing(df)
                            # 挑選了哪些模型
                            es = foxlink_train.select_model()
                            # 訓練模型
                            model, report = foxlink_train.stacking(es)
                            # 計算評估指標
                            acc, red_recall, red_f1, arf = foxlink_train.ARF(report)
                            # 存至暫存器
                            temp.append((t, arf))
                            if dv not in every_error_performance:
                                every_error_performance[dv] = {}
                            if events not in every_error_performance[dv]:
                                every_error_performance[dv][events] = {}
                            if t not in every_error_performance[dv][events]:
                                every_error_performance[dv][events][t] = {'device': device_id,
                                                                        'event': event.id,
                                                                        'threshold': t,
                                                                        'actual_cutpoint': cutting_point,
                                                                        'model': model,
                                                                        'arf': arf,
                                                                        'acc': acc,
                                                                        'red_recall': red_recall,
                                                                        'red_f1score': red_f1,
                                                                        'used_col': str(used_col),
                                                                        'created_date': timenow}
                        except:
                            print('無法訓練')
                    # 找最佳ARF的Threshold
                    best_t = sorted(temp, key=lambda x: (x[1]), reverse=True)[0][0]
                    best_model = every_error_performance[dv][events][best_t]['model']
                    # 儲存模型
                    if select_type == 'week':
                        joblib.dump(
                            best_model, f'/app/model_week/{dv}_{ca}_{timenow}.pkl')
                    else:
                        joblib.dump(best_model, f'/app/model/{dv}_{ca}_{timenow}.pkl')

                    every_error_performance[dv][events][best_t]['freq'] = select_type
                    # 寫入資料庫      
                    pd.DataFrame(every_error_performance[dv][events][best_t], index=[0]).drop(
                        columns='model').to_sql('train_performances', con=conn, if_exists='append', index=False)
            trans.commit()
        except Exception as e:
            trans.rollback()
            raise e
            
    return

@transaction()
async def PredictData(project_id: int, select_type: str,user:str):
    with ntust_engine.connect() as conn:
        trans = conn.begin()
        try:
            input_data_dict, infos = await foxlink_predict.data_preprocessing_from_sql(project_id=project_id,select_type=select_type)
            for dv in input_data_dict:
                device = await Device.objects.filter(
                    project = project_id,
                    name=dv
                ).get_or_none()
                if device is None:
                    raise HTTPException(
                        status_code=400, detail="this device_id doesnt existed.")
                device_id = device.id
                for events in tqdm(input_data_dict[dv]):

                        df = input_data_dict[dv][events]
                        if select_type == 'week':
                            try:
                                df['date1'] = pd.to_datetime(df['date'].iloc[:, 0])
                            except:
                                df['date1'] = pd.to_datetime(df['date'])
                            df.set_index('date1', inplace=True)
                            # df = df.resample('W').sum()
                            df.drop(['date'], axis=1, inplace=True)
                            df = df.resample('W').agg(
                                {col: foxlink_predict.choose_agg_func(col) for col in df.columns})
                            df['date'] = df.index

                        event = infos[dv][events]['event'].values[0]

                        time = pd.to_datetime(
                            infos[dv][events]['created_date'].values[0]).strftime('%Y%m%d%H%M')
                        X = foxlink_predict.fit_model_data_preprocessing(df)
                        model = foxlink_predict.map_model(
                            dv, device_id, event, time, select_type)
                        pred = model.predict(X)

                        df = df.T.drop_duplicates().T
                        df['pred'] = pred
                        df['device'] = device_id
                        df['event'] = event
                        if select_type == 'week':
                            df['pred_date'] = df.date.apply(
                                lambda x: x + pd.Timedelta(days=7))
                            df.reset_index(inplace=True, drop=True)
                            df['pred_type'] = 1
                        else:
                            df['pred_date'] = df.date.apply(
                                lambda x: x + pd.Timedelta(days=1))
                            df['pred_type'] = 0

                        df.rename(columns={'date': 'ori_date'}, inplace=True)
                        df = df[['device', 'event',
                                'ori_date', 'pred_date', 'pred', 'pred_type']]
                        df.to_sql('predict_results', con=conn,
                                if_exists='append', index=False)
            await AuditLogHeader.objects.create(
                action=AuditActionEnum.PREDICT_SUCCEEDED.value,
                user=user,
                description=project_id
            )
            trans.commit()
        except Exception as e:
            trans.rollback()
            await AuditLogHeader.objects.create(
                action=AuditActionEnum.PREDICT_FAILED.value,
                user=user,
                description=project_id
            )
            raise e
    return


async def GetFoxlinkTables():
    tables = await foxlink_dbs.get_all_project_tabels()
    return tables

# async def HappenedCheck(project_id: int, start_time: datetime, select_type: str):
#     # data = await Project.objects.filter(id=project_id).select_related(
#     #     ["devices", "devices__predictresults"]
#     # ).filter(
#     #     devices__predictresults__pred_date__gte=get_ntz_now().date()
#     # ).all()
#     # event = await ErrorFeature.objects.filter(
#     #             device=dvs.id,
#     #             project=project_id
#     #         ).all()
#     #         event = set([row.event.id for row in event])
#     #         events = await ProjectEvent.objects.filter(id__in=event).all()
#     project = await Project.objects.filter(id=project_id).select_related(["devices", "devices__events"]).all()
#     devices = project[0].devices
#     for dvs in devices:
#         events = dvs.events
#         for event in events:
#             if select_type == "day":
#                 checkPredEvent = await PredictResult.objects.filter(event=event.id, pred_type=0).order_by('-pred_date').limit(1).get_or_none()

#                 # check
#                 if checkPredEvent is None:
#                     continue

#                 pred_data = await PredictResult.objects.filter(event=event.id, ori_date__gte=start_time, pred_type=0).order_by('-pred_date').all()
#                 update_pred_data_bulk = []
#                 for data in pred_data:
#                     # week predict
#                     if data.pred_type is True:
#                         continue
#                     # day predict
#                     else:
#                         stmt = f"""
#                         SELECT * FROM `{project[0].name}_event`
#                         WHERE
#                             Device_Name = '{dvs.name}' AND
#                             Message = '{event.name}' AND
#                             (Start_Time > '{data.pred_date}' AND Start_Time < '{data.pred_date + timedelta(days=1)}')
#                             ORDER BY Start_Time DESC;
#                         """
#                         existed = await foxlink_dbs[FOXLINK_AOI_DATABASE].fetch_all(query=stmt)
#                         if len(existed) >= 1:
#                             data.last_happened = datetime(
#                                 existed[0]["Start_Time"])

#                         data.last_happened_check = 1
#                         update_pred_data_bulk.append(data)

#                 await PredictResult.objects.bulk_update(
#                     objects=update_pred_data_bulk,
#                     columns=["last_happened", "last_happened_check"]
#                 )
#             else:
#                 checkPredEvent = await PredictResult.objects.filter(event=event.id, pred_type=1).order_by('-pred_date').limit(1).get_or_none()

#                 # check
#                 if checkPredEvent is None:
#                     continue

#                 pred_data = await PredictResult.objects.filter(event=event.id, ori_date__gte=start_time, pred_type=1).order_by('-pred_date').all()
#                 update_pred_data_bulk = []
#                 for data in pred_data:
#                     # day predict
#                     stmt = f"""
#                         SELECT * FROM `{project[0].name}_event`
#                         WHERE
#                             Device_Name = '{dvs.name}' AND
#                             Message = '{event.name}' AND
#                             (Start_Time > '{data.pred_date}' AND Start_Time < '{data.pred_date + timedelta(days=7)}')
#                             ORDER BY Start_Time DESC;
#                         """
#                     existed = await foxlink_dbs[FOXLINK_AOI_DATABASE].fetch_all(query=stmt)
#                     if len(existed) >= 1:
#                         data.last_happened = datetime(existed[0]["Start_Time"])

#                     data.last_happened_check = 1
#                     update_pred_data_bulk.append(data)

#                 await PredictResult.objects.bulk_update(
#                     objects=update_pred_data_bulk,
#                     columns=["last_happened", "last_happened_check"]
#                 )
#     return
