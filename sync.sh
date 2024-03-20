#!/bin/bash
backend=/home/simslab/Foxlink2/foxlink-backend-2th/
frontend=/home/foxlink/Desktop/foxlink-second


final_backend=/home/ntust/foxlink-backend-2th/
final_frontend=/home/ntust/temp/

Host=192.168.65.212
User=ntust
# password = aa946809
# 更新端
# bash sync.sh set back
# bash sync.sh set front
if [ $1 = "set" ]
then 
    if [[ -n $3 ]] && [ $3 == "dry" ];# 判斷空值
    then
        if [ $2 == "back" ] 
        then
            rsync -avh --dry-run --exclude={".git",".github","model/*","model_week/*",".env","logs/*","*.tar","__pycache__/","alembic/","*.sql","sync.sh"} $backend $User@$Host:$final_backend
        elif [ $2 == "front" ]
        then 
            rsync -avh --dry-run --exclude ".git" --exclude "update.sh" $frontend $User@$Host:$final_frontend
        fi

    elif [ $2 == "back" ] 
    then
        rsync -avh --exclude={".git",".github","model/*","model_week/*",".env","logs/*","*.tar","__pycache__/","alembic/","*.sql","sync.sh"} $backend $User@$Host:$final_backend
    elif [ $2 == "front" ]
    then 
        rsync -avh --exclude ".git" --exclude "update.sh" $frontend $User@$Host:$final_frontend
    fi
fi