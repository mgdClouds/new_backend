#!/usr/bin/env bash
echo 开始初始化数据库
rm -rf /Users/chaos/Project/Company/newcom/migrations/versions/*
echo 已删除历史版本文件
mysql -uroot -pZcwd1986 -e"
drop database if exists newcom;
CREATE DATABASE IF NOT EXISTS newcom DEFAULT CHARSET utf8 COLLATE utf8_general_ci;
"
echo 已重建数据库
cd /Users/chaos/Project/Company/newcom/
echo 进入祝目录
/Users/chaos/anaconda3/envs/newcom/bin/python3 manager.py db migrate
echo 已生成数据表脚本
/Users/chaos/anaconda3/envs/newcom/bin/python3 manager.py db upgrade
echo 已生成数据表
