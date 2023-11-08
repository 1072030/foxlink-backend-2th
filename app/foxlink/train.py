"""
訓練模型
"""
import pandas as pd
import numpy as np
from datetime import datetime

from sklearn.tree import DecisionTreeClassifier
from sklearn.ensemble import RandomForestClassifier, AdaBoostClassifier, StackingClassifier
from sklearn.metrics import classification_report
from sklearn.preprocessing import MinMaxScaler
from sklearn.model_selection import train_test_split
from sklearn.svm import SVC
from imblearn.over_sampling import SMOTE, RandomOverSampler

from xgboost import XGBClassifier

from tqdm import tqdm
import joblib

from sqlalchemy import create_engine
from sqlalchemy.types import Float, Integer, Date, Time, DateTime, VARCHAR, DECIMAL, BigInteger, SmallInteger

from fastapi.exceptions import HTTPException
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
    PredTarget,
    ErrorFeature
)

import warnings
warnings.filterwarnings('ignore')


def connect_foxlink_db():
    # 從正崴資料庫讀取
    foxlink_charset = 'utf8'
    foxlink_engine = create_engine(f'mysql+pymysql://ntust:ntustpwd@172.21.0.1:12345/aoi?charset={foxlink_charset}')
    return foxlink_engine

def connect_ntust_db():
    ntust_charset = 'utf8'
    ntust_engine = create_engine(f'mysql+pymysql://root:AqqhQ993VNto@mysql-test:3306/foxlink?charset={ntust_charset}')
    return ntust_engine

