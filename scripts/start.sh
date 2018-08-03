#!/bin/bash

SCRIPT_DIR=$(dirname "$0")
SCRIPT_PARENT_DIR=$(realpath "$SCRIPT_DIR/..")
PROG="$SCRIPT_PARENT_DIR/main.py"

if [ ! -e "$PROG" ]
then
    echo "$PROG does not exist"
    exit 1
fi

echo "run $PROG"

LOGFILE_DIR="$SCRIPT_PARENT_DIR/log"
mkdir -p "$LOGFILE_DIR"

for token_name in "$@"
do
    echo "start $token_name scan service";
    nohup python3 "$PROG" "$token_name" &> "$LOGFILE_DIR/${token_name}_scan.log" &
done
