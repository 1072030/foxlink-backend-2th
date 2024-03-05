"""
daemon功能主要在派工系統的功能，在第二期預知保養不會使用到
設定是每3秒執行一次loop
"""



import argparse
parser = argparse.ArgumentParser()
# parser.add_argument('-i', dest='interval', type=int, default=10)


def create(**p):
    args = []
    for k, _v in p.items():
        args.append('-' + k)
        args.append(str(_v))
    parser.parse_args(args)
    return [__name__] + args


if __name__ == "__main__":
    import asyncio
    import signal
    import time
    import argparse
    from datetime import datetime,timedelta
    from app.log import logging, CustomFormatter, LOG_FORMAT_FILE
    from app.foxlink.db import foxlink_dbs
    from app.env import (
        DEBUG,
        FOXLINK_EVENT_DB_HOSTS,
        FOXLINK_EVENT_DB_NAME
    )
    from app.core.database import (
        transaction,
        get_ntz_now,
        api_db,
        Env,
        Project,
        AuditActionEnum,
        AuditLogHeader,
        PredictResult,
        AoiFeature,
    )
    from fastapi import HTTPException
    from app.services.project import(
        PredictData,
        UpdatePreprocessingData
    )
    from pymysql.err import (
        Warning, Error,
        InterfaceError, DataError, DatabaseError,
        OperationalError,
        IntegrityError, InternalError, NotSupportedError,
        ProgrammingError
    )
    from datetime import datetime
    from app.services.project import(
        PreprocessingData,
        UpdatePreprocessingData,
        PredictData
    )
    import json
    import traceback
    host = FOXLINK_EVENT_DB_HOSTS[0]+"@"+FOXLINK_EVENT_DB_NAME[0]
    logger = logging.getLogger(f"foxlink(daemon)")
    logger.addHandler(
        logging.FileHandler('logs/foxlink(daemon).log', mode="w")
    )
    logger.handlers[-1].setFormatter(CustomFormatter(LOG_FORMAT_FILE))
    if (DEBUG):
        logger.handlers[-1].setLevel(logging.DEBUG)
    else:
        logger.handlers[-1].setLevel(logging.WARN)

    _terminate = None

    MAIN_ROUTINE_MIN_RUNTIME = 60
    NOTIFICATION_INTERVAL = 30
    
    def show_duration(func):
        async def wrapper(*args, **_args):
            logger.info(f'[{func.__name__}] started running.')
            start = time.perf_counter()
            result = await func(*args, **_args)
            end = time.perf_counter()
            logger.info(f'[{func.__name__}] took {end - start:.2f} seconds.')
            return result
        return wrapper

    # @transaction(callback=True)
    # @show_duration
    # async def new_project_data_handler(handler=[]):
    #     checkEnv = await Env.objects.filter(key="new_preprocess_timer").get_or_none()
    #     if checkEnv is None:
    #         raise HTTPException(400,"can not find 'new_preprocess_timer' env settings")
        
    #     updateTimer = datetime.strptime(checkEnv.value,'%H:%M:%S')

    #     if get_ntz_now() <= get_ntz_now().replace(hour=updateTimer.hour,minute=updateTimer.minute,second=updateTimer.second):
    #         return
        
    #     projects = await Project.objects.all()
    #     project_ids = [i.id for i in projects]
    #     for i in projects:
    #         checklog = await AuditLogHeader.objects.filter(
    #             action=AuditActionEnum.DATA_PREPROCESSING_SUCCEEDED.value,
    #             description=i.id
    #         ).limit(1).get_or_none()
    #         if checklog is not None:
    #             project_ids.remove(i.id)

    #     bulk_create_started = [
    #         AuditLogHeader(
    #             action=AuditActionEnum.DATA_PREPROCESSING_STARTED.value,
    #             user='admin',
    #             description=i
    #         )for i in project_ids
    #     ]
    #     await AuditLogHeader.objects.bulk_create(bulk_create_started)
    #     # started 
    #     await asyncio.gather(
    #         *[PreprocessingData(project_id) for project_id in project_ids]
    #     )

    #     bulk_create_succeeded = [
    #         AuditLogHeader(
    #             action=AuditActionEnum.DATA_PREPROCESSING_SUCCEEDED.value,
    #             user='admin',
    #             description=i
    #         )for i in project_ids
    #     ]
    #     await AuditLogHeader.objects.bulk_create(bulk_create_succeeded)
    #     return


    @transaction(callback=True)
    @show_duration
    async def daily_project_data_handler(handler=[]):
        # 每日前處理時間 通常為 今日的早上 7:00
        checkEnv = await Env.objects.filter(key="daily_preprocess_timer").get_or_none()
        if checkEnv is None:
            raise HTTPException(400,"can not find 'daily_preprocess_timer' env settings")
        
        updateTimer = datetime.strptime(checkEnv.value,'%H:%M:%S')

        if get_ntz_now() <= get_ntz_now().replace(hour=updateTimer.hour,minute=updateTimer.minute,second=updateTimer.second):
            return

        # need add check logs detail
        projects = await Project.objects.all()
        project_ids = []
        for i in projects:
            # 確定專案前處理有成功執行
            checkPreProcessLogs = await AuditLogHeader.objects.filter(
                action=AuditActionEnum.DATA_PREPROCESSING_SUCCEEDED.value,
                description=i.id
            ).order_by('-created_date').limit(1).get_or_none()
            # check preprocess implement
            if checkPreProcessLogs is None:
                continue   

            # 確認今日前處理錯誤次數
            checkFailLogs = await AuditLogHeader.objects.filter(
                action=AuditActionEnum.DAILY_PREPROCESSING_FAILED.value,
                created_date__gte=get_ntz_now().date(),
                description=i.id
            ).limit(3).all()
    
            # 超過三次則不再執行
            if len(checkFailLogs) == 3:
                continue

            # 確認今日是否有執行每日前處理
            checkSucceedLog = await AuditLogHeader.objects.filter(
                action=AuditActionEnum.DAILY_PREPROCESSING_SUCCEEDED.value,
                created_date__gte=get_ntz_now().date(),
                description=i.id
            ).order_by('-created_date').limit(1).get_or_none()
            # check daily preprocess succeed implement
            if checkSucceedLog is None:
                project_ids.append(i.id)


        
        # 執行每日前處理
        await asyncio.gather(
            *[UpdatePreprocessingData(project_id,"admin") for project_id in project_ids]
        )

        return
    
    @transaction(callback=True)
    @ show_duration
    async def daily_project_predict_handler(handler=[]):
        # 每日預測時間 通常為 今日的早上 7:20
        checkEnv = await Env.objects.filter(key="daily_predict_timer").get_or_none()
        if checkEnv is None:
            raise HTTPException(400,"can not find 'daily_project_predict' env settings")
        
        updateTimer = datetime.strptime(checkEnv.value,'%H:%M:%S')
        if get_ntz_now() <= get_ntz_now().replace(hour=updateTimer.hour,minute=updateTimer.minute,second=updateTimer.second):
            return
        
        projects = await Project.objects.select_related(["devices", "devices__aoimeasures"]).all()
        projects_temp = []
        for i in projects:
            # 確認aoi_feature資料存在
            checkAoi_featureData = await AoiFeature.objects.filter(
                date__gte=get_ntz_now().replace(hour=0,minute=0,second=0,microsecond=0) + timedelta(days=-7)
            ).all()


            # # 確認每日預測是否成功執行過
            checkSucceedLogs = await AuditLogHeader.objects.filter(
                action=AuditActionEnum.PREDICT_SUCCEEDED.value,
                created_date__gte=get_ntz_now().replace(hour=0,minute=0,second=0,microsecond=0),
                description=i.id
            ).limit(1).get_or_none()
            # 確認每日預測錯誤次數
            checkFailLogs = await AuditLogHeader.objects.filter(
                action=AuditActionEnum.PREDICT_FAILED.value,
                created_date__gte=get_ntz_now().replace(hour=0,minute=0,second=0,microsecond=0),
                description=i.id
            ).limit(3).all()

            # 超過三次失敗 則不執行
            if checkSucceedLogs is None and len(checkFailLogs) != 3:
                projects_temp.append(i)

        if len(projects_temp) == 0:
            return

        # check predict result
        predict_required = []
        for project in projects_temp:
            for device in project.devices:
                predict_required.append({
                    "project_id":project.id,
                    "select_type":"day"
                })
                # 確認每週預測時間點
                if get_ntz_now().weekday() == 6:
                    predict_required.append({
                        "project_id":project.id,
                        "select_type":"week"
                    })
                break

        # 產生log
        bulk_create_started = []
        for deatil in predict_required:
            bulk_create_started.append(
                AuditLogHeader(
                    action=AuditActionEnum.PREDICT_STARTED.value,
                    user='admin',
                    description=deatil["project_id"]
                )
            )
        if len(bulk_create_started) != 0:
            await AuditLogHeader.objects.bulk_create(bulk_create_started)

        for detail in predict_required:
            await PredictData(detail['project_id'],detail['select_type'],"admin")

        return
    
    @transaction(callback=True)
    @ show_duration
    async def sync_foxlink_event_happened_handler(handler=[]):
        projects = await Project.objects.select_related(["devices","devices__events"]).all()
        result = await asyncio.gather(*[
            sync_foxlink_event_happened(project,device,event)
            for project in projects
            for device in project.devices
            for event in device.events
        ])
        # print(result)
        with open('happened.json','w') as jsonfile:
            result = {
                "data":result,
                "timestamp":f'{get_ntz_now()+timedelta(hours=8)}'
            }
            json.dump(result,jsonfile)
    async def sync_foxlink_event_happened(project,device,event):
        stmt = (
            f"SELECT * FROM `{project.name}_event_new` WHERE "
            f"Device_Name='{device.name}' AND "
            f"Line = {device.line} AND "
            f"Category = {event.category} AND "
            f"Message = '{event.name}' AND "
            f"Start_Time >= '{get_ntz_now().date()}' "
            "ORDER BY ID DESC "
            "LIMIT 100;"
        )

        try:
            row = await foxlink_dbs[host].fetch_all(query=stmt)
            return {
                "event_id":event.id,
                "recently":str(row[0]["Start_Time"]),
                "happened":len(row)
            }
        except:
            row = None
            return {
                "event_id":event.id,
                "recently":row,
                "happened":0
            }



    ######### main #########

    def shutdown_callback():
        global _terminate
        _terminate = True

    async def connect_services():
        api_db.options["min_size"] = 3
        api_db.options["max_size"] = 7
        while True:
            try:
                logger.info("Start to Create Connections.")
                await asyncio.gather(
                    api_db.connect(),
                    foxlink_dbs.connect(),
                )
            except Exception as e:
                logger.error(f"{e}")
                logger.error(f"Cannot connect to the databases and servers")
                logger.error(f"Reconnect in 5 seconds...")
                await asyncio.sleep(5)
            else:
                logger.info("All Connections Created.")
                break

    async def disconnect_services():
        while True:
            logger.info("Termiante Databases/Connections...")
            try:
                await asyncio.gather(
                    api_db.disconnect(),
                    foxlink_dbs.disconnect()
                )
            except Exception as e:
                logger.error(f"{e}")
                logger.error(f"Cannot disconnect to the databases and servers")
                logger.error(f"Reconnect in 5 seconds...")
                await asyncio.wait(5)
            else:
                logger.info("All Services Disconnected.")
                break

    async def general_routine():
        global _terminate
        logger.info(f"General Routine Start @{get_ntz_now()}")
        last_nofity_time = time.perf_counter()
        while (not _terminate):
            try:
                logger.info('[main_routine] Foxlink daemon is running...')

                beg_time = time.perf_counter()

                await daily_project_data_handler()

                await daily_project_predict_handler()

                await sync_foxlink_event_happened_handler()

                end_time = time.perf_counter()

                logger.info(
                    "[main_routine] took %.2f seconds", end_time - beg_time
                )

                if (end_time - beg_time < MAIN_ROUTINE_MIN_RUNTIME):
                    await asyncio.sleep(max(MAIN_ROUTINE_MIN_RUNTIME - (end_time - beg_time), 0))
            except InterfaceError as e:
                logger.error(f'Connection error occur in general routines: {repr(e)}')
                traceback.print_exc()
                logger.error(f'Waiting 3 seconds to restart...')
                await asyncio.sleep(3)
                continue
            except Exception as e:
                logger.error(f'Unknown excpetion occur in general routines: {repr(e)}')
                traceback.print_exc()
                logger.error(f'Waiting 5 seconds to restart...')
                await asyncio.sleep(5)
                continue
            else:
                continue

    async def notify_routine():
        global _terminate
        while (not _terminate):
            try:
                # await send_mission_notification_routine()

                await asyncio.sleep(1)

            except Exception as e:
                logger.error(f'Unknown excpetion in notify routines: {repr(e)}')
                traceback.print_exc()
                logger.error(f'Waiting 5 seconds to restart...')
                await asyncio.sleep(5)

    async def main():
        global _terminate
        _terminate = False
        loop = asyncio.get_event_loop()
        loop.add_signal_handler(signal.SIGINT, shutdown_callback)
        loop.add_signal_handler(signal.SIGTERM, shutdown_callback)

        logger.info("Daemon Initilialized.")

        ###################################################

        # connect to services
        await connect_services()
        try:
            # main loop
            await asyncio.gather(
                general_routine()
                # ,notify_routine()
            )
        except Exception as e:
            logger.error(f"Exception Caught at main:{e}")
        # disconnect to services
        await disconnect_services()
        ###################################################

        logger.info("Daemon Terminated.")

    args = parser.parse_args()

    asyncio.run(
        main(),
        debug=DEBUG
    )
