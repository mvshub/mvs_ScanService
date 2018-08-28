# Scan Service of CrossChain

#### Description
Scan Service of CrossChain

#### Software Architecture
Python3 & Flask

#### Installation

1. install mysqldb
```bash
sudo apt-get install mysql-server
sudo apt-get install libmysqlclient-dev
sudo apt-get install python-mysqldb
pip3 install mysqlclient

default mysql database config (see config/service.json)

"mysql_host":"127.0.0.1",
"mysql_port":3306,
"mysql_user":"root",
"mysql_passwd":"123456",
"mysql_db":"wallet",
```

2. install python3 packages
```bash
pip3 install gevent
pip3 install pycrypto

pip3 install flask
pip3 install flask-sqlalchemy
pip3 install sqlalchemy-utils
pip3 install flask-migrate
```

3. create database 'wallet'
```
create database wallet charset utf8;
```

#### Instructions

Run:
1. run manually
start _one process_ each time with a _single_ token name parameter.
```bash
# token name is a single parameter,
# accept token name should exist in file config/service.json,
# same as one of scans.services.coin fields value (ignore case)
python3 main.py <token_name>
examples:
python3 main.py etp
python3 main.py eth
python3 main.py ethtoken
```
2. run batch
cd `scripts`, and use the following ways to run `start_scan_service.py` to start _one or more processes_.
This script has function of watching the processes and restart them if it's not running.
```bash
./start_scan_service.py etp
./start_scan_service.py etp eth ethtoken
echo "etp eth ethtoken" | xargs -n1 ./start_scan_service.py
cat token_names.txt | xargs -n1 ./start_scan_service.py
# use nohup if use remote server
nohup ./start_scan_service.py etp eth ethtoken >/dev/null 2>&1 &
```

#### ETH
1. install & start
```
sudo npm install -g ganache-cli truffle
ganache-cli
```

2. truffle commands
```
cd project_dir
truffle init
truffle create contract contract_name
truffle compile

truffle migrate --reset
truffle migrate
truffle deploy

truffle console

contract_name.deployed().then(instance => contract = instance)
contract.function.call()
```
