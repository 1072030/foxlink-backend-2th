import asyncio
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from fastapi.security import OAuth2PasswordRequestForm
from app.mqtt import mqtt_client
from app.services.auth import authenticate_user, create_access_token, get_current_user, set_device_UUID
from datetime import datetime, timedelta, timezone
from app.core.database import (
    transaction,
    api_db,
    User,
    AuditLogHeader,
    AuditActionEnum,
    Device,
    Mission,
    UserLevel,
    WorkerStatusEnum
)
from app.core.database import get_ntz_now
from app.services.user import check_user_begin_shift
from app.services.mission import set_mission_by_rescue_position
from app.env import DISABLE_STARTUP_RESCUE_MISSION, PWD_SALT
from app.utils.utils import AsyncEmitter, BenignObj
from app.services.user import pwd_context

ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 12
# pwd_context = CryptContext(schemes=[PWD_SCHEMA], deprecated="auto")
# async def main():
#     await api_db.connect()
#     while True:
#         await asyncio.sleep(1)
#         await User.objects.get()
#         print("succeed")


async def main(username="admin", password="foxlink", client_id=""):
    await api_db.connect()
    form_data = BenignObj()
    form_data.password = password
    form_data.username = username
    form_data.client_id = client_id
    user = await authenticate_user(form_data.username, form_data.password)

    if user.status == WorkerStatusEnum.working.value:
        raise HTTPException(
            403, f'the worker on device : {user.current_UUID} is working now.'
        )

    # form_data.client_id

    access_token = create_access_token(
        data={
            "sub": user.badge,
            "UUID": form_data.client_id
        },
        expires_delta=timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    )

    changes = BenignObj()
    emitter = AsyncEmitter()

    changes.current_UUID = form_data.client_id
    changes.login_date = get_ntz_now()

    emitter.add(
        AuditLogHeader.objects.create(
            table_name="users",
            record_pk=user.badge,
            action=AuditActionEnum.USER_LOGIN.value,
            user=user,
        )
    )

    if await check_user_begin_shift(user):
        if (user.level == UserLevel.maintainer.value):
            rescue_missions = (
                await Mission.objects
                .select_related(["device"])
                .filter(
                    worker=user,
                    is_done=False
                )
                .get_or_none()
            )

            changes.shift_beg_date = get_ntz_now()
            changes.finish_event_date = get_ntz_now()
            changes.shift_reject_count = 0
            changes.shift_start_count = 0

            if (rescue_missions):
                emitter.add(
                    rescue_missions.update(
                        is_done=True,
                        is_done_cancel=True
                    )
                )

            if not DISABLE_STARTUP_RESCUE_MISSION and not user.start_position == None:
                # give rescue missiong if condition match
                await set_mission_by_rescue_position(
                    user,
                    user.start_position.id
                )
            else:
                changes.status = WorkerStatusEnum.idle.value
        else:
            changes.status = WorkerStatusEnum.idle.value
    else:
        # RUBY: prevent mission.device is null
        mission = await Mission.objects.select_related("device").filter(is_done=False, worker=user).get_or_none()

        if mission:
            if mission.device.is_rescue is True:
                changes.status = WorkerStatusEnum.notice.value
            elif (not mission.repair_beg_date == None):
                changes.status = WorkerStatusEnum.working.value
            elif (not mission.accept_recv_date == None):
                changes.status = WorkerStatusEnum.moving.value
            elif (not mission.notify_send_date == None):
                changes.status = WorkerStatusEnum.notice.value
        else:
            changes.status = WorkerStatusEnum.idle.value

    emitter.add(
        user.update(
            **changes.__dict__
        )
    )

    await emitter.emit()

    return {"access_token": access_token, "token_type": "bearer"}


if __name__ == "__main__":
    pwd = pwd_context.hash("foxlink", salt=PWD_SALT)
    import cProfile
    pr = cProfile.Profile()
    pr.enable()
    asyncio.run(main(password=pwd))
    pr.disable()
    pr.print_stats(sort='time')
