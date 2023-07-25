import sys
import uuid
import logging
import asyncio
import multiprocessing as mp
from fastapi import FastAPI
from app.env import MQTT_BROKER, MQTT_PORT, PY_ENV
from app.routes import (
    health,
    user,
    auth,
    log,
    system,
    backup,
    project
)
from app.core.database import api_db
# from app.mqtt import mqtt_client
from app.log import LOGGER_NAME
from fastapi.middleware.cors import CORSMiddleware
# from app.foxlink.db import foxlink_dbs

# dictConfig(LogConfig().dict())
logger = logging.getLogger(LOGGER_NAME)
logger.propagate = False

app = FastAPI(title="Foxlink API Backend", version="0.0.1")


# Adding CORS middleware
origins = [
    "http://localhost:3000",
    "http://localhost:8080",
    "http://localhost:8888",
    "http://127.0.0.1:8888",
    "http://127.0.0.1:8086",
    "http://140.118.157.9:43114",
    "http://192.168.65.210:8083",
    "http://140.118.157.9:8086",
    "http://192.168.65.210:8086",
    "http://ntust.foxlink.com.tw:*",
    "http://192.168.0.115:8080",
    "*"
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_origin_regex="http(?:s)?://(?:.+\.)?foxlink\.com\.tw(?::\d+)?",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Adding routers
app.include_router(health.router)
app.include_router(system.router)
app.include_router(user.router)
app.include_router(auth.router)
app.include_router(project.router)
# app.include_router(migration.router)
# app.include_router(statistics.router)
app.include_router(log.router)
# app.include_router(device.router)
# app.include_router(workshop.router)
# app.include_router(test.router)
# app.include_router(shift.router)
app.include_router(backup.router)

# if PY_ENV == 'dev':
#     app.include_router(test.router)


@app.on_event("startup")
async def startup():
    # connect to databases
    while True:
        try:
            await asyncio.gather(*[
                api_db.connect(),
                # foxlink_dbs.connect()
            ])
        except Exception as e:
            logger.error(f"Start up error: {e}")
            logger.error(f"Waiting for 5 seconds to restart")
            await asyncio.sleep(5)
        else:
            logger.info("Foxlink API Server startup complete.")
            break


@app.on_event("shutdown")
async def shutdown():
    # disconnect databases
    while True:
        try:
            await asyncio.gather(*[
                api_db.disconnect(),
                # foxlink_dbs.disconnect()
            ])
        except Exception as e:
            logger.error(f"Start up error: {e}")
            logger.error(f"Waiting for 5 seconds to restart")
            await asyncio.sleep(5)
        else:
            logger.info("Foxlink API Server shutdown complete.")
            break
