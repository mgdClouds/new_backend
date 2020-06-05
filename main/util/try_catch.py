#!/usr/bin/env python
# coding=utf-8
import traceback
import re
from functools import wraps
import random

from flask import jsonify, current_app
from marshmallow.exceptions import MarshmallowError
from sqlalchemy.exc import IntegrityError
from ..exception import NewComException
from config import load_config


CHARS = "abcdefghijklmnopqrstuvwxyz0123456789"
Config = load_config()


def gen_wrong_code():
    result = ""
    for i in range(4):
        result += CHARS[random.randint(0, 35)]
    return result


def gen_error(msg, code, locate_code=None):
    result = {"user_msg": msg}
    result["debug_info"] = traceback.format_exc()
    if not locate_code:
        locate_code = gen_wrong_code()
    current_app.logger.error("错误定位码：{}\n{}".format(locate_code, result))
    return jsonify(result), code


def api_response(func):
    @wraps(func)
    def decorated_view(*args, **kwargs):
        try:
            return func(*args, **kwargs)

        except NewComException as e:
            return gen_error(e.description, e.status_code)
        except MarshmallowError as e:
            error_msg = str(e)
            return gen_error("提交数据有误", 501)
        except IntegrityError as e:
            error_msg = str(e)
            current_app.logger.error(error_msg)
            result = re.search(
                '"Duplicate.entry.(?P<value>.+?).for key.(?P<key>.+?)"', error_msg
            )
            if result is not None:
                return gen_error(
                    "您输入的值：'{}'和已有记录冲突。请重新选择输入。".format(result["value"]), 501
                )
            return gen_error("您输入的某项信息和已有记录冲突，请重新选择" + error_msg, 501)
        except Exception as e:
            lc = gen_wrong_code()
            return gen_error("系统错误，定位码：{}, 请联系管理员".format(lc), 501, locate_code=lc)

    return decorated_view


# (pymysql.err.IntegrdityError) (1062, "Duplicate entry '签证' for key 'name'") [SQL: 'INSERT INTO company (created, name, contact, phone, email, address, contract_uuid, contract_name) VALUES (%(created)s, %(name)s, %(contact)s, %(phone)s, %(email)s, %(address)s, %(contract_uuid)s, %(contract_name)s)'] [parameters: {'created': datetime.datetime(2019, 4, 11, 16, 43, 23, 574230), 'name': '签证', 'contact': 'asdfa', 'phone': '13772016090', 'email': 'asdf@111.com', 'address': 'asdfad asdf ', 'contract_uuid': 'eb8ef6f6-5c78-11e9-bcee-525400259acb', 'contract_name': '张超，学习心得.pdf'}] (Background on this error at: http://sqlalche.me/e/gkpj)
