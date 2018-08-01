for i in "$@"; do

echo "restore $i";
cp -v ~/swaptoken/config/$i.json ~/swaptoken/$i/TokenDroplet/config/service.json

done
