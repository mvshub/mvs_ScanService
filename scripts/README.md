# scripts descripion

## clear database
```
./cleardb.sh
```

## start service
```
./start.sh
```

## deploy service
```
./deploy.sh
```

## backup and restore config file
```
./backup.sh
./restore.sh
```

## example
```
./start.sh etp
./start.sh etp eth
echo "etp eth" | xargs -n1 ./start.sh
cat token_names.txt | xargs -n1 ./start.sh
```
