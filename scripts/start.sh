PROJECT_DIR="${HOME}/TokenDroplet"

for i in "$@"; do

if [ ! -e "${PROJECT_DIR}/$i/ScanService" ]; then
    echo "${PROJECT_DIR}/$i/ScanService not exist, ignore start $i scan service"
    continue
fi

echo "start ${PROJECT_DIR}/$i/ScanService";
cd ${PROJECT_DIR}/$i/ScanService && nohup python main.py $i &

done
