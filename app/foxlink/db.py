"""
主要是連線到正崴資料庫的function
"""
import asyncio
import logging
from typing import Optional, Dict, Tuple, List
from databases import Database
from app.env import (
    DATABASE_USER,
    DATABASE_PASSWORD,
    DATABASE_HOST,
    DATABASE_PORT,
    DATABASE_NAME,
    FOXLINK_EVENT_DB_NAME,
    FOXLINK_EVENT_DB_HOSTS,
    FOXLINK_EVENT_DB_USER,
    FOXLINK_EVENT_DB_PWD,
    FOXLINK_EVENT_DB_TABLE_POSTFIX,
    FOXLINK_DEVICE_DB_NAME,
    FOXLINK_DEVICE_DB_HOST,
    FOXLINK_DEVICE_DB_USER,
    FOXLINK_DEVICE_DB_PWD,
)
import re
import pandas as pd
from sqlalchemy import create_engine
class FoxlinkDatabasePool:
    def __init__(self):
        self.connection:List[str] = (
            host+"@"+database 
                for host in FOXLINK_EVENT_DB_HOSTS 
                for database in FOXLINK_EVENT_DB_NAME
            )
        self.event_dbs: Dict[str, Database] = {
            host: Database(
                f"mysql+aiomysql://{FOXLINK_EVENT_DB_USER}:{FOXLINK_EVENT_DB_PWD}@{host.split('@')[0]}/{host.split('@')[1]}",
                min_size=3,
                max_size=5
            )
            for host in self.connection
        }
        self.device_db = Database(
            f"mysql+aiomysql://{FOXLINK_DEVICE_DB_USER}:{FOXLINK_DEVICE_DB_PWD}@{FOXLINK_DEVICE_DB_HOST}/{FOXLINK_DEVICE_DB_NAME}",
            min_size=3,
            max_size=5
        )
        self.ntust_db = create_engine(
            f'mysql+pymysql://{DATABASE_USER}:{DATABASE_PASSWORD}@{DATABASE_HOST+":"+str(DATABASE_PORT)}/{DATABASE_NAME}', pool_pre_ping=True
        )
        self.foxlink_db = create_engine(
            f'mysql+pymysql://{FOXLINK_EVENT_DB_USER}:{FOXLINK_EVENT_DB_PWD}@{FOXLINK_EVENT_DB_HOSTS[0]}/{FOXLINK_EVENT_DB_NAME[0]}',pool_pre_ping=True
        )
        # self.databases = [
        #     f"{FOXLINK_EVENT_DB_HOSTS[0]}@{FOXLINK_EVENT_DB_NAME[0]}",
        #     f"{FOXLINK_EVENT_DB_HOSTS[1]}@{FOXLINK_EVENT_DB_NAME[0]}"
        # ]

    def __getitem__(self, key):
        return self.event_dbs[key]

    async def get_device_names(self,project_name: str):
        # 取得所有事件英文和中文名稱
        full_cnames: List[str, str] = await self.device_db.fetch_all(
            f"SELECT device_ename, device_cname FROM `{FOXLINK_DEVICE_DB_NAME}`.`dev_func`"
        )
        # 轉換為dict格式
        full_cnames: Dict[str, str] = {k: v for k, v in full_cnames}
        # 依照正崴device_setting來取得此專案擁有的事件和機台
        query =  f"""
                SELECT DISTINCT dsl.Device_Name,dsl.Dev_Func,dsl.Line 
                from sfc.device_setting as dsl 
                where 
                    dsl.Project = :project and 
                    dsl.Dev_Func is not null 
        """
        project_names = await self.device_db.fetch_all(
            query=query,
            values={
                "project": project_name,
            }
        )

        # 重新整理資料格式
        project_detail = {}
        for i in project_names:
            name = i.Device_Name + "-" + i.Line
            aoi = re.split(',',i[1])
            if name not in project_detail.keys():
                project_detail[name] = project_detail.get(name,aoi)
            else:
                project_detail[name].extend(aoi)
                
        data = []
        for i in project_detail.keys():
            device = i.split('-')[0]
            line = int(i.split('-')[1])
            cname = ""
            ename = ""
            for j in project_detail[i]:
                cname += (full_cnames[j] + ",")
                ename += (j + ",")
                # [project_name,line,device,ename[:-1],cname[:-1]]
            data.append({
                "project":project_name,
                "line":line,
                "device":device,
                "ename":ename[:-1],
                "cname":cname[:-1]
            })
        # final output:
        #   "project":str, 專案名稱
        #   "line":int,    線號
        #   "device":str,  機台名稱
        #   "ename":str,   事件英文名稱
        #   "cname":str    事件中文名稱
        return data
    
    async def get_all_project_tabels(self):
        all_tables = []
        for db in self.event_dbs.values():
            tables = await db.fetch_all(query="SHOW TABLES;")
            formatted_tables = [re.sub(r"[\'\(\),]", '', str(table)) for table in tables]
            all_tables.extend(formatted_tables)
        return all_tables
    
    # -- edit by mike 2024/7/9
    async def get_server_ip(self,project_name):
        # 依照device_setting和facinfo表來找到對應專案所在的ip位置
        query = f"""
            select distinct fs.SUB_IP  
            from sfc.device_setting as dsl
            join sfc.facinfo as fs on fs.fac_code = dsl.FAC_CODE
            where dsl.Project = :project;
        """
        server_ip = await self.device_db.fetch_one(
            query=query,
            values = {
                "project":project_name
            }
        )
        # ------- this settings is for debug. You need to delete it before deploy to server
        if server_ip[0] == "172.168.1.231":
            return FOXLINK_EVENT_DB_HOSTS[0]
        elif server_ip[0] == "172.168.1.237":
            return FOXLINK_EVENT_DB_HOSTS[1]
        # ------- this settings is for debug. You need to delete it before deploy to server
        # output ex: 172.168.1.231:3306
        return f"{server_ip[0]}:{DATABASE_PORT}"
    # -- edit by mike 2024/7/9
    async def get_device_db(self,project_name,device_name):
        query = f"""
            select dsl.Category
            from sfc.device_setting dsl
            where
            dsl.Project = :project and
            dsl.Device_Name = :device and
            dsl.Category in ('AOI','HMI') and
            dsl.Enable = 1 and
            dsl.Read_Enabled = 1
        """
        query_db = await self.device_db.fetch_one(
            query = query,
            values = {
                "project":project_name,
                "device":device_name
            }
        )
        # output ex: AOI
        return query_db[0]
    # -- edit by mike 2024/7/9
    async def choose_database(self, project_name,device_name):
        server_ip = await self.get_server_ip(project_name)
        device_db = await self.get_device_db(project_name,device_name)

        return f"{server_ip}@{str(device_db).lower()}"


    async def connect(self):
        db_connect_routines = [db.connect() for db in self.event_dbs.values()]
        await asyncio.gather(*db_connect_routines)

        try:
            await self.device_db.connect()
        except:
            logging.warning("cannot connect to foxlink device DB.")

    async def disconnect(self):
        db_disconnect_routines = [
            db.disconnect()
            for db in self.event_dbs.values()
        ]
        await asyncio.gather(
            *db_disconnect_routines,
            self.device_db.disconnect()
        )

        if self.device_db.is_connected:
            await self.device_db.disconnect()

        # for db in self.databases:
        #     try:
        #         await foxlink_dbs[db].connect()
        #         project = await foxlink_dbs[db].fetch_one(query=stmt)
        #         await foxlink_dbs[db].disconnect()  # 确保断开连接
        #         if project is not None:
        #             return db
        #     except Exception as e:
        #         print(f"Error occurred while connecting to {db}: {e}")
        
    async def foxlink_db_engine(self, FOXLINK_AOI_DATABASE):
        host = FOXLINK_AOI_DATABASE.split('@')[0]
        name = FOXLINK_AOI_DATABASE.split('@')[1]
        path = create_engine(
            f'mysql+pymysql://{FOXLINK_EVENT_DB_USER}:{FOXLINK_EVENT_DB_PWD}@{host}/{name}',pool_pre_ping=True
        )
        
        return path       
    
foxlink_dbs = FoxlinkDatabasePool()
