for i in "$@"; do

echo "start $i";
cp ~/swaptoken/config/$i.json ~/swaptoken/$i/TokenDroplet/config/service.json && cd ~/swaptoken/$i/TokenDroplet  && nohup python main.py $i &


done
