"""
和專案有關係
"""
from fastapi import APIRouter, Depends, status
from fastapi.exceptions import HTTPException
from typing import List
# from fastapi import Query
from app.core.database import (
    transaction,
    Project,
    ProjectUser,
    User,
    AuditActionEnum,
    AuditLogHeader,
    UserLevel,
    Task,
    TaskAction,
    TaskStatus,
    Env,
    Device,
    get_ntz_now
)
from app.services.project import (
    AddNewProjectWorker,
    SearchProjectDevices,
    AddNewProjectEvents,
    DeleteProjects,
    DeleteDevices,
    RemoveProjectWorker,
    PreprocessingData,
    UpdatePreprocessingData,
    TrainingData,
    PredictData,
    GetFoxlinkTables,
    AddNewProjects,
    auto_TrainingData
)
from app.services.auth import (
    get_current_user,
    checkUserProjectPermission,
    checkUserSearchProjectPermission,
    checkNewProjectPermission,
    checkAdminPermission,
    checkFoxlinkAuth,
)
from app.models.schema import NewProjectDto, NewUserDto
from datetime import datetime,date,timedelta
router = APIRouter(prefix="/project")


@router.get("/", tags=["project"])
async def get_all_project(user: User = Depends(get_current_user())):
    """
    取得所有專案內容(當前使用者權限內所有的專案)
    """
    # 取得專案id和專案名稱
    project_id_list, project_name_list = await checkUserSearchProjectPermission(user, UserLevel.project_worker.value)
    if len(project_id_list) != 0:
        return await (Project.objects.filter(
            id__in=project_id_list
        ).all())


@router.get("/users", tags=["project"])
async def get_all_project(project_id: int, user: User = Depends(get_current_user())):
    """
    取得對應專案內的所有人員(當前使用者權限內的專案)
    project_id:int 專案id
    """
    # 查看此使用者是否符合設定權限
    user = await checkUserProjectPermission(project_id, user, UserLevel.project_leader.value)

    try:
        user = await ProjectUser.objects.select_related(['user']).filter(project=project_id).all()
        format_data = []
        for i in user:
            format_data.append({
                'badge': i.user.badge,
                'username': i.user.username,
                'permission': i.permission
            })
        return format_data
    except:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Permission Denied"
        )


@router.delete("/", tags=["project"])
async def delete_devices(dto: List[NewProjectDto], user: User = Depends(get_current_user())):
    """
    刪除專案(僅專案管理者以上之人員)
    NewProjectDto
        project:str 專案名稱
        line:int    專案線號
        device:str  機台名稱
        ename:str   事件英文名稱
        cname:str   事件中文名稱
    """
    project_name = dto[0].project.upper()
    project = await Project.objects.filter(name=project_name).get_or_none()
    project_id = project.id
    # 查看此使用者是否符合設定權限
    user = await checkUserProjectPermission(project_id, user, UserLevel.project_manager.value)
    if user is not None:
        # 刪除機台
        devices_name = await DeleteDevices(dto)
        # 產生log
        await AuditLogHeader.objects.create(
            action=AuditActionEnum.DELECT_DEVICES.value,
            user=user.badge,
            project=project_id,
            description=f"Deleted devices:{devices_name}"
        )
        return
    else:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Permission Denied"
        )


@router.post("/add-project-worker", tags=["project"])
async def add_new_workers(dto: NewUserDto, user: User = Depends(get_current_user())):
    """
    新增專案內人員(會確認新增者權限)
    NewUserDto
        project_id:int 專案id
        user_id:str 員工id
        permission:int 員工權限
    """
    # 查看此使用者是否符合設定權限
    user = await checkUserProjectPermission(dto.project_id, user, UserLevel.project_leader.value)
    if user is not None:
        # 新增專案使用者
        await AddNewProjectWorker(dto.project_id, dto.user_id, dto.permission)
        # 產生log
        await AuditLogHeader.objects.create(
            action=AuditActionEnum.ADD_PROJECT_WORKER.value,
            user=user.badge,
            project=dto.project_id,
            description=f"{dto.user_id}"
        )
        return
    else:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Permission Denied"
        )


