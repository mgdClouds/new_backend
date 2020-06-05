#!/usr/bin/env bash
echo 开始初始化数据库
rm -rf /home/ubuntu/project/newcom/migrations/versions/*
echo 已删除历史版本文件
#Jinchongzi321@123.103.74.232:3306/
mysql -uroot -pZcwd1986 -e"
drop database if exists newcom;
CREATE DATABASE IF NOT EXISTS newcom DEFAULT CHARSET utf8 COLLATE utf8_general_ci;
"
echo 已重建数据库
cd /home/ubuntu/project/newcom/
echo 进入祝目录
python manager.py db migrate
echo 已生成数据表脚本
python manager.py db upgrade
echo 已生成数据表
