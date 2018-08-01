for i in "$@"; do

PROJECT_DIR="~/TokenDroplet"
echo "start $i";
cp -v ${PROJECT_DIR}/config/ScanService/$i.json ${PROJECT_DIR}/$i/ScanService/config/service.json && cd ${PROJECT_DIR}/$i/ScanService && nohup python main.py &

done
