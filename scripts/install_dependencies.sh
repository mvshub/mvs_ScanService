#!/bin/bash

sudo apt-get install mysql-server
sudo apt-get install libmysqlclient-dev
sudo apt-get install python-mysqldb
sudo apt-get install python3-pip

pip3 install --upgrade pip

pip3 install mysqlclient

pip3 install gevent
pip3 install pycrypto

pip3 install flask
pip3 install flask-sqlalchemy
pip3 install sqlalchemy-utils
pip3 install flask-migrate
