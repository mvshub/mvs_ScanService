PROJECT_DIR="${HOME}/TokenDroplet"

for i in "$@"; do

echo "backup $i"
if [ ! -e "${PROJECT_DIR}/$i/ScanService/config/service.json" ]; then
    echo "${PROJECT_DIR}/$i/ScanService/config/service.json does not exist!"
    continue
fi

mkdir -p ${PROJECT_DIR}/config/ScanService
cp -v ${PROJECT_DIR}/$i/ScanService/config/service.json ${PROJECT_DIR}/config/ScanService/$i.json

done
