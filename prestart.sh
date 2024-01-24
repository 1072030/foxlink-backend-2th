#! /usr/bin/env bash
sleep 30;
mkdir -p logs/
python -m app.server_daemons &
