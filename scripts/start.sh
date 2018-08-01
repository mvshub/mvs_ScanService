PROJECT_DIR="~/TokenDroplet"

for i in "$@"; do

echo "start $i";
if [ ! -e "${PROJECT_DIR}/config/ScanService/$i.json" ]; then
    echo "${PROJECT_DIR}/config/ScanService/$i.json does not exist!"
    continue
fi

if [ ! -e "${PROJECT_DIR}/$i/ScanService/config" ]; then
    echo "${PROJECT_DIR}/$i/ScanService/config directory does not exist!"
    continue
fi

cp -v ${PROJECT_DIR}/config/ScanService/$i.json ${PROJECT_DIR}/$i/ScanService/config/service.json && cd ${PROJECT_DIR}/$i/ScanService && nohup python main.py &

done