@router.delete("/remove-project-worker", tags=["project"])
async def delete_workers(project_id: int, user_id: str, user: User = Depends(get_current_user())):
    """
    新增專案內人員(admin、manager、leader)
    project_id: int 專案id
    user_id: str 員工id
    """
    # 查看此使用者是否符合設定權限
    user = await checkUserProjectPermission(project_id, user, UserLevel.project_leader.value)

    if user is not None:
        # 刪除專案中的員工
        await RemoveProjectWorker(project_id, user_id)
        # 產生log
        await AuditLogHeader.objects.create(
            action=AuditActionEnum.DELECT_PROJECT_WORKER.value,
            user=user.badge,
            project=project_id,
            description=f"{user_id}"
        )
        return
    else:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Permission Denied"
        )


@router.get("/search-project-devices", tags=["project"])
async def search_project_devices(project_name: str):
    """
    搜尋專案擁有的devices
    project_name: str 專案名稱
    """
    # 防呆 機台名稱不能為空
    if project_name == "":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=f"please input project"
        )      
    # 搜尋專案      
    return await SearchProjectDevices(project_name)

@router.post("/add-project-events", status_code=200, tags=["project"])
async def add_project_and_events(dto: List[NewProjectDto], start_date: date = None ,user: User = Depends(get_current_user())):
    """
    搜尋專案內的所有事件(新增者權限 = admin、manager)
    NewProjectDto
        project:str 專案名稱
        line:int    線號
        device:str  機台名稱
        ename:str   事件英文名稱
        cname:str   事件中文名稱
    """
    # project_id_list, project_name_list = await checkAdminPermission(user, UserLevel.project_manager.value)
    # 確認新增專案的使用者權限
    createProjectUser = await checkNewProjectPermission(user)

    if len(dto) == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=f"please select device"
        )
    # 確認起始日期
    if start_date is None:
        checkEnv = await Env.objects.filter(key="preprocess_days").get_or_none()
        if checkEnv is None:
            raise HTTPException(400,"can not find 'preprocess_days' env settings")
        preprocess_days = int(checkEnv.value)
        start_date = date.today() - timedelta(days = preprocess_days)
    # 新增專案
    project = await AddNewProjectEvents(dto,start_date)
    if project is not None:
        # 產生log
        await AuditLogHeader.objects.create(
            action=AuditActionEnum.ADD_NEW_PROJECT.value,
            user=user.badge,
            project=project.id,
            description=project.id
        )
    # 產生一系列tasks (前處理、日訓練、週訓練、日預測、週預測)讓系統可以自動排程任務
    tasks = [
            Task(
                action=TaskAction.DATA_PREPROCESSING.value,
                status=TaskStatus.Pending.value,
                project=project.id
            ),
            Task(
                action=TaskAction.TRAINING_DAY.value,
                status=TaskStatus.Pending.value,
                project=project.id
            ),
            Task(
                action=TaskAction.TRAINING_WEEK.value,
                status=TaskStatus.Pending.value,
                project=project.id
            ),
            Task(
                action=TaskAction.PREDICT_DAY.value,
                status=TaskStatus.Pending.value,
                project=project.id
            ),
            Task(
                action=TaskAction.PREDICT_WEEK.value,
                status=TaskStatus.Pending.value,
                project=project.id
            )
    ]
    await Task.objects.bulk_create(tasks)
    return

@router.get("/preprocessing-data", tags=["project"])
async def preprocessing_data(project_id: int, user: User = Depends(get_current_user())):
    """
    訓練前的前處理 : 產生資料表 aoi_feature dn_mf hourly_mf
    project_id: int 專案id
    """
    # 產生log
    await AuditLogHeader.objects.create(
        action=AuditActionEnum.DATA_PREPROCESSING_STARTED.value,
        user=user.badge,
        project = project_id,
        description=project_id
    )
    try:
        # 資料前處理
        await PreprocessingData(project_id)
        # 產生log
        await AuditLogHeader.objects.create(
            action=AuditActionEnum.DATA_PREPROCESSING_SUCCEEDED.value,
            user=user.badge,
            project=project_id,
            description=project_id
        )
        return
    except Exception as e:
        await AuditLogHeader.objects.create(
            action=AuditActionEnum.DATA_PREPROCESSING_FAILED.value,
            user=user.badge,
            project=project_id,
            description=project_id
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=f"DATA_PREPROCESSING_FAILED : {repr(e)}"
        )


