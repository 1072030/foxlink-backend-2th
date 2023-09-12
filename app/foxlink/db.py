import asyncio
import logging
from typing import Optional, Dict, Tuple, List
# from app.core.database import Device
from databases import Database
from app.env import (
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

    def __getitem__(self, key):
        return self.event_dbs[key]

    # async def get_device_cnames(self, workshop_name: str):

    #     main_db = self.device_db

    #     all_cnames = await main_db.fetch_all(
    #         "SELECT Device_CName, Device_EName FROM `sfc`.`dev_func`"
    #     )

    #     cnames_dict: Dict[str, str] = {v: k for k, v in all_cnames}

    #     query = f"""
    #         SELECT distinct Project 
    #         FROM `sfc`.`device_setting` ds 
    #         WHERE ds.IP like (
    #             select concat('%', IP_Address, '%')
    #             from `sfc`.`layout_mapping` lm
    #             where lm.Layout = :workshop_name
    #         ) and Project != ''
    #     """

    #     project_names = await main_db.fetch_all(query, {"workshop_name": workshop_name})

    #     async def worker(p: str):
    #         return await main_db.fetch_all(
    #             """
    #             select Project, Line, Device_Name, Dev_Func
    #             from `sfc`.`device_setting` ds
    #             where Project = :project and Device_Name not like '%Repeater%';
    #             """,
    #             {"project": p},
    #         )

    #     resp = await asyncio.gather(*(worker(p[0]) for p in project_names))

    #     device_infos = {}

    #     for item in resp:
    #         device_infos[item[0]["Project"]] = [dict(x) for x in item]

    #     for _, v in device_infos.items():
    #         for info in v:
    #             split_ename = info["Dev_Func"].split(",")
    #             info["Dev_Func"] = [cnames_dict[x] for x in split_ename]
    #             info["Line"] = int(info["Line"])

    #     if device_infos == {}:
    #         return None

    #     return device_infos

    # async def get_device_cname(self, workshop: str, project: str, line: str, device: str):

    #     full_cnames: List[str, str] = await self.device_db.fetch_all(
    #         f"SELECT device_ename, device_cname FROM `{FOXLINK_DEVICE_DB_NAME}`.`dev_func`"
    #     )

    #     full_cnames: Dict[str, str] = {k: v for k, v in full_cnames}

    #     query = f"""
    #         SELECT ds.dev_func
    #         FROM `sfc`.`device_setting` as ds 
    #         WHERE ds.project LIKE :project AND ds.ip LIKE (
    #             SELECT CONCAT('%', lm.ip_address, '%')
    #             FROM `sfc`.`layout_mapping` as lm
    #             WHERE lm.layout = :workshop
    #         ) AND ds.device_name = :device AND ds.line = :line;
    #     """

    #     project_names = await self.device_db.fetch_one(
    #         query=query,
    #         values={
    #             "workshop": workshop,
    #             "project": project+"%",
    #             "line": line,
    #             "device": device
    #         }
    #     )
    #     try:
    #         ename_split = project_names["dev_func"].split(",")
    #         cname_list = ", ".join(
    #             [
    #                 full_cnames[ename]
    #                 for ename in ename_split
    #             ]
    #         )
    #     except:
    #         cname_list = "無法解析裝置中文名稱"

    #     return cname_list

    # async def get_db_tables(self, host: str,) -> Tuple[List[str], str]:
    #     database = host.split('@')[1]

    #     r = await self.event_dbs[host].fetch_all(
    #         "SELECT TABLE_NAME FROM information_schema.tables WHERE TABLE_SCHEMA = :schema_name AND TABLE_NAME LIKE :table_name",
    #         {
    #             "schema_name": database,
    #             "table_name": f"%{FOXLINK_EVENT_DB_TABLE_POSTFIX}"
    #         },
    #     )
    #     return (
    #         host,
    #         [x[0] for x in r]
    #     )

    # async def get_all_db_tables(self) -> List[List[str]]:
    #     devices = await Device.objects.filter(
    #         flag=True
    #     ).exclude(
    #         project="rescue"
    #     ).all()
    #     devices_project=[]
    #     for i in devices:
    #         if i.project.lower() not in devices_project:
    #             devices_project.append(i.project.lower())
            
    #     get_table_names_routines = [
    #         self.get_db_tables(host)
    #         for host in self.event_dbs.keys()
                
    #     ]
    #     return await asyncio.gather(*get_table_names_routines)

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
