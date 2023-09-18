from datetime import datetime
from typing import List, Optional
from fastapi import APIRouter, Depends ,Response
from fastapi.exceptions import HTTPException
from datetime import timedelta
import pandas as pd
import numpy as np
from sqlalchemy import create_engine
from app.core.database import (
    get_ntz_now,
    User,
    Project,
    ProjectUser,
    ProjectEvent,
    UserLevel
)
from app.foxlink.db import foxlink_dbs


async def AddNewProject(project_name:str):
    await foxlink_dbs.connect()
    stmt = (
        f"SELECT Device_Name , Measure_Workno FROM testing_foxlink.measure_info WHERE Project = '{project_name}'"
    )
    devices = await foxlink_dbs['mysql-test:3306@testing_foxlink'].fetch_all(query=stmt)

    check_duplicate = await Project.objects.get_or_none(name=project_name)
    if devices is not None and check_duplicate is None:
        return await Project.objects.create(name=project_name)
    else:
        raise HTTPException(
            status_code=404, detail="The project name is duplicate or not existed.")

async def AddNewProjectWorker(project_id:int,user_id:str,permission:int=UserLevel):
    user = await User.objects.filter(badge=user_id).get_or_none()
    if user is None:
        raise HTTPException(404, 'user is not found')
    
    project = await Project.objects.filter(id=project_id).get_or_none()

    if project is None:
        raise HTTPException(404, 'project is not found')

    check_duplicate = await ProjectUser.objects.filter(
        project_id=project_id,user_id=user_id
        ).get_or_none()
    
    if check_duplicate is None:
        await ProjectUser.objects.create(
           project_id=project_id,
           user_id=user.badge,
           permission=permission
        ) 
        return True
    else:
        raise HTTPException(400, 'this user is already in the project')

async def SearchProjectDevices(project_id:str):
    await foxlink_dbs.connect()
    host = 'aoi'
    stmt = (
        f"SELECT Device_Name , Measure_Workno FROM testing_foxlink.measure_info WHERE Project = '{project_id}'"
    )
    devices = await foxlink_dbs['mysql-test:3306@testing_foxlink'].fetch_all(query=stmt)
    # print(device)
    dvs_aoi = {}
    print(devices)
    for device,measure in devices:
        if device not in dvs_aoi.keys():
            dvs_aoi[device] = dvs_aoi.get(device,[])
        dvs_aoi[device].append(measure.lower())
    print(dvs_aoi)

    await foxlink_dbs.disconnect()
    return dvs_aoi

async def AddNewProjectDevices():
    return

async def CreateTable():
    foxlink_engine = create_engine(f'mysql+pymysql://ntust:ntustpwd@172.21.0.1:12345/aoi')
    ntust_engine = create_engine(f'mysql+pymysql://root:AqqhQ993VNto@mysql-test:3306/foxlink')
    await foxlink_dbs.connect()
    stmt = (
        f"SELECT Device_Name , Measure_Workno FROM aoi.measure_info WHERE Project = 'd7x e75'"
    )
    devices = await foxlink_dbs['172.21.0.1:12345@aoi'].fetch_all(query=stmt)
    # print(device)
    dvs_aoi = {}
    print(devices)
    for device,measure in devices:
        if device not in dvs_aoi.keys():
            dvs_aoi[device] = dvs_aoi.get(device,[])
        dvs_aoi[device].append(measure.lower())
    # print(dvs_aoi)

    # await foxlink_dbs.disconnect()
    hourly_mf = pd.DataFrame()
    dn_mf = pd.DataFrame()
    operation_day={}
    aoi_feature = pd.DataFrame()

