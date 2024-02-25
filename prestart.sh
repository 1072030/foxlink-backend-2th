#! /usr/bin/env bash
sleep 10;
mkdir -p logs/
mkdir -p model/
mkdir -p model_week/
cat > happenend.json
python -m app.server_daemons &
