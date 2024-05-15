
import inspect
import logging
import asyncio
from fastapi import FastAPI,applications
from fastapi.openapi.docs import get_swagger_ui_html
from app.routes import (
    health,
    user,
    auth,
    log,
    system,
    backup,
    project,
    statistics,
    scheduler,
    task,
    test
)
from app.core.database import api_db
from app.log import LOGGER_NAME,CustomFormatter,LOG_FORMAT_FILE
from fastapi.middleware.cors import CORSMiddleware
from app.foxlink.db import foxlink_dbs

from app.routes.scheduler import asyncIOScheduler

logger = logging.getLogger(LOGGER_NAME)
logger.propagate = False
logger.addHandler(
    logging.FileHandler('logs/uvicorn.log', mode="w")
)
logger.handlers[-1].setFormatter(CustomFormatter(LOG_FORMAT_FILE))

def get_function_default_args(func):
    '''获取函数默认参数'''
    sign = inspect.signature(func)
    return {
        k: v.default
        for k, v in sign.parameters.items()
        if v.default is not inspect.Parameter.empty
    }

def swagger_monkey_patch(*args, **kwargs):
    """
    Wrap the function which is generating the HTML for the /docs endpoint and
    overwrite the default values for the swagger js and css.
    """
    param_dict = get_function_default_args(get_swagger_ui_html)
    swagger_js_url = param_dict['swagger_js_url'].replace('https://cdn.jsdelivr.net/npm/', 'https://unpkg.com/')
    swagger_css_url = param_dict['swagger_css_url'].replace('https://cdn.jsdelivr.net/npm/', 'https://unpkg.com/')
    return get_swagger_ui_html(
        *args, **kwargs,
        swagger_js_url=swagger_js_url,
        swagger_css_url=swagger_css_url
    )

applications.get_swagger_ui_html  = swagger_monkey_patch

app = FastAPI(title="Foxlink API Backend", version="0.0.1")


# Adding CORS middleware
origins = [
    "http://localhost:3000",
    "http://localhost:8080",
    "http://localhost:8888",
    "http://localhost:8088",
    "http://127.0.0.1:8888",
    "http://127.0.0.1:8086",
    "http://ntust.foxlink.com.tw:*",
    "http://ntust2.foxlink.com.tw:*",
    "http://192.168.0.115:8080",
    "http://192.168.65.212:*",
    "http://192.168.1.103:*",
    "http://192.168.50.130",
    "ntust2.foxlink.com.tw",
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
app.include_router(log.router)
app.include_router(backup.router)
app.include_router(statistics.router)
app.include_router(test.router)
app.include_router(scheduler.router)
app.include_router(task.router)


# import random
# import string
# import time
# @app.middleware("http")
# async def log_requests(request, call_next):
#     response = await call_next(request)
#     logger.info(f"{request.client.host}:{request.client.port} - {request.url._url} {request.scope['type']}/{request.scope['http_version']} {response.status_code}")
#     return response

@app.on_event("startup")
async def startup():
    # connect to databases
    while True:
        try:
            await asyncio.gather(*[
                api_db.connect(),
                foxlink_dbs.connect(),
            ])
            asyncIOScheduler.start()
            # remove job table
            foxlink_dbs.ntust_db.execute('TRUNCATE TABLE job')
            # Starting scheduler
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
                foxlink_dbs.disconnect(),
            ])
            asyncIOScheduler.shutdown()
        except Exception as e:
            logger.error(f"Start up error: {e}")
            logger.error(f"Waiting for 5 seconds to restart")
            await asyncio.sleep(5)
        else:
            logger.info("Foxlink API Server shutdown complete.")
            break
