#! /usr/bin/env bash
sleep 10;
mkdir -p logs/
mkdir -p model/
mkdir -p model_week/
python -m app.server_daemons &
sleep 15
curl -X GET "http://localhost/scheduler/pending-task-activate"