
from fastapi import APIRouter
from datetime import timedelta
from app.core.database import (
    Project,
    Task,
    TaskAction,
    TaskStatus,
    AuditLogHeader,
    AuditActionEnum,
    User,
    ProjectUser,
    get_ntz_now
)
from app.services.project import(
    PreprocessingData,
    TrainingData,
    PredictData
)
from typing import List
from fastapi.exceptions import HTTPException
import smtplib
from email.mime.text import MIMEText
from email.header import Header
router = APIRouter(prefix="/task")
@router.get("/", tags=["task"])
async def get_all_task():
    """
    取得所有的task
    """
    return await Task.objects.all()

@router.delete("/",tags=["task"])
async def remove_task(dto:List[str]):
    """
    刪除task 目前無作用
    """
    return

@router.post("/redo", tags=["task"])
async def redo_task(id:int,action:TaskAction,project:List[int]):
    """
    重新執行task
    """
    task = Task(
        action=action,
        stauts=TaskStatus.Pending.value,
       project=project)
    await Task.objects.create(task)

@router.get("/check-task", tags=["task"])
async def checking_task():
    """
    task queue的api
    """
    pending_task = await Task.objects.order_by('id').filter(status=TaskStatus.Pending.value).limit(1).get_or_none()
    processing_task = await Task.objects.order_by('id').filter(status=TaskStatus.Processing.value).limit(1).get_or_none()

    # 正在執行
    if processing_task is not None:
        # 運作時間過長
        # if processing_task.updated_date >= get_ntz_now() - timedelta(hours=3):
        #     processing_task.status = TaskStatus.Failure.value
        #     await processing_task.update()
        return
    
    # 沒有任務
    if pending_task is None:
        return
        
        #--- 執行任務
    args = pending_task.project.id
    pending_task.status = TaskStatus.Processing.value
    pending_task.updated_date = get_ntz_now()
    await pending_task.update()
    
    if pending_task.action == TaskAction.DATA_PREPROCESSING.value:
            await AuditLogHeader.objects.create(
                action=AuditActionEnum.DATA_PREPROCESSING_STARTED.value,
                user='admin',
                project=str(args),
                description=str(args)
            )
            try:
                await PreprocessingData(int(args))
                await AuditLogHeader.objects.create(
                    action=AuditActionEnum.DATA_PREPROCESSING_SUCCEEDED.value,
                    user='admin',
                    project=str(args),
                    description=str(args)
                )

                pending_task.status = TaskStatus.Succeeded.value
                pending_task.updated_date = get_ntz_now()
                await pending_task.update()

            except Exception as e:
                await AuditLogHeader.objects.create(
                    action=AuditActionEnum.DATA_PREPROCESSING_FAILED.value,
                    user='admin',
                    project=str(args),
                    description=f'{args} detail:{e.detail}'
                )
                project = await Project.objects.filter(id = args).get_or_none()
                pjt_users = await ProjectUser.objects.filter(project=args,permission__gte=3).select_related(["user"]).all()
                print(pjt_users)
                recipients = []
                for pjt_user in pjt_users:
                    recipients.append(pjt_user.user.email)

                if project:
                    if e.detail == "Not enough data.":
                        body = f'{project.name} :新增機台資料量過少，請重新選擇起始日期'
                    elif e.detail == "aoi_measure does not start from the same date":
                        body = f'{project.name} :新增機台之aoi_measure資料量不一致'
                    else:
                        body = f'{project.name} :新增機台前處理失敗'
                else:
                    if e.detail == "Not enough data.":
                        body = f'{args} :新增機台資料量過少，請重新選擇起始日期'
                    elif e.detail == "aoi_measure does not start from the same date":
                        body = f'{args} :新增機台之aoi_measure資料量不一致'
                    else:
                        body = f'{args} :新增機台前處理失敗'

                # 設置郵件內容
                subject = "設備預知保養系統通知"
                msg = MIMEText(body, 'plain', 'utf-8')
                msg['Subject'] = Header(subject, 'utf-8')
                msg['From'] = "Joey_Chen@cn.foxlink.com.tw"
                # msg['To'] = ", ".join(recipients)

                # 發送郵件
                smtp_server = "192.168.64.249"  # SMTP 伺服器
                smtp_port = 25  #  SMTP 端口

                with smtplib.SMTP(smtp_server, smtp_port) as smtpObj:
                    smtpObj.ehlo()
                    smtpObj.sendmail(msg['From'], recipients, msg.as_string())
                    smtpObj.quit()

                print("郵件發送成功")

                pending_task.status = TaskStatus.Failure.value
                await pending_task.update()

        # 日訓練
    elif pending_task.action == TaskAction.TRAINING_DAY.value:
            await AuditLogHeader.objects.create(
                action=AuditActionEnum.TRAINING_STARTED_DAILY.value,
                user='admin',
                project=str(args),
                description=str(args)
            )
            try:
                await TrainingData(int(args),'day')
                await AuditLogHeader.objects.create(
                    action=AuditActionEnum.TRAINING_SUCCEEDED_DAILY.value,
                    user='admin',
                    project=str(args),
                    description=str(args)
                )

                pending_task.status = TaskStatus.Succeeded.value
                pending_task.updated_date = get_ntz_now()
                await pending_task.update()

            except Exception as e:
                await AuditLogHeader.objects.create(
                    action=AuditActionEnum.TRAINING_FAILED_DAILY.value,
                    user='admin',
                    project=str(args),
                    description=f'{args} detail:{e}'
                )
                project = await Project.objects.filter(id = args).get_or_none()
                pjt_users = await ProjectUser.objects.filter(project=args,permission__gte=3).select_related(["user"]).all()
                print(pjt_users)

                recipients = []
                for pjt_user in pjt_users:
                    recipients.append(pjt_user.user.email)
                    
                if project:
                    body = f'{project.name} :新增機台日訓練失敗'
                else:    
                    body = f'{args} :新增機台日訓練失敗'
                
                 # 設置郵件內容
                subject = "設備預知保養系統通知"
                msg = MIMEText(body, 'plain', 'utf-8')
                msg['Subject'] = Header(subject, 'utf-8')
                msg['From'] = "Joey_Chen@cn.foxlink.com.tw"
                # msg['To'] = ", ".join(recipients)

                # 發送郵件
                smtp_server = "192.168.64.249"  # SMTP 伺服器
                smtp_port = 25  #  SMTP 端口

                with smtplib.SMTP(smtp_server, smtp_port) as smtpObj:
                    smtpObj.ehlo()
                    smtpObj.sendmail(msg['From'], recipients, msg.as_string())
                    smtpObj.quit()

                print("郵件發送成功")
                pending_task.status = TaskStatus.Failure.value
                await pending_task.update()


        # 週訓練
    elif pending_task.action == TaskAction.TRAINING_WEEK.value:
            await AuditLogHeader.objects.create(
                action=AuditActionEnum.TRAINING_STARTED_WEEKLY.value,
                user='admin',
                project=str(args),
                description=str(args)
            )
            try:
                await TrainingData(int(args),'week')
                await AuditLogHeader.objects.create(
                    action=AuditActionEnum.TRAINING_SUCCEEDED_WEEKLY.value,
                    user='admin',
                    project=str(args),
                    description=str(args)
                )

                pending_task.status = TaskStatus.Succeeded.value
                pending_task.updated_date = get_ntz_now()
                await pending_task.update()

            except Exception as e:
                await AuditLogHeader.objects.create(
                    action=AuditActionEnum.TRAINING_FAILED_WEEKLY.value,
                    user='admin',
                    project=str(args),
                    description=f'{args} detail:{e}'
                )
                project = await Project.objects.filter(id = args).get_or_none()
                pjt_users = await ProjectUser.objects.filter(project=args,permission__gte=3).select_related(["user"]).all()
                print(pjt_users)

                recipients = []
                for pjt_user in pjt_users:
                    recipients.append(pjt_user.user.email)
                    
                if project:
                    body = f'{project.name} :新增機台週訓練失敗'
                else:    
                    body = f'{args} :新增機台週訓練失敗'
                
                 # 設置郵件內容
                subject = "設備預知保養系統通知"
                msg = MIMEText(body, 'plain', 'utf-8')
                msg['Subject'] = Header(subject, 'utf-8')
                msg['From'] = "Joey_Chen@cn.foxlink.com.tw"
                # msg['To'] = ", ".join(recipients)

                # 發送郵件
                smtp_server = "192.168.64.249"  # SMTP 伺服器
                smtp_port = 25  #  SMTP 端口

                with smtplib.SMTP(smtp_server, smtp_port) as smtpObj:
                    smtpObj.ehlo()
                    smtpObj.sendmail(msg['From'], recipients, msg.as_string())
                    smtpObj.quit()

                print("郵件發送成功")

                pending_task.status = TaskStatus.Failure.value
                await pending_task.update()

        # 日預測
    elif pending_task.action == TaskAction.PREDICT_DAY.value:
            await AuditLogHeader.objects.create(
                action=AuditActionEnum.PREDICT_STARTED.value,
                user='admin',
                project=str(args),
                description=str(args)
            )
            try:
                await PredictData(int(args),'day','admin')
                await AuditLogHeader.objects.create(
                    action=AuditActionEnum.PREDICT_SUCCEEDED.value,
                    user='admin',
                    project=str(args),
                    description=str(args)
                )

                pending_task.status = TaskStatus.Succeeded.value
                pending_task.updated_date = get_ntz_now()
                await pending_task.update()

            except Exception as e:
                # await AuditLogHeader.objects.create(
                #     action=AuditActionEnum.PREDICT_FAILED.value,
                #     user='admin',
                #     description=f'{args} detail:{e}'
                # )
                project = await Project.objects.filter(id = args).get_or_none()
                pjt_users = await ProjectUser.objects.filter(project=args,permission__gte=3).select_related(["user"]).all()
                print(pjt_users)

                recipients = []
                for pjt_user in pjt_users:
                    recipients.append(pjt_user.user.email)
                    
                if project:
                    body = f'{project.name} :新增機台日預測失敗'
                else:    
                    body = f'{args} :新增機台日預測失敗'
                
                 # 設置郵件內容
                subject = "設備預知保養系統通知"
                msg = MIMEText(body, 'plain', 'utf-8')
                msg['Subject'] = Header(subject, 'utf-8')
                msg['From'] = "Joey_Chen@cn.foxlink.com.tw"
                # msg['To'] = ", ".join(recipients)

                # 發送郵件
                smtp_server = "192.168.64.249"  # SMTP 伺服器
                smtp_port = 25  #  SMTP 端口

                with smtplib.SMTP(smtp_server, smtp_port) as smtpObj:
                    smtpObj.ehlo()
                    smtpObj.sendmail(msg['From'], recipients, msg.as_string())
                    smtpObj.quit()

                print("郵件發送成功")

                pending_task.status = TaskStatus.Failure.value
                await pending_task.update()

        # 週預測
    elif pending_task.action == TaskAction.PREDICT_WEEK.value:
            await AuditLogHeader.objects.create(
                action=AuditActionEnum.PREDICT_STARTED.value,
                user='admin',
                project=str(args),
                description=str(args)
            )
            try:
                await PredictData(int(args),'week','admin')
                await AuditLogHeader.objects.create(
                    action=AuditActionEnum.PREDICT_SUCCEEDED.value,
                    user='admin',
                    project=str(args),
                    description=str(args)
                )

                pending_task.status = TaskStatus.Succeeded.value
                pending_task.updated_date = get_ntz_now()
                await pending_task.update()

            except Exception as e:
                # await AuditLogHeader.objects.create(
                #     action=AuditActionEnum.PREDICT_FAILED.value,
                #     user='admin',
                #     description=f'{args} detail:{e}'
                # )
                project = await Project.objects.filter(id = args).get_or_none()
                pjt_users = await ProjectUser.objects.filter(project=args,permission__gte=3).select_related(["user"]).all()
                print(pjt_users)

                recipients = []
                for pjt_user in pjt_users:
                    recipients.append(pjt_user.user.email)
                    
                if project:
                    body = f'{project.name} :新增機台週預測失敗'
                else:    
                    body = f'{args} :新增機台週預測失敗'
                
                 # 設置郵件內容
                subject = "設備預知保養系統通知"
                msg = MIMEText(body, 'plain', 'utf-8')
                msg['Subject'] = Header(subject, 'utf-8')
                msg['From'] = "Joey_Chen@cn.foxlink.com.tw"
                # msg['To'] = ", ".join(recipients)

                # 發送郵件
                smtp_server = "192.168.64.249"  # SMTP 伺服器
                smtp_port = 25  #  SMTP 端口

                with smtplib.SMTP(smtp_server, smtp_port) as smtpObj:
                    smtpObj.ehlo()
                    smtpObj.sendmail(msg['From'], recipients, msg.as_string())
                    smtpObj.quit()

                print("郵件發送成功")

                pending_task.status = TaskStatus.Failure.value
                await pending_task.update()

    return