@router.get("/update-preprocessing-data", tags=["project"])
async def update_preprocessing_data(project_id: int, user: User = Depends(get_current_user())):
    """
    每日前處理 產生資料表內容 : aoi_feature dn_mf hourly_mf
    """
    # 查看此使用者是否符合設定權限
    user = await checkUserProjectPermission(project_id, user, UserLevel.project_manager.value)
    try:
        # 每日資料前處理
        await UpdatePreprocessingData(project_id,user.badge)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=f"DAILY_PREPROCESSING_FAILED : {repr(e)}"
        )
    return


@router.get("/training-data", tags=["project"])
async def training_data(project_id: int, select_type: str, user: User = Depends(get_current_user())):
    """
    對前處理資料進行訓練 : 產生 model->.pkl檔 train_performance資料表內容
    project_id: int     專案id
    select_type: str    日訓練或是週訓練的選擇
    """
    try:
        # 開始訓練
        await TrainingData(project_id, select_type)
        if select_type == "day":
            await AuditLogHeader.objects.create(
                action=AuditActionEnum.TRAINING_SUCCEEDED_DAILY.value,
                user=user.badge,
                project=project_id,
                description=project_id
            )
        else:
            await AuditLogHeader.objects.create(
                action=AuditActionEnum.TRAINING_SUCCEEDED_WEEKLY.value,
                user=user.badge,
                project=project_id,
                description=project_id
            )
    except Exception as e:
        if select_type == "day":
            await AuditLogHeader.objects.create(
                action=AuditActionEnum.TRAINING_FAILED_DAILY.value,
                user=user.badge,
                project=project_id,
                description=project_id
            )
        else:
            await AuditLogHeader.objects.create(
                action=AuditActionEnum.TRAINING_FAILED_WEEKLY.value,
                user=user.badge,
                project=project_id,
                description=project_id
            )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=f"TRAINING_FAILED : {repr(e)}"
        )
    return

@router.get("/auto-training-data", tags=["project"])
async def auto_train(preprocessing_days: int, days_before_retrain: int, description: str):

    current_date = get_ntz_now().date()
    created_date = get_ntz_now()
    ago = current_date - timedelta(days=days_before_retrain)
    start_date = current_date - timedelta(days=preprocessing_days)
    devices = await Device.objects.all()  
    auto_train_device: List[Device] = []

    for device in devices:
        date = device.created_date.date()

        if date <= ago:
            device.retrain = True
            device.created_date = created_date
            device.start_date = start_date
            auto_train_device.append(device)

    if len(auto_train_device) != 0:
        await Device.objects.bulk_update(auto_train_device, ['retrain', 'created_date', 'start_date'])
    else:
        return
    
    projects = []
    for device in auto_train_device:
        if device.project.id not in projects:
            projects.append(device.project.id)
    # projects = set(device.project for device in auto_train_device)

    for project in projects:
        await AuditLogHeader.objects.create(
                action=AuditActionEnum.TRAINING_STARTED_WEEKLY.value,
                user='admin',
                project=project,
                description=project
            )
        try:
            await auto_TrainingData(project, 'day', start_date)  
            await AuditLogHeader.objects.create(
                action=AuditActionEnum.RETRAIN_SUCCEEDED_DAILY.value,
                project=project,
                description=project
            )
        except:
            await AuditLogHeader.objects.create(
                action=AuditActionEnum.RETRAIN_FAILED_DAILY.value,
                project=project,
                description=project
            )
        try:
            await auto_TrainingData(project, 'week', start_date)  
            await AuditLogHeader.objects.create(
                action=AuditActionEnum.RETRAIN_SUCCEEDED_WEEKLY.value,
                project=project,
                description=project
            )
        except:
            await AuditLogHeader.objects.create(
                action=AuditActionEnum.RETRAIN_FAILED_WEEKLY.value,
                project=project,
                description=project
            )

        await Device.objects.filter(project=project,retrain = True).update(retrain = False)
        

@router.post("/predict-data", tags=["project"])
async def predict_data(project_id: int, pred_type: str, user: User = Depends(get_current_user())):
    """
    從已訓練模型(.pkl)進行每日預測
    """
    await AuditLogHeader.objects.create(
        action=AuditActionEnum.PREDICT_STARTED.value,
        user=user.badge,
        project=project_id,
        description=project_id
    )
    try:
        await PredictData(project_id, pred_type,user.badge)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=f"PREDICT_FAILED : {repr(e)}"
        )
    return

