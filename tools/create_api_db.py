from os import system
import mysql.connector
import asyncio
from app.env import (
    DATABASE_HOST,
    DATABASE_PORT,
    DATABASE_USER,
    DATABASE_PASSWORD,
    DATABASE_NAME
)
from app.core.database import metadata, create_engine, api_db, User , Env

print(f"Working at Foxlink DB")
connection = mysql.connector.connect(
    host=DATABASE_HOST,
    user=DATABASE_USER,
    password=DATABASE_PASSWORD,
    port=DATABASE_PORT
)
cursor = connection.cursor()
##### DROP  TABLE #####
print("Dropping table...")
try:
    cursor.execute(
        f"""DROP DATABASE {DATABASE_NAME};"""
    )
    connection.commit()
except Exception as e:
    print(e)
##### BUILD TABLE ######
print("Creating table...")
try:
    cursor.execute(
        f"""CREATE DATABASE {DATABASE_NAME};"""
    )
    connection.commit()
except Exception as e:
    print(e)
##### BUILD SCHEMA ######
print("Creating Schema...")
try:
    # engine = create_engine(
    #     f"mysql://{DATABASE_USER}:{DATABASE_PASSWORD}@{DATABASE_HOST}:{DATABASE_PORT}/{DATABASE_NAME}")
    # metadata.create_all(engine)

    system("rm -rf /app/app/alembic/versions/* 2> /dev/null")
    system("alembic revision --autogenerate -m 'initialize'")
    system("alembic upgrade head")
except Exception as e:
    print(e)


##### BUILD DEFAULTS ######
async def create_default_entries():
    await api_db.connect()
    # check table exists

    if (await User.objects.count() == 0):
        await User.objects.create(
            badge='admin',
            username='admin',
            current_UUID=0,
            flag=1
        )
        envs = [
            Env(
                key="daily_preprocess_timer",
                value="23:00:00"
            ),
            Env(
                key="daily_predict_timer",
                value="23:20:00"
            )
        ]
        await Env.objects.bulk_create(envs)

    await api_db.disconnect()
print("Creating Default Entries...")
try:
    asyncio.run(create_default_entries())
except Exception as e:
    print(e)


##### END #######
print("All done!")
