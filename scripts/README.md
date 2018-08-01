# deploy paths introduction

## Top work directory
```
~/TokenDroplet
```
In this directory,
1. For each scan token(ie. etp), there is a project sub-directory(ie. etp), and deploy service in this sub-directory.
2. It has a `config` sub-directory which is used to backup config files for all services of each token.
3. It has a `src` sub-directory which concludes the common source code to be deployed separately for each service.

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
./deploy.sh (use rsync)
./deploylocal.sh
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
