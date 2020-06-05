#!/usr/bin/env python
# coding=utf-8
from flask_apscheduler import APScheduler
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from flask_wtf.csrf import CSRFProtect

db = SQLAlchemy()

login_manager = LoginManager()

csrf = CSRFProtect()

scheduler = APScheduler()
