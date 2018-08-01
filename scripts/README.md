# deploy paths introduction

## Top work directory
```
~/TokenDroplet
```
In this directory,
1. For each scan token(ie. etp), there is a project sub-directory(ie. etp), and deploy service in this sub-directory.
2. It has a `config` sub-directory which is used to backup config files for all services of each token.
3. It has a `src` sub-directory which concludes the common source code to be deployed separately for each service.

# deploy steps
```
TOKENS="etp eth ethtoken"
1. ./deploylocal.sh $TOKENS
2. ./backup.sh $TOKENS
3. edit config file in `config` sub-directory
    modify "port" number to not conflict with each other
    modify "enable" of scans services to enable only one needed scan service
4. ./start $TOKENS
```

# scripts descripion

## clear database
```
./cleardb.sh $TOKENS
```

## start service
```
./start.sh $TOKENS
```

## deploy service
```
./deploy.sh $TOKENS (use rsync)
./deploylocal.sh $TOKENS
```

## backup and restore config file
```
./backup.sh $TOKENS
./restore.sh $TOKENS
```

## examples of passing parameters
```
./start.sh etp
./start.sh etp eth
echo "etp eth" | xargs -n1 ./start.sh
cat token_names.txt | xargs -n1 ./start.sh
```
