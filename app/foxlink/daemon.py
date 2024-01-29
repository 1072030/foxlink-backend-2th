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
    from datetime import datetime
    from app.log import logging, CustomFormatter, LOG_FORMAT_FILE
    from app.foxlink.db import foxlink_dbs
    from app.env import (
        DEBUG
    )
    from app.core.database import (
        transaction,
        get_ntz_now,
        api_db,
        Env,
        Project,
        AuditActionEnum,
        AuditLogHeader,
        PredictResult
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

    import traceback

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

    MAIN_ROUTINE_MIN_RUNTIME = 3600
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

    @transaction(callback=True)
    @ show_duration
    async def daily_project_preprocess_data():
        checkEnv = await Env.objects.filter(key="daily_project_preprocess").get_or_none()
        if checkEnv is None:
            raise HTTPException(400,"can not find 'daily_project_preprocess' env settings")

        updateTimer = datetime.strptime(checkEnv.value,'%H:%M:%S')
        if get_ntz_now() <= get_ntz_now().replace(hour=updateTimer.hour,minute=updateTimer.minute,second=updateTimer.second):
            return

        projects = await Project.objects.all()

        await asyncio.gather(*[
            PredictData(detail['project_id'],detail['select_type']) for detail in predict_required
        ])

        return
    
    @transaction(callback=True)
    @ show_duration
    async def daily_project_predict(handler=[]):
        checkEnv = await Env.objects.filter(key="daily_project_predict").get_or_none()
        if checkEnv is None:
            raise HTTPException(400,"can not find 'daily_project_predict' env settings")
        
        updateTimer = datetime.strptime(checkEnv.value,'%H:%M:%S')

        if get_ntz_now() <= get_ntz_now().replace(hour=updateTimer.hour,minute=updateTimer.minute,second=updateTimer.second):
            return

        projects = await Project.objects.select_related("devices").all()
        projects_temp = []
        for i in projects:
            checkSucceedLogs = await AuditLogHeader.objects.filter(
                action=AuditActionEnum.PREDICT_SUCCEEDED.value,
                created_date__gte=get_ntz_now().date(),
                description=i.id
            ).limit(1).get_or_none()
            checkFailLogs = await AuditLogHeader.objects.filter(
                action=AuditActionEnum.PREDICT_FAILED.value,
                created_date__gte=get_ntz_now().date(),
                description=i.id
            ).limit(3).all()

            # failed over three times => dont continue
            if checkSucceedLogs is None and len(checkFailLogs) != 3:
                projects_temp.append(i)

        if len(projects_temp) == 0:
            return

        # check predict result
        predict_required = []
        for project in projects_temp:
            for device in project.devices:
                checkPredictLogsDaily = await PredictResult.objects.filter(
                    device = device.id,
                    pred_type = 0
                ).limit(1).get_or_none()
                checkPredictLogsWeekly = await PredictResult.objects.filter(
                    device = device.id,
                    pred_type = 1
                ).limit(1).get_or_none()
                if checkPredictLogsDaily is not None:
                    predict_required.append({
                        "project_id":project.id,
                        "select_type":"day"
                    })
                if checkPredictLogsWeekly is not None:
                    predict_required.append({
                        "project_id":project.id,
                        "select_type":"week"
                    })
                break
        await asyncio.gather(*[
            PredictData(detail['project_id'],detail['select_type']) for detail in predict_required
        ])
        return
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

                await daily_project_predict()

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
