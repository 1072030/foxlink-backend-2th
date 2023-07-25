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
    import ormar
    import pandas as pd
    import json
    from os.path import join
    from os import walk
    from typing import Any, Dict, List, Tuple, Optional
    from datetime import timedelta
    from app.log import logging, CustomFormatter, LOG_FORMAT_FILE
    # from app.models.schema import MissionDto, MissionEventOut
    from app.utils.utils import AsyncEmitter,BenignObj
    # from app.foxlink.model import FoxlinkEvent
    from app.utils.utils import DTO
    # from app.foxlink.utils import assemble_device_id
    # # from app.foxlink.db import foxlink_dbs
    from fastapi import HTTPException
    # from app.services.mission import (
    #     assign_mission,
    #     reject_mission,
    #     set_mission_by_rescue_position
    # )
    # from app.services.user import check_user_begin_shift
    # from app.services.migration import import_devices
    # from app.utils.utils import get_current_shift_type
    # from app.mqtt import mqtt_client
    from app.env import (
        DEBUG,
        UPLOAD_FILES_PATH
    )
    from multiprocessing import Process

    from app.core.database import (
        transaction,
        get_ntz_now,
        User,
        AuditLogHeader,
        AuditActionEnum,
        WorkerStatusEnum,
        UserLevel,
        api_db,
        Env
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

    MAIN_ROUTINE_MIN_RUNTIME = 3
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
    # @ show_duration
    # async def send_mission_notification_routine(handler=[]):
    #     missions = (
    #         await Mission.objects
    #         .filter(
    #             repair_end_date__isnull=True,
    #             notify_recv_date__isnull=True,
    #             is_done=False,
    #             worker__isnull=False
    #         )
    #         .select_related(
    #             [
    #                 "device", "worker", "device__workshop",
    #                 "worker__at_device", "events"
    #             ]
    #         )
    #         .exclude_fields(
    #             FactoryMap.heavy_fields("device__workshop")
    #         )
    #         .filter(
    #             events__event_end_date__isnull=True
    #         )
    #         .all()
    #     )
    #     # RUBY: related device workshop

    #     async def driver(m: Mission):
    #         if m.device.is_rescue == False:
    #             handler.append(
    #                 mqtt_client.publish(
    #                     f"foxlink/users/{m.worker.current_UUID}/missions",
    #                     {
    #                         "type": "new",
    #                         "mission_id": m.id,
    #                         "worker_now_position": m.worker.at_device.id,
    #                         "badge": m.worker.badge,
    #                         # RUBY: set worker now position and badge
    #                         "create_date": m.created_date,
    #                         "device": {
    #                             "device_id": m.device.id,
    #                             "device_name": m.device.device_name,
    #                             "device_cname": m.device.device_cname,
    #                             "workshop": m.device.workshop.name,
    #                             "project": m.device.project,
    #                             "process": m.device.process,
    #                             "line": m.device.line,
    #                         },
    #                         "name": m.name,
    #                         "description": m.description,
    #                         "notify_receive_date": None,
    #                         "notify_send_date": m.notify_send_date,
    #                         "events": [
    #                             MissionEventOut.from_missionevent(e).dict()
    #                             for e in m.events
    #                         ],
    #                         "timestamp": get_ntz_now()
    #                     },
    #                     qos=2,
    #                     retain=True
    #                 )
    #             )
    #         else:
    #             handler.append(
    #                 mqtt_client.publish(
    #                     f"foxlink/users/{m.worker.current_UUID}/move-rescue-station",
    #                     {
    #                         "type": "rescue",
    #                         "mission_id": m.id,
    #                         "worker_now_position": m.worker.at_device.id,
    #                         "badge": m.worker.badge,
    #                         # RUBY: set worker now position and badge
    #                         "create_date": m.created_date,
    #                         "device": {
    #                             "device_id": m.device.id,
    #                             "device_name": m.device.device_name,
    #                             "device_cname": m.device.device_cname,
    #                             "workshop": m.device.workshop.name,
    #                             "project": m.device.project,
    #                             "process": m.device.process,
    #                             "line": m.device.line,
    #                         },
    #                         "name": m.name,
    #                         "description": m.description,
    #                         "notify_receive_date": None,
    #                         "notify_send_date": m.notify_send_date,
    #                         "events": [],
    #                         "timestamp": get_ntz_now()
    #                     },
    #                     qos=2,
    #                     retain=True
    #                 )
    #             )

    #     await asyncio.gather(
    #         *[driver(m) for m in missions]
    #     )
    #     return True

    
    # done

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
                    # foxlink_dbs.connect(),
                    # mqtt_client.connect()
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
                    # mqtt_client.disconnect(),
                    # foxlink_dbs.disconnect()
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

                # await update_complete_events_handler()

                # await mission_shift_routine()

                # await move_idle_workers_to_rescue_device()

                # await check_mission_working_duration_overtime()

                # await check_mission_assign_duration_overtime()

                # await sync_events_from_foxlink_handler()

                # await early_login_mission_check()

                # await auto_rescue_point_generate()

                # await auto_remove_whitelist()

                # if not DISABLE_FOXLINK_DISPATCH:
                #     await mission_dispatch()

                # if time.perf_counter() - last_nofity_time > NOTIFICATION_INTERVAL:
                #     await send_mission_notification_routine()
                #     last_nofity_time = time.perf_counter()

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
