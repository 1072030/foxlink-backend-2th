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


async def FullBackup(path: str):
    # path = '/app/backup.sql'
    env = await Env.objects.filter(key="backup_path").get_or_none()
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