class FoxlinkTrain:
    def __init__(self):
        self.s = ['random_forest', 'xgboost', 'adaboost', 'svm', 'decision_tree'] ## 屆時這裡要改成接收API
        self.Threshold = [0.5, 0.6, 0.65, 0.7, 0.8, 0.85, 0.9,0.91,0.92,0.93,0.94, 0.95, 0.96, 0.97,0.98, 0.99] 
        self.dvs_aoi = {
        'Device_5':['glue'],
        'Device_6':['clip'],
        'Device_8':['shell'],
        'Device_9':['barcode'],
        'Device_10':['force','llcr','os'],
        'Device_11':['leak','ccd1','ccd2','ccd3'],
        'Device_12':['ccd4','ccd5','ccd6','ccd7','scan'],
        'Device_13':['package']
        }
        self.ntust_engine = connect_ntust_db()
        self.foxlink_engine = connect_foxlink_db()
        
    async def data_preprocessing_from_sql(self,project_id:int):    
        """
        從台科資料庫讀取處理好的資料做portion and feature selection
        Returns:
            dict: 內容為每個Device的error特徵
        """
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
            event = await ErrorFeature.objects.filter(
                device=dvs.id,
                project=project_id
            ).all()
            event = set([row.message for row in event])
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
            # sql = f"""
            #     SELECT Measure_Workno FROM aoi.measure_info 
            #     WHERE 
            #         Workno_Order=1 and 
            #         Project='{project[0].name}'and
            #         Device_Name='{dvs.name}';
            # """
            # first_aoi_measure = pd.read_sql(sql, self.foxlink_engine)['Measure_Workno'][0].lower()
            
            for row in event: # 預測目標異常 Y
                # print(f"{get_ntz_now} : starting preprocessing {row.message}")
                sql = f"""
                    SELECT * FROM error_feature
                    WHERE 
                        device = '{dvs.id}' and 
                        project = {project_id} and 
                        message = '{row}'
                """
                target_Y = pd.read_sql(sql, self.ntust_engine)
                target_Y.rename(columns={'happened':row}, inplace=True)
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
                                aoi_measure = {measure_id} 
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
                        op_day_total_error = target_feature[target_feature['operation_day']==1][row].sum()

                        #計算平均發生次數
                        error_per_pcs = op_day_total_error / op_day_total_pcs # 計算比例

                        #
                        invalid_date_index = target_feature[target_feature['operation_day']==0].index
                        target_feature.loc[invalid_date_index, row] = round(target_feature.loc[invalid_date_index, measure+'_pcs'] * error_per_pcs) # 依照生產比例補值
                        
                    else:
                        sql = f"SELECT * FROM aoi_feature WHERE device = '{dvs.name}' and aoi_measure = '{measure_id}';"
                        aoi_fea = pd.read_sql(sql, self.ntust_engine)
                        aoi_fea.rename(columns={
                            'pcs':measure+'_pcs',
                            'ng_num':measure+'_ng_num',
                            'ng_rate(%)':measure+'_ng_rate(%)',
                            'ct_max':measure+'_ct_max',
                            'ct_mean':measure+'_ct_mean',
                            'ct_min':measure+'_ct_min'
                            }, inplace=True
                        )
                        aoi_fea.drop(['Device_Name','AOI_measure','operation_day'],axis=1, inplace=True)
                        target_feature = pd.merge(target_feature, aoi_fea, on=['date'], how='outer')
                # 加入同機台其他異常事件發生次數
                for others in event:
                    if others == row:
                        continue
                    else:
                        sql = f"SELECT date, category, happened FROM error_feature WHERE device = {dvs.id} and message = '{others}' and project={project_id};"
                        other_error_happened = pd.read_sql(sql, self.ntust_engine) # 預測目標異常的特徵
                        category = str(other_error_happened['category'].iloc[0])
                        other_error_happened.rename(columns={'happened':category}, inplace=True)
                        target_feature = pd.merge(target_feature, other_error_happened[['date', category]], on='date', how='outer')
                
                target_feature.sort_values('date', inplace=True)
                target_feature.reset_index(drop=True, inplace=True)
                steady_index = target_feature[target_feature['operation_day']==1].index.min() # 穩定生產第一天
                target_feature = target_feature[steady_index:]
                
                target_feature.drop(['device', 'message', 'category', 'operation_day'], axis=1, inplace=True)
                target_feature.fillna(0, inplace=True)
                target_feature.set_index('date', inplace=True)
                # feature selection
                pearson = target_feature.corr(method='pearson') # 線性相關
                spearman = target_feature.corr(method='spearman') # 非線性相關

                pf = set(pearson[row][pearson[row].abs()>0.4].index) # 選擇特徵
                sf = set(spearman[row][spearman[row].abs()>0.4].index) # 選擇特徵
                pnsf = list(pf|sf)
                target_feature.reset_index(inplace=True)
                input_data = pd.merge(target_feature[['date',row]], target_feature[['date']+pnsf])

                if dvs.name not in input_data_dict:
                    input_data_dict[dvs.name] = {}
                    
                input_data_dict[dvs.name][row] = input_data
    
        return input_data_dict
    
    def light_labeling(self, df, events, Threshold):
        df.rename(columns = {events:'count'}, inplace = True)
        cutting_point = np.quantile(df['count'], Threshold)
        # 轉換燈號
        df['light'] = df['count'].apply(lambda x: 0 if x < cutting_point else 1)
        # 平移
        df.light = df['light'].shift(-1)
        # 把空的那行移除
        df.dropna(inplace =True)
        lights = df.light.value_counts().reset_index()
        lights['Total'] = sum(lights['light'])
        lights['Percent'] = lights.apply(lambda x: x['light'] / x['Total'], axis = 1)
        lights.drop('Total', axis =1, inplace = True)
        print('實際切割點數值：', cutting_point)
        print('分群後個數：\n', lights)
        return df, lights, cutting_point
    
    def training_data_preprocessing(self ,df, scaler=True , upsample_method= 'upsample'):
        try:
            X = df.drop(['date', 'count', 'light'], axis =1)
        except:
            X = df.drop(['count', 'light'], axis =1)
        Y = df[['light']]
        ## 正規化
        if scaler == True:
            sc = MinMaxScaler()
            X = sc.fit_transform(X)
            print('正規化完成')

        x_train, x_test, y_train, y_test = train_test_split(X, Y, test_size = 0.2, random_state= 42)
        ## 這有設計 Upsample方法可以選，但Smote會報錯。
        if upsample_method == 'SMOTE':
            try: 
                print('upsample method: SMOTEUpsample')
                sm = SMOTE()
                x_train, y_train = sm.fit_resample(x_train, y_train)
            except:
                print('無法SMOTE, upsample method: RandomUpsample')
                oversample = RandomOverSampler(sampling_strategy='auto')
                x_train, y_train =  oversample.fit_resample(x_train, y_train)
        elif upsample_method == 'upsample':
            print('upsample method: RandomUpsample')
            oversample = RandomOverSampler(sampling_strategy='auto')
            x_train, y_train =  oversample.fit_resample(x_train, y_train)
        else:
            print('沒有這種upsample的方式，會報錯')

        self.X_train = x_train
        self.Y_train = y_train
        self.X_test = x_test
        self.Y_test = y_test
        print(f'訓練集: {self.X_train.shape, self.Y_train.shape} 測試集: {self.X_test.shape, self.Y_test.shape}')
    
    def select_model(self):
        selected = []
        ## 將被選中的model append到list中
        for m in self.s:
            if m == 'xgboost':
                selected.append(('xgb', XGBClassifier()))
            elif m == 'random_forest':
                selected.append(('rf', RandomForestClassifier()))
            elif m == 'adaboost':
                selected.append(('ada', AdaBoostClassifier()))
            elif m == 'decision_tree':
                selected.append(('dt', DecisionTreeClassifier()))
            elif m == 'svm':
                selected.append(('svm', SVC()))
            else:
                print('There is no model in this project')
        return selected
    
    def stacking(self, es):
        print('訓練模型')
        ## 這裡是Stacking的部分
        model = StackingClassifier(
            estimators=es,
            n_jobs=-1,
            final_estimator= RandomForestClassifier()
        )
        model.fit(self.X_train, self.Y_train)
        ts_pred = model.predict(self.X_test)
        ts_report =classification_report(self.Y_test, ts_pred, output_dict=True)
        return model, ts_report
    
    def ARF(self, report):
        acc = report['accuracy']
        ## 這邊是防呆，若切點切出只有一個標籤則會跳過不計算
        if '1.0' in report.keys():
            red_recall = report['1.0']['recall']
            red_f1 = report['1.0']['f1-score']
            try:
                arf = (3 / ((1/acc) + (1/red_recall) + (1/red_f1)) )
                return acc, red_recall ,red_f1 , arf
            except:
                return acc, red_recall ,red_f1, 0
        else:
            return acc, 0, 0, 0
        
    def map_category(self, dv, events):
        sql = f"SELECT category FROM pred_targets WHERE device={dv} and message='{events}';"
        ca = pd.read_sql(sql, self.ntust_engine)['category'].iloc[0]
        return ca
    
    def choose_agg_func(self,col_name):
        if 'mean' in col_name:
            return 'mean'
        elif 'max' in col_name:
            return 'max'
        elif 'min' in col_name:
            return 'min'
        else:
            return 'sum'
foxlink_train = FoxlinkTrain()