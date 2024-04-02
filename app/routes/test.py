from datetime import datetime
from typing import List, Optional
from fastapi import APIRouter, Depends ,Response
from fastapi.exceptions import HTTPException
from datetime import timedelta
from app.core.database import (
    get_ntz_now,
    AuditActionEnum,
    LogoutReasonEnum,
    User,
    UserLevel,
    WorkerStatusEnum,
    AuditLogHeader,
    api_db,
    transaction
)
from app.services.auth import (
    get_current_user,
    get_manager_active_user,
    verify_password,
    get_admin_active_user,
)


router = APIRouter(prefix="/test")

@router.get("/", tags=["test"])
async def getUser():
    return await User.objects.all()

@router.post("/", tags=["test"])
async def NewUser(user_id:str,user_name:str):
    return await User.objects.create(badge=user_id,username=user_name)


@router.get("/predict_result", tags=["test"])
async def get_predict_result( user: User = Depends(get_current_user())):
    """
    儀表板內容和機況預測api
    """
    # formatData = {}
    # dvs_project_name = "D8X E00"
    # formatData[dvs_project_name] = {}
    # dvs_name ="Device_8"
    # formatData[dvs_project_name][dvs_name] = []
    # formatData[dvs_project_name][dvs_name].append({
    #     'id': "1",
    #     'name': "1",
    #     'category':1,
    #     'steady': 1, # steady  
    #     'ori_date': "1",
    #     'pred_date':"1",
    #     'frequency': "1",
    #     'happenLastTime':"can not find recently data",
    #     'happened_times':1,
    #     'line':1,
    #     'faithful': True
    #             })
    formatData = {
    "D7X E75": {
        "Device_5": [
            {
                "id": 8593,
                "name": "Glue异常",
                "category": 198,
                "steady": 0,
                "ori_date": "03-24",
                "pred_date": "03-30",
                "frequency": "週預測",
                "happenLastTime": None,
                "happened_times": 1,
                "line": 1,
                "faithful": True
            },
            {
                "id": 8595,
                "name": "UV检测站故障",
                "category": 191,
                "steady": 0,
                "ori_date": "03-24",
                "pred_date": "03-30",
                "frequency": "週預測",
                "happenLastTime": None,
                "happened_times": 0,
                "line": 1,
                "faithful": True
            },
            {
                "id": 8597,
                "name": "料盘取料上下气缸故障",
                "category": 5,
                "steady": 0,
                "ori_date": "03-24",
                "pred_date": "03-30",
                "frequency": "週預測",
                "happenLastTime":"2024-03-30 15: 30: 30",
                "happened_times": 1,
                "line": 1,
                "faithful": True
            },
            {
                "id": 8599,
                "name": "tray盘站故障",
                "category": 190,
                "steady": 0,
                "ori_date": "03-24",
                "pred_date": "03-30",
                "frequency": "週預測",
                "happenLastTime": None,
                "happened_times": 0,
                "line": 1,
                "faithful": False
            },
            {
                "id": 8601,
                "name": "House平移定位气缸故障",
                "category": 7,
                "steady": 0,
                "ori_date": "03-24",
                "pred_date": "03-30",
                "frequency": "週預測",
                "happenLastTime": None,
                "happened_times": 0,
                "line": 1,
                "faithful": True
            }
        ]
    }
}
    return formatData
