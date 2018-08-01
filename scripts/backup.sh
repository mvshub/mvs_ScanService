for i in "$@"; do

PROJECT_DIR="~/TokenDroplet"
echo "backup $i"
cp -v ${PROJECT_DIR}/$i/ScanService/config/service.json ${PROJECT_DIR}/config/ScanService/$i.json

done