@router.get('/tables',tags=["project"])
async def get_foxlink_tables(user: User = Depends(get_current_user())):
    """
    取得所有aoi資料表中的table_name
    """
    user = await checkAdminPermission(user)
    if user is not None:
        return await GetFoxlinkTables()
    

@router.post("/project", tags=["project"])
async def add_project(projects: List[str], user: User = Depends(get_current_user())):
    """
    新增專案名稱 (新增者權限 = admin)
    """
    # add new project
    user = await checkAdminPermission(user)
    if len(projects) == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=f"please select project"
        ) 
    if user is not None:
        projects = await AddNewProjects(projects,user)
        for project in projects:
            pjt = await Project.objects.filter(name=project).get_or_none()
            await AuditLogHeader.objects.create(
                action=AuditActionEnum.ADD_NEW_PROJECT.value,
                user=user.badge,
                project=pjt.id,
                description=str(projects)
            )
    return

@router.delete("/project", tags=["project"])
async def delete_projects(projects: List[str], user: User = Depends(get_current_user())):
    """
    刪除專案名稱(刪除者權限 = admin)
    """
    user = await checkAdminPermission(user)
    if len(projects) == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=f"please select project"
        ) 
    if user is not None:
        for project in projects:
            pjt = await Project.objects.filter(name=project).get_or_none()
        
        projects = await DeleteProjects(projects)
        await AuditLogHeader.objects.create(
            action=AuditActionEnum.DELECT_PROJECT.value,
            user=user.badge,
            project=pjt.id,
            description=str(projects)
        )
    return

@router.get("/task", tags=["project"])
async def check_project_task(user: User = Depends(get_current_user())):
    """
    確認專案機台新增進度
    """
    project_id_list, project_name_list = await checkUserSearchProjectPermission(user, UserLevel.project_worker.value)
    if len(project_id_list) != 0:
        formatData = []
        for project_id in project_id_list:
            data = await Project.objects.select_related(["tasks"]).filter(id = project_id).order_by('-id').get_or_none()
            if data is not None:
                tasks = await data.tasks.order_by('-id').all()
                for i in tasks:
                    project_name = data.name
                    action = i.action
                    if not any(item['project_name'] == project_name and item['action'] == action for item in formatData):
                    # if data.name not in formatData['project_name']:
                        temp = {}
                        temp['project_name'] = data.name
                        temp['action'] = i.action
                        temp['status'] = i.status
                        temp['created_date'] = i.created_date
                        temp['updated_date'] = i.updated_date
                        formatData.append(temp)
    return formatData


@router.get("/user-projects", tags=["project"])
async def get_all_project(user_id: str, user: User = Depends(get_current_user())):
    """
    取得人員對應的所有專案(當前使用者權限內的專案)
    """
    project_id_list, project_name_list = await checkUserSearchProjectPermission(user, UserLevel.project_leader.value)
    if len(project_id_list) != 0:
        try:
            projects = await ProjectUser.objects.select_related(['project']).filter(user=user_id).all()
            format_data = []
            for i in projects:
                if i.project.id in project_id_list:
                    format_data.append({
                        'badge': user_id,
                        'project_id': i.project.id,
                        'project':i.project.name,
                        'permission': i.permission
                    })
    

        except Exception as e:
            print(f"An error occurred: {e}")  
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal Server Error"
            )
    return format_data
    
@router.delete("/user-projects", tags=["project"])
async def delete_worker_projects(project_id:List[int], user_id: str, user: User = Depends(get_current_user())):
    """
    依照人員刪除參與專案的人員
    """
    project_id_list, project_name_list = await checkUserSearchProjectPermission(user, UserLevel.project_leader.value)
    if len(project_id_list) != 0:
        output = []
        try:
            projects = await ProjectUser.objects.select_related(['project']).filter(user=user_id).all()
            for pjt in projects:
                if pjt.project.id in project_id:
                    await pjt.delete()
                    output.append({
                            "project_name": pjt.project.name.upper()
                            })
                    project_id.remove(pjt.project.id)
                    if not project_id:
                        break

        except Exception as e:
            print(f"An error occurred: {e}")  
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal Server Error"
            )
    return output