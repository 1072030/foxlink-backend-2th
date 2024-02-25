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


    def __getitem__(self, key):
        return self.event_dbs[key]

    async def get_device_names(self,project_name: str):

        full_cnames: List[str, str] = await self.device_db.fetch_all(
            f"SELECT device_ename, device_cname FROM `{FOXLINK_DEVICE_DB_NAME}`.`dev_func`"
        )

        full_cnames: Dict[str, str] = {k: v for k, v in full_cnames}
        query =  f"""
                SELECT DISTINCT dsl.Device_Name,dsl.Dev_Func,dsl.Line 
                from sfc.device_setting_log as dsl 
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
        return data
    
    async def get_all_project_tabels(self):
        stmt = (
            f"""
            Show tables;
            """
        )
        dbs = [db for db in self.event_dbs.values()]
        tables = await dbs[0].fetch_all(
            query=stmt
        )
        output = []
        for table in tables:
            format = re.sub(r"[\'\(\),]",'',str(table))
            output.append(format)

        return output

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


foxlink_dbs = FoxlinkDatabasePool()
