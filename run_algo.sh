#!/bin/bash
echo "File = $1, Scheduling = $2 $3"
echo "Running python script..."

if [ -z "$3" ]; then
    python3 algo.py "$1" "$2"
else
    python3 algo.py "$1" "$2" "$3"
fi