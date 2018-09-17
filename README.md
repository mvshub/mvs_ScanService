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
python3 main.py ethtoken
```
2. run batch
use the following ways to run `./scripts/start_scan_service.py` to start _one or more processes_.
This script has function of watching the processes and restart them if it's not running.
```bash
./scripts/start_scan_service.py etp
./scripts/start_scan_service.py etp ethtoken
echo "eth ethtoken" | xargs -n1 ./scripts/start_scan_service.py
cat token_names.txt | xargs -n1 ./scripts/start_scan_service.py
# use nohup if use remote server
nohup ./scripts/start_scan_service.py etp eth ethtoken >/dev/null 2>&1 &
```

#### Config file
1. service.json
```
mysql数据库：
mysql_host: 地址
mysql_port: 监听端口
mysql_user: 用户
mysql_passwd: 密码
mysql_db:  数据库名称

rpcs 服务:
id：唯一标志，不能重复
name：ETP， ETH，ETHToken
type：ETP为rpcs.etp.Etp， ETH代币 为 rpcs.eth_token.EthToken，ETH为 rpcs.eth.Eth
uri:全节点url
contract_mapaddress：ETPMap 合约地址，用于链接eth地址到etp did或者address
tx_verify_uri：第三方交易检验url

scans 扫描置换模块：
interval：扫描数据库间隔
services 交易模块:
rpc: rpc id,
coin: 货币类型，ETH,ETP,ETHToken
minconf: 最小块高确认,
scan_address：扫描交易地址
scan_initial_height:扫描初始块高
enable:是否启用


tokens 监视代币模块：
name:代币symbol，不能重复
contract_address:代币创建合约地址
enable:是否激活
decimal: 小数位数
```
2. token_mapping.json
配置以太坊ERC20，MST 关联资产
示例：
"EDU" : "ERC20.EDU"
ERC20 EDU代币 置换 MST ERC20.EDU资产

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
