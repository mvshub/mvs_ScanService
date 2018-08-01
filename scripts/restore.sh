for i in "$@"; do

PROJECT_DIR="~/TokenDroplet"
echo "restore $i";
cp -v ${PROJECT_DIR}/config/ScanService/$i.json ${PROJECT_DIR}/$i/ScanService/config/service.json

done
