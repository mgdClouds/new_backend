#!/usr/bin/env python
# coding=utf-8
from flask import Flask
from flask.logging import default_handler
from logging.handlers import TimedRotatingFileHandler

from config import load_config
from .extention import csrf, scheduler
from .jinja_filter import init_app as jinja_filter_init_app
from flask_babelex import Babel
from flasgger import Swagger
from flask_cors import CORS
from flask_apscheduler import APScheduler

from .model import *
from .api import init_api


def init_logging(app):
    app.logger.removeHandler(default_handler)
    handler = TimedRotatingFileHandler("log/log_of", "D", 1, 0)
    app.logger.addHandler(handler)
    # logging.getLogger('sqlalchemy.engine').setLevel(logging.INFO)
    # logging.basicConfig(level=logging.INFO)
    return app


def init_routes(app):
    init_api(app)
    """
    将api接口的csrf保护关闭
    app.view_functions能读取出所有的视图函数
    app.view_functions.keys()读取出去的是所有的视图函数名称
    app.view_functions.values()读取出的是所有的视图函数
    __module__读取模块名称，检测在main.api中的视图函数，关闭跨域保护
    """
    for v in app.view_functions.values():
        if v.__module__.split(".")[1] == "api":
            csrf.exempt(v)
    """
    由于flask-sqlalchemy3.0将删除SQLALCHEMY_COMMIT_ON_TEARDOWN(见官网)，
    故此处在不改动原代码基础上封装commit，未验证是否可解决官方删除原因。
    """

    @app.after_request
    def autocmt(response=None):
        if response.status_code == 200:
            db.session.commit()
        return response

    @app.teardown_request
    def autormv(exc=None):
        db.session.remove()
        return exc


def init_ext(app):
    db.init_app(app)
    csrf.init_app(app)
    login_manager.init_app(app)
    jinja_filter_init_app(app)
    babel = Babel(app)
    swagger = Swagger(app)
    scheduler.init_app(app)
    scheduler.start()


def create_app(name=__name__):
    app = Flask(__name__)
    config = load_config()
    app.config.from_object(config)
    init_logging(app)
    init_ext(app)
    init_routes(app)
    CORS(app, resources=r"/api/*")
    return app


if __name__ == "__main__":
    # Entry the application
    app = create_app()
    app.run(host="0.0.0.0")
