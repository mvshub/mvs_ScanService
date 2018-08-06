#!/bin/bash

SCRIPT_DIR=$(dirname "$0")
cd "$SCRIPT_DIR/.."

PROG="main.py"

if [ ! -e "$PROG" ]
then
    echo "$PWD/$PROG does not exist"
    exit 1
fi

echo "run $PWD/$PROG"

LOGFILE_DIR="log"
mkdir -p "$LOGFILE_DIR"

while true
do
    echo "-------------`date`---------------"
    for token_name in "$@"
    do
        echo "check if $token_name scan service is started"
        FOUND_RESULT=$(ps -ef | grep "python3 $PROG $token_name" | grep -v grep)
        if [ -z "$FOUND_RESULT" ]; then
            echo "no, start $token_name scan service";
            nohup python3 "$PROG" "$token_name" &> "$LOGFILE_DIR/${token_name}_scan.log" &
            sleep 2
        else
            echo "yes, $token_name scan service is already started"
        fi
    done
    echo "sleep 60 seconds"
    echo ""
    sleep 60
done
