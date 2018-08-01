for i in "$@"; do

echo "backup $i"
cp -v ~/swaptoken/$i/TokenDroplet/config/service.json ~/swaptoken/config/$i.json

done
