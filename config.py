#!/usr/bin/env python
# coding=utf-8
from os import path, environ, getcwd
from dotenv import load_dotenv

load_dotenv()


class BaseConfig(object):
    """Base config class."""
    SQLALCHEMY_TRACK_MODIFICATIONS: bool = False  # 关闭事件监控
    SECRET_KEY: str = environ.get("SECRET_KEY")
    BABEL_DEFAULT_LOCALE: str = environ.get("BABEL_DEFAULT_LOCALE")
    JWT_ALGORITHM: str = environ.get("JWT_ALGORITHM")
    DEFAULT_PWD: str = environ.get("DEFAULT_PWD")
    ROOT_DIR: str = getcwd()
    DEFAULT_ENTRY_FILE_TEMPLATE = path.join(ROOT_DIR, "scripts", "默认入项材料说明.doc")
    RETURN_MOCK: bool = False
    FILE_TEM_PATH: str = "main/files/tem"
    FILE_RESUME_PATH: str = "main/uploads/resumes"
    FILE_CONTRACT_PATH: str = "main/files/contract"
    EXCEL_PATH: str = "main/files/excel/"
    EXCEL_FOR_PURCHASE_NAME_FORMAT: str = "{}-{}年-{}月-工时结算单.xls"
    EXCEL_FOR_ENGINEER_NAME_FORMAT: str = "{}-{}年-{}月-薪资结算单.xls"
    FILE_CV_PATH: str = "main/files/cv"
    FILE_ENTER_PATH: str = "main/files/et"
    FEE_RATE_DEFAULT: float = 0.10
    TAX_RATE_DEFAULT: float = 0.05
    WELFARE_RATE_DEFAULT: float = 0
    PERSONAL_TAX_RATE_DEFAULT: float = 0.08
    OSS_KEY: str = environ.get("OSS_KEY")
    OSS_SEC: str = environ.get("OSS_SEC")

    JOBS: list = [
        {
            "id": "daily1",
            "func": "main.api.scheduler:daily1",
            "args": "",
            "trigger": {"type": "cron", "hour": "11", "minute": "53"},
        }
    ]

    SCHEDULER_API_ENABLED: bool = True


class ProdConfig(BaseConfig):
    DEBUG: bool = False
    """Production config  ."""
    SQLALCHEMY_DATABASE_URI: str = environ.get("SQLALCHEMY_DATABASE_URI")
    DOMAIN: str = environ.get("DOMAIN")
    DAILY_LOCK = "/newcom_scheduer.lock"
    AliOss_Bucket = "newcom"


class DevConfig(BaseConfig):
    """Development config class."""
    # Open the DEBUG
    DEBUG: bool = True
    DOMAIN: str = "127.0.0.1:5000"
    SQLALCHEMY_DATABASE_URI: str = "mysql+pymysql://root:123456@127.0.0.1:3306/newcom"
    DAILY_LOCK: str = BaseConfig.ROOT_DIR + "newcom_scheduer.lock"
    AliOss_Bucket: str = "newcom-local"
    # SQLALCHEMY_ECHO: bool = True


class TestConfig(BaseConfig):
    """Development config class."""
    # Open the DEBUG
    DEBUG: bool = True
    DOMAIN: str = environ.get("TEST_DOMAIN")
    SQLALCHEMY_DATABASE_URI: str = environ.get("TEST_SQLALCHEMY_DATABASE_URI")
    DAILY_LOCK: str = "/tmp/newcom_scheduer.lock"
    AliOss_Bucket: str = "newcom--dev"


def load_config():
    """加载配置类"""
    mode = environ.get("MODE")
    try:
        if mode == "PRODUCTION":
            return ProdConfig
        elif mode == "TESTING":
            return TestConfig
        else:
            return DevConfig
    except (ImportError, Exception):
        return BaseConfig
