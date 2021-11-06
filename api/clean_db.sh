#!/bin/bash

# Go to script directory
cd "$(dirname "$0")"
source env/bin/activate

# Set LD_LIBRARY_PATH as we need to use newer sqlite3 version
export LD_LIBRARY_PATH=/usr/local/lib

python clean_db.py > /tmp/pasta-clean-db.log