# for dvs in list(dvs_aoi)[:2]:
    for dvs in dvs_aoi:
        if dvs == "Device_5":

            for measure in dvs_aoi[dvs]:
                print(dvs, measure)
                # stmt = (
                #     f"SELECT Code1,Code2,Code3,Code4,Code6 FROM aoi.`d7x e75_{measure}_data`"
                # )
                # aoi = await foxlink_dbs['172.21.0.1:12345@aoi'].fetch_all(query=stmt)
                # aoi = pd.DataFrame() # 批次讀取後再合併
                aoi = pd.DataFrame()
                sql = f"SELECT * FROM `d7x e75_{measure}_data` LIMIT 1;" # 資料表第一筆資料
                first_data_date = pd.read_sql(sql, foxlink_engine)['Code3'].values[0] # 第一筆資料的日期
                dr = pd.date_range(first_data_date, datetime.now().date(), freq='3M').astype(str) # 每六個月為一個週期，批次讀取

                sql = f"""
                    SELECT ID,Code1,Code2,Code3,Code4,Code6 FROM `d7x e75_{measure}_data`
                    WHERE 
                        (Code3 = '{str(first_data_date)}' AND Code4 >= '07:40:00') OR
                        (Code3 > '{str(first_data_date)}' AND Code3 < '{dr[0]}') OR
                        (Code3 = '{dr[0]}' AND Code4 <= '07:40:00')
                        AND Code2 < 3 ;
                    """
                tmp_data = pd.read_sql(sql, foxlink_engine)
                aoi = aoi.append(tmp_data)
                for index in range(1, len(dr)):
                    sql = f"""
                    SELECT ID,Code1,Code2,Code3,Code4,Code6 FROM `d7x e75_{measure}_data`
                    WHERE 
                        (Code3 = '{dr[index-1]}' AND Code4 >= '07:40:00') OR
                        (Code3 > '{dr[index-1]}' AND Code3 < '{dr[index]}') OR
                        (Code3 = '{dr[index]}' AND Code4 <= '07:40:00')
                        AND Code2 < 3 ;
                    """
                    tmp_data = pd.read_sql(sql, foxlink_engine)
                    aoi = aoi.append(tmp_data)
                
                # aoi = pd.read_csv(f'../d7x/AOI/2022/{dvs}_{measure}.csv', usecols=['ID', 'Code1','Code2','Code3','Code4','Code6'])
                # test = pd.DataFrame(columns=["Code1","Code2","Code3","Code4","Code6"])
                # for i in aoi:
                #     temp = []
                #     for j in i:
                #         temp.append(j)
                #     test.loc[len(test)] = temp
                # aoi = test
                # aoi = pd.DataFrame.from_records(aoi,columns=["Code1","Code2","Code3","Code4","Code6"])
                # print(aoi)
                aoi = aoi[(aoi['Code2']<3)]
                aoi['MF_Time'] = pd.to_datetime(aoi['Code3'] + ' ' + aoi['Code4'])
                aoi["Time_shift"] = aoi["MF_Time"] - pd.Timedelta(hours=7, minutes=40)  # 將早班開始時間(7:40)平移置0:00
                aoi['date'] = aoi['Time_shift'].dt.date # 以班別為基礎的工作日期 如2022-01-02 為 2022-01-02 7:40(早班開始) 到 2023-01-03 7:40(晚班結束)
                aoi['hour'] = aoi['Time_shift'].dt.hour+1 # 工作日期的第幾個小時 1~12為早班 13~24為晚班
                aoi['shift'] = pd.cut(aoi['hour'], bins=[0,12,24], labels=['D','N']) # 班別 1~12為早班(D) 13~24為晚班(N)
                
                # 每小時生產資訊
                hourly_dvs_mf = pd.DataFrame()
                hourly_dvs_mf['time'] = pd.date_range(aoi['date'].min(), pd.Timestamp(aoi['date'].max()) + pd.Timedelta(hours= 23), freq='h')
                hourly_dvs_mf['date'] = hourly_dvs_mf['time'].dt.date
                hourly_dvs_mf['hour'] = hourly_dvs_mf['time'].dt.hour+1
                hourly_dvs_mf['shift'] = pd.cut(hourly_dvs_mf['hour'], bins=[0,12,24], labels=['D','N'])
                hourly_dvs_mf.drop('time',axis=1, inplace=True)

                hourly_dvs_mf = pd.merge(hourly_dvs_mf, aoi.groupby(['date','hour']).ID.count().reset_index().rename(columns={'ID':'pcs'}), on=['date','hour'], how='outer') # 生產量
                hourly_dvs_mf = pd.merge(hourly_dvs_mf, aoi[aoi['Code2']==0].groupby(['date','hour']).ID.count().reset_index().rename(columns={'ID':'ng_num'}), on=['date','hour'], how='outer') # 不良品量
                hourly_dvs_mf['pcs'].fillna(0, inplace=True)
                hourly_dvs_mf['ng_num'].fillna(0, inplace=True)
                hourly_dvs_mf['ng_rate(%)'] = hourly_dvs_mf['ng_num'] / hourly_dvs_mf['pcs'] * 100 # 不良率

                hourly_dvs_mf = pd.merge(hourly_dvs_mf, aoi.drop_duplicates(['date','hour'], keep='first')[['date','hour','Time_shift']].rename(columns={'Time_shift':'first_prod_time'}) , on=['date','hour'], how='outer') # 各小時第一筆生產時間
                hourly_dvs_mf = pd.merge(hourly_dvs_mf, aoi.drop_duplicates(['date','hour'], keep='last')[['date','hour','Time_shift']].rename(columns={'Time_shift':'last_prod_time'}) , on=['date','hour'], how='outer') # 各小時最後一筆生產時間
                hourly_dvs_mf['operation_time'] = hourly_dvs_mf['last_prod_time'] - hourly_dvs_mf['first_prod_time']
                hourly_dvs_mf['operation_time'].fillna(pd.Timedelta(0), inplace=True)
                
                hourly_dvs_mf['Device_Name'] = dvs
                hourly_dvs_mf['AOI_measure'] = measure
                
                hourly_dvs_mf['pcs'] = hourly_dvs_mf['pcs'].astype(int)
                hourly_dvs_mf['ng_num'] = hourly_dvs_mf['ng_num'].astype(int)

                hourly_mf = hourly_mf.append(hourly_dvs_mf)
                
                # 日夜班 生產量 運作時間
                dn_dvs_mf = hourly_dvs_mf.groupby(['date','shift']).pcs.sum().reset_index() # 生產量
                dn_dvs_mf = pd.merge(dn_dvs_mf, hourly_dvs_mf.groupby(['date','shift'])['operation_time'].sum().reset_index(), on=['date','shift'], how='outer')
                dn_dvs_mf['pcs'] = dn_dvs_mf['pcs'].astype(int)
                
                dn_dvs_mf['Device_Name'] = dvs
                dn_dvs_mf['AOI_measure'] = measure

                dn_mf = dn_mf.append(dn_dvs_mf)
                
                # 計算operation day
                working = dn_dvs_mf[dn_dvs_mf['pcs']>0]
                dtime = working[working['shift']=='D']['operation_time']
                ntime = working[working['shift']=='N']['operation_time']
                dpcs = working[working['shift']=='D']['pcs']
                npcs = working[working['shift']=='N']['pcs']

                d_timelower = np.percentile(dtime,25) - 1.5*(np.percentile(dtime,75)-np.percentile(dtime,25)) #25%-1.5IQR
                n_timelower = np.percentile(ntime,25) - 1.5*(np.percentile(ntime,75)-np.percentile(ntime,25)) #25%-1.5IQR
                d_pcslower = np.percentile(dpcs,25) - 1.5*(np.percentile(dpcs,75)-np.percentile(dpcs,25)) #25%-1.5IQR
                n_pcslower = np.percentile(npcs,25) - 1.5*(np.percentile(npcs,75)-np.percentile(npcs,25)) #25%-1.5IQR

                dvs_operation_day = (
                    set(dn_mf[(dn_mf['shift']=='D') & ((dn_mf['operation_time']>=d_timelower) | (dn_mf['pcs']>=d_pcslower))]['date']) 
                    & set(dn_mf[(dn_mf['shift']=='N') & ((dn_mf['operation_time']>=n_timelower) | (dn_mf['pcs']>=n_pcslower))]['date'])
                )
                operation_day[dvs] = dvs_operation_day
                op_day = pd.DataFrame()
                op_day['date'] = sorted(list(dvs_operation_day))
                op_day['operation_day'] = 1
                
                # AOI 特徵 (每天)
                aoi_fea = pd.DataFrame()
                aoi_fea['date'] = pd.date_range(aoi['date'].min(), aoi['date'].max())
                aoi_fea['date'] = aoi_fea['date'].dt.date
                aoi_fea['Device_Name'] = dvs
                aoi_fea['AOI_measure'] = measure
                aoi_fea = pd.merge(aoi_fea, op_day, on='date', how='outer')
                
                aoi_fea = pd.merge(aoi_fea, aoi.groupby(['date']).ID.count().reset_index().rename(columns={'ID':'pcs'}), on='date', how='outer')
                aoi_fea = pd.merge(aoi_fea, aoi[aoi['Code2']==0].groupby(['date']).ID.count().reset_index().rename(columns={'ID':'ng_num'}), on='date', how='outer')
                aoi_fea['ng_rate(%)'] = aoi_fea['ng_num'] / aoi_fea['pcs'] * 100
                
                aoi_fea = pd.merge(aoi_fea, aoi.groupby(['date']).Code6.max().reset_index().rename(columns={'Code6':'ct_max'}), on='date', how='outer')
                aoi_fea = pd.merge(aoi_fea, aoi.groupby(['date']).Code6.mean().reset_index().rename(columns={'Code6':'ct_mean'}), on='date', how='outer')
                aoi_fea = pd.merge(aoi_fea, aoi.groupby(['date']).Code6.min().reset_index().rename(columns={'Code6':'ct_min'}), on='date', how='outer')
                aoi_fea.fillna(0, inplace=True)
                
                aoi_fea['pcs'] = aoi_fea['pcs'].astype(int)
                aoi_fea['ng_num'] = aoi_fea['ng_num'].astype(int)
                aoi_fea['operation_day'] = aoi_fea['operation_day'].astype(int)

                aoi_feature = aoi_feature.append(aoi_fea)
                print(aoi_feature)



            return
        
# async def 