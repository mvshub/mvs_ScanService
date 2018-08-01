PROJECT_DIR="${HOME}/TokenDroplet"

for i in "$@"; do

LOCAL_PATH="${PROJECT_DIR}/$i/ScanService"
TARGET_PATH="${PROJECT_DIR}/$i"

echo "deploy $i to ${TARGET_PATH}";

REMOTE_HOST="ubuntu@dev1.xinyuanjie.org"
REMOTE_COMMAND="test -d ${TARGET_PATH} || mkdir -p ${TARGET_PATH}"
ssh -i ${HOME}/.ssh/id_rsa -p 12008 $REMOTE_HOST $REMOTE_COMMAND

EXCLUDES="--exclude '*.pyc' --exclude '*.log' --exclude 'cscope.*'"
rsync -avPr ${EXCLUDES} ${LOCAL_PATH} ${REMOTE_HOST}:${TARGET_PATH}

done

