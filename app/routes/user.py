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
    PendingApproval,
    transaction
)
from app.services.user import (
    get_user_summary,
    add_pending_user,
    created_user,
    get_password_hash,
    delete_user_by_badge,
    get_worker_attendances,
)
from app.services.auth import (
    get_current_user,
    get_manager_active_user,
    verify_password,
    get_admin_active_user,
)
from app.models.schema import (
    UserBase,
    UserCreate,
    UserChangePassword,
    UserOut,
    UserOutWithWorkTimeAndSummary,
    UserPatch,
    UserStatus,
    WorkerAttendance,
    WorkerStatusDto,
    WorkerSummary,
    UserPedding
)

router = APIRouter(prefix="/users")


# @router.get("/", response_model=List[UserOut], tags=["users"])
# async def read_all_users(
#     user: User = Depends(get_admin_active_user), workshop_name: Optional[str] = None
# ):
#     """
#     查詢所有使用者
#     """
#     return


@router.get("/info", response_model=UserOutWithWorkTimeAndSummary, tags=["users"])
async def get_user_himself_info(user: User = Depends(get_current_user())):
    return

# RUBY: add api check worker-summary


@router.get("/worker-summary", response_model=WorkerSummary, tags=["users"])
async def get_worker_summary(user: User = Depends(get_current_user())):
    return await get_user_summary(user.badge)


@router.get("/worker-attendance", response_model=List[WorkerAttendance], tags=["users"])
async def get_user_attendances(user: User = Depends(get_current_user())):
    return await get_worker_attendances(user.badge)


@router.get("/check-user-status", response_model=UserStatus, tags=["users"])
async def check_user_status(user: User = Depends(get_current_user())):
    return

@router.get("/pending-approvals-list", tags=["users"])
async def pending_approvals_list(user: User = Depends(get_current_user())):
    return await PendingApproval.objects.all()

# @router.post("/change-password", tags=["users"])
# async def change_password(
#     dto: UserChangePassword, user: User = Depends(get_current_user())
# ):
#     if not verify_password(dto.old_password, user.password_hash):
#         raise HTTPException(
#             status_code=401, detail="The old password is not matched")

#     await user.update(
#         password_hash=get_password_hash(dto.new_password),
#         change_pwd=True
#     )

@router.post("/pending-approval-user", tags=["users"])
async def pending_approval_user(dto:UserPedding):
    """
    
    """
    return await add_pending_user(dto)

@router.post("/create-user", tags=["users"])
async def create_user(dto:List[UserCreate]):
    return await created_user(dto)


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




@router.patch("/{badge}", tags=["users"])
async def update_user_information(
    badge: str, dto: UserPatch, user: User = Depends(get_current_user())
):
    if user.level < UserLevel.manager.value:
        raise HTTPException(401, "You do not have permission to do this")

    return await user.update(**dto.dict())


# @router.delete("/{badge}", tags=["users"])
# async def delete_a_user_by_badge(
#     badge: str, user: User = Depends(get_admin_active_user)
# ):
#     await delete_user_by_badge(badge)
#     return True


# @router.get("/subordinates", tags=["users"], response_model=List[WorkerStatusDto])
# async def get_user_subordinates(user: User = Depends(get_manager_active_user)):
#     return await get_user_all_level_subordinates_by_badge(user.badge)


# @router.get("/mission-history", tags=["users"], response_model=List[MissionDto])
# async def get_user_mission_history(user: User = Depends(get_current_user())):
#     return await get_worker_mission_history(user.badge)


# @router.get("/overview", tags=["users"], response_model=DayAndNightUserOverview)
# async def get_all_users_overview(workshop_name: str, user: User = Depends(get_manager_active_user)):
#     return await get_users_overview(workshop_name)
