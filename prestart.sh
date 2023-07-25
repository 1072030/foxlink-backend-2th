#! /usr/bin/env bash
sleep 10;
mkdir -p logs/
python -m app.server_daemons &
