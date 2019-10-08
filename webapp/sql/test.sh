#!/bin/bash
set -xe
set -o pipefail

cat << EOF | mysql --no-warn -uroot -p${MYSQL_ROOT_PASSWORD} -h${MYSQL_HOST:-127.0.0.1}
DROP DATABASE IF EXISTS \`test_isucari\`;
CREATE DATABASE \`test_isucari\`;

DROP USER IF EXISTS 'isucari'@'localhost';
CREATE USER 'isucari'@'localhost' IDENTIFIED BY 'isucari';
GRANT ALL PRIVILEGES ON \`test_isucari\`.* TO 'isucari'@'localhost';

DROP USER IF EXISTS 'isucari'@'%';
CREATE USER 'isucari'@'%' IDENTIFIED BY 'isucari';
GRANT ALL PRIVILEGES ON \`test_isucari\`.* TO 'isucari'@'%';
EOF

CURRENT_DIR=$(cd $(dirname $0);pwd)
export MYSQL_HOST=${MYSQL_HOST:-127.0.0.1}
export MYSQL_PORT=${MYSQL_PORT:-3306}
export MYSQL_USER=${MYSQL_USER:-isucari}
export MYSQL_DBNAME=${MYSQL_DBNAME:-isucari}
export MYSQL_PWD=${MYSQL_PASS:-isucari}
export LANG="C.UTF-8"
cd $CURRENT_DIR

cat 01_schema.sql 02_categories.sql | grep -v 'use ' | mysql -u root -ppasswd -h 127.0.0.1  test_isucari --no-warn
