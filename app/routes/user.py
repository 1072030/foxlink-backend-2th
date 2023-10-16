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

router = APIRouter(prefix="/users")

@router.post("/get-off-work", tags=["users"])
async def get_off_work(
    reason: LogoutReasonEnum, to_change_status: bool = True, user: User = Depends(get_current_user(True))
):
    return await logout_routine(reason, to_change_status, user)


@transaction()
async def logout_routine(reason, to_change_status, user):
    if user.status != WorkerStatusEnum.idle.value and user.level == UserLevel.maintainer.value:
        raise HTTPException(400, '您不得登出除了闲置状态')

    user.logout_date = get_ntz_now()
    user.current_UUID = "0"
    if (not user.level == UserLevel.admin.value):
        user.status = WorkerStatusEnum.leave.value

    try:
        logout_user = await api_db.fetch_all(f"SELECT * FROM users WHERE badge ='{user.badge}' FOR UPDATE")
        if logout_user[0].status != WorkerStatusEnum.idle.value and logout_user[0].level == UserLevel.maintainer.value:
            raise HTTPException(400, '您不得登出除了闲置状态')
        await user.update()
    except Exception as e:
        print(f"error in transaction: {repr(e)}")
        raise HTTPException(
            400,"被指派任務了"
        )

    await AuditLogHeader.objects.create(
        user=user.badge,
        table_name="users",
        action=AuditActionEnum.USER_LOGOUT.value,
        description=reason.value,
    )
    return {
        "leave_time":user.updated_date + timedelta(hours=8)
    }
