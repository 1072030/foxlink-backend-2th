"""
預測機台發生時間
"""

import pandas as pd
import numpy as np
from datetime import datetime,timedelta

from tqdm import tqdm

import joblib

from glob import glob
from sklearn.preprocessing import MinMaxScaler


# from sqlalchemy import create_engine
from app.foxlink.db import foxlink_dbs

from fastapi.exceptions import HTTPException
from app.core.database import (
    transaction,
    get_ntz_now,
    Project,
    ProjectEvent,
    Device,
    ErrorFeature
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
import warnings
warnings.filterwarnings('ignore')
# def engine(user: str, password: str, host: str, database: str):
#     return f'mysql+pymysql://{user}:{password}@{host}/{database}'

# ntust_engine = create_engine(engine(
#     DATABASE_USER, DATABASE_PASSWORD, DATABASE_HOST+":"+str(DATABASE_PORT), DATABASE_NAME))
# foxlink_engine = create_engine(
#     engine(FOXLINK_EVENT_DB_USER, FOXLINK_EVENT_DB_PWD, FOXLINK_EVENT_DB_HOSTS[0], FOXLINK_EVENT_DB_NAME[0]))




class FoxlinkPredict:
    def __init__(self) -> None:
        self.ntust_engine = foxlink_dbs.ntust_db
        self.foxlink_engine = foxlink_dbs.foxlink_db
        
    async def data_preprocessing_from_sql(self,project_id:int,select_type:str):
        ## Todo：要將SQL目標改成要query的時間，這邊先以原數據做示範。
        infos = {}
        if select_type == "day":
            predict_date = get_ntz_now().date() + timedelta(days=-1)
        elif select_type == "week":
            predict_date = get_ntz_now().date() + timedelta(days=-7)
        project = await Project.objects.filter(id=project_id).select_related(
            ["devices","devices__aoimeasures"]
        ).all()
        if project is None:
            raise HTTPException(
                    status_code=400, detail="this project doesnt existed.")
        # 用來存每個device的每個error的輸入表
        input_data_dict = {}
        for dvs in project[0].devices:
            print(f"{get_ntz_now()} : starting preprocessing {dvs.name}")
            device_events = await Device.objects.filter(id=dvs.id).select_related(["events"]).all()
            all_events = device_events[0].events
            event = []
            for i in all_events:
                check  = await ErrorFeature.objects.filter(event=i.id).order_by("-date").limit(1).get_or_none()
                if check is None:
                    continue
                event.append(i.id)

            events = await ProjectEvent.objects.filter(id__in=event).all()

            # aoi measure日期改成1天
            sql = f"""
                SELECT Measure_Workno FROM aoi.measure_info 
                WHERE 
                    Device_Name='{dvs.name}' and
                    Project='{project[0].name}'
                    ORDER BY Workno_Order;
            """
            dvs_aoi_measure = pd.read_sql(sql, self.foxlink_engine)['Measure_Workno']
            first_aoi_measure = dvs_aoi_measure[0].lower()
            ntust_measure = await Device.objects.select_related(['aoimeasures']).filter(name=dvs.name).all()
            # ntust_measure = for i in ntust_measure[0].aoimeasures
            ntust_measure = ntust_measure[0].aoimeasures
            
            for row in events: # 預測目標異常 Y
                # print(f"{get_ntz_now} : starting preprocessing {row.message}")
                sql = f"""
                    SELECT * FROM error_feature
                    WHERE 
                        device = '{dvs.id}' and 
                        project = {project_id} and 
                        event = '{row.id}' and
                        date >= '{predict_date}'
                """
                target_Y = pd.read_sql(sql, self.ntust_engine)
                target_Y.rename(columns={'happened':row.name}, inplace=True)
                target_feature = target_Y.drop('operation_day', axis=1)

                # 加入AOI檢測特徵
                for measure in dvs_aoi_measure:
                    measure = measure.lower()
                    for i in ntust_measure:
                        if i.name == measure:
                            measure_id = i.id

                    if measure == first_aoi_measure: # 用第一個AOI生產數做比例補值
                        sql = f"""
                            SELECT * FROM aoi_feature 
                            WHERE 
                                device = {dvs.id} and 
                                aoi_measure = {measure_id} and
                                date >= '{predict_date}'
                        """
                        aoi_fea = pd.read_sql(sql, self.ntust_engine)
                        aoi_fea.rename(columns={
                            'pcs':measure+'_pcs',
                            'ng_num':measure+'_ng_num',
                            'ng_rate':measure+'_ng_rate',
                            'ct_max':measure+'_ct_max',
                            'ct_mean':measure+'_ct_mean',
                            'ct_min':measure+'_ct_min'
                            }, inplace=True
                    )

                        #移除不需要的欄位
                        aoi_fea.drop(['device','aoi_measure'],axis=1, inplace=True)
                        
                        #合併兩個dataframe
                        target_feature = pd.merge(target_feature, aoi_fea, on=['date'], how='outer')

                        #補0
                        target_feature[['operation_day', measure+'_pcs']] = target_feature[['operation_day', measure+'_pcs']].fillna(0)

                        #所有可執行日的pcs總和
                        op_day_total_pcs = aoi_fea[aoi_fea['operation_day']==1][measure+'_pcs'].sum()

                        #將發生次數總和
                        op_day_total_error = target_feature[target_feature['operation_day']==1][row.name].sum()

                        #計算平均發生次數
                        if op_day_total_pcs != 0:
                            error_per_pcs = op_day_total_error / op_day_total_pcs # 計算比例
                        else:
                            error_per_pcs = 0

                        #
                        invalid_date_index = target_feature[target_feature['operation_day']==0].index
                        target_feature.loc[invalid_date_index, row.name] = round(target_feature.loc[invalid_date_index, measure+'_pcs'] * error_per_pcs) # 依照生產比例補值
                        
                    else:
                        sql = f"SELECT * FROM aoi_feature WHERE device = '{dvs.name}' and aoi_measure = '{measure_id}' and date >= '{predict_date}';"
                        aoi_fea = pd.read_sql(sql, self.ntust_engine)
                        aoi_fea.rename(columns={
                            'pcs':measure+'_pcs',
                            'ng_num':measure+'_ng_num',
                            'ng_rate':measure+'_ng_rate',
                            'ct_max':measure+'_ct_max',
                            'ct_mean':measure+'_ct_mean',
                            'ct_min':measure+'_ct_min'
                            }, inplace=True
                        )
                        aoi_fea.drop(['device','aoi_measure','operation_day'],axis=1, inplace=True)
                        target_feature = pd.merge(target_feature, aoi_fea, on=['date'], how='outer')
                # 加入同機台其他異常事件發生次數
                for others in events:
                    if others.name == row.name:
                        continue
                    else:
                        sql = f"""
                        SELECT e.date, p.category, e.happened 
                        FROM error_feature as e 
                        JOIN project_events as p 
                        ON p.id=e.event 
                        WHERE 
                            e.device = {dvs.id} and 
                            e.event = {others.id} and 
                            e.project={project_id} and
                            e.date >= '{predict_date}';
                        """
                        other_error_happened = pd.read_sql(sql, self.ntust_engine) # 預測目標異常的特徵
                        if other_error_happened.empty:
                            raise HTTPException(400,"this error feature is empty")
                        category = str(other_error_happened['category'].iloc[0])
                        other_error_happened.rename(columns={'happened':category}, inplace=True)
                        target_feature = pd.merge(target_feature, other_error_happened[['date', category]], on='date', how='outer')
                
                target_feature.sort_values('date', inplace=True)
                target_feature.reset_index(drop=True, inplace=True)
                # steady_index = target_feature[target_feature['operation_day']==1].index.min() # 穩定生產第一天
                # print(target_feature)
                # target_feature = target_feature[steady_index:]
                
                target_feature.drop(['device', 'event','operation_day'], axis=1, inplace=True)
                target_feature.fillna(0, inplace=True)
                target_feature.set_index('date', inplace=True)

                target_feature.reset_index(inplace=True)
                #---------------
                ## 建立 SQL command
                get_trained_info_sql = f"SELECT * FROM train_performances WHERE device= '{dvs.id}' and event = '{row.id}' and freq = '{select_type}';"
                ## 從SQL讀取訓練後的資訊
                trained_info = pd.read_sql(get_trained_info_sql, self.ntust_engine)
                ## 轉換時間
                trained_info['created_date'] = pd.to_datetime(trained_info['created_date']).dt.strftime('%Y/%m/%d %H:%M')
                ## 排序時間，descending
                trained_info.sort_values('created_date',ascending=False , inplace=True)
                ## 提取目標列
                trained_info = trained_info.iloc[[0]]
                ## 因欄位寫入SQL時轉換為str，這邊在把轉換回List
                trained_info['used_col'] = trained_info['used_col'].apply(lambda x: eval(x))
                ## Mappping該事件用什麼欄位訓練
                map_col = trained_info.iloc[0]['used_col'] +['date']
                map_col.remove('count')
                input_data = target_feature[map_col]
                
                if dvs.name not in input_data_dict:
                    input_data_dict[dvs.name] = {}
                    infos[dvs.name] = {}
                input_data_dict[dvs.name][row.name] = input_data
                infos[dvs.name][row.name] = trained_info[['device', 'event', 'created_date', 'actual_cutpoint', 'threshold']]
        return input_data_dict, infos
    
    def fit_model_data_preprocessing(self, df, scaler=True):
        X = df.drop(['date'], axis =1)
        if scaler == True:
            sc = MinMaxScaler()
            X = sc.fit_transform(X)
        return X

    def map_model(self, dv,device_id, event_id, time,timetype):
        # sql = f"SELECT category FROM pred_targets WHERE device= {device_id} and event='{error}';"
        # ca = pd.read_sql(sql, self.ntust_engine)['category'].iloc[0]
        sql = f"""
            SELECT pe.category 
            FROM pred_targets as pt
            JOIN project_events as pe
            ON pe.id=pt.event
            WHERE 
                pt.device={device_id} and 
                pt.event='{event_id}';
            """
        ca = pd.read_sql(sql, self.ntust_engine)['category'].iloc[0]
        if timetype == 'week':
            model = joblib.load(f'/app/model_week/{dv}_{ca}_{time}.pkl')
        else:
            model = joblib.load(f'/app/model/{dv}_{ca}_{time}.pkl')
        return model
    
    def choose_agg_func(self,col_name):
        if 'mean' in col_name:
            return 'mean'
        elif 'max' in col_name:
            return 'max'
        elif 'min' in col_name:
            return 'min'
        else:
            return 'sum'
foxlink_predict = FoxlinkPredict()