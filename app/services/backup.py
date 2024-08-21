from app.env import (
    DATABASE_HOST,
    DATABASE_USER,
    DATABASE_PASSWORD,
    DATABASE_NAME,
)
from app.core.database import (
    Env
)
from fastapi.responses import JSONResponse
import subprocess
# path:str

# 完整備份功能
async def FullBackup(path: str):
    # path = '/app/backup.sql'
    # 從env資料表中提取路徑
    env = await Env.objects.filter(key="backup_path").get_or_none()
    # 如果沒有路徑資料
    if env is None:
        mysqldump_cmd = f"mysqldump -h {DATABASE_HOST} -u {DATABASE_USER} -p{DATABASE_PASSWORD} {DATABASE_NAME} --lock-all-tables > {path}"
        await Env.objects.create(key="backup_path", value=path)
    else:
        if env.value != path:
            mysqldump_cmd = f"mysqldump -h {DATABASE_HOST} -u {DATABASE_USER} -p{DATABASE_PASSWORD} {DATABASE_NAME} --lock-all-tables > {path}"
            await Env.objects.filter(key="backup_path").update(value=path)
        else:
            mysqldump_cmd = f"mysqldump -h {DATABASE_HOST} -u {DATABASE_USER} -p{DATABASE_PASSWORD} {DATABASE_NAME} --lock-all-tables > {path}"
    try:
        # subprocess.run(mysqldump_cmd, shell=True, check=True)
        task = subprocess.check_output(mysqldump_cmd, shell=True).decode()
        # subprocess.Popen.wait(timeout=None)
        # output = task.communicate()[0]
        return JSONResponse(content={"message": "Database backup successful."})
    except subprocess.CalledProcessError as e:
        return JSONResponse(content={"error": f"Error: {e}"}, status_code=500)
