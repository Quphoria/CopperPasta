#!/bin/bash

cd /pasta/api

# clean database every hour
watch -n 3600 -t python3 clean_db.py &

# start nginx
nginx &

# run server
gunicorn --workers 3 --bind 0.0.0.0:5000 -m 007 wsgi:app
