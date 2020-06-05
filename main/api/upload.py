#!/usr/bin/env python
# coding=utf-8

from uuid import uuid1
from urllib.parse import quote
import time

import os
from flask_login import current_user
from flask import request, make_response
from werkzeug.utils import secure_filename

from ..model import Roles, Company
from ..exception import NewComException
from ..util.try_catch import api_response
from ..util.word2pdf import turn_word_to_pdf
from config import load_config

Config = load_config()


def upload_file(input_name):
    """
    把上传后的文件名保存到临时目录，并返回临时文件名
    :return: 临时文件名
    """

    f = request.files[input_name]
    tail_name = f.filename.split(".")[-1].lower()
    tem_path = os.path.join(Config.ROOT_DIR, Config.FILE_TEM_PATH)
    if not secure_filename(f.filename) or not tail_name in ["pdf", "doc", "docx"]:
        raise NewComException("bad file type", 500)
    if tail_name in ["doc", "docx"]:
        filename = f.filename.replace(",", "，")
        tem_word_path = os.path.join(tem_path, "{}.{}".format(str(uuid1()), filename))
        fn = ".".join(tem_word_path.split(".")[0:-1])
        tem_pdf_path = os.path.join(tem_path, "{}.{}".format(fn, "pdf"))
        f.save(tem_word_path)
        turn_word_to_pdf(tem_word_path, tem_pdf_path)
        while True:
            time.sleep(0.1)
            if os.path.exists(tem_pdf_path):
                break
        return tem_pdf_path.split("/")[-1], tem_pdf_path
    else:
        tem_filename = "%s.%s" % (str(uuid1()), f.filename)
        path = os.path.join(tem_path, tem_filename)
        # todo 此处可对接第三方平台存储
        f.save(path)
        return tem_filename, path


def simple_upload(input_name):
    mode = request.headers['MODE']

    f = request.files[input_name]
    tail_name = f.filename.split(".")[-1].lower()
    
    if mode == 'resume':
      tem_path = os.path.join(Config.ROOT_DIR, Config.FILE_RESUME_PATH)
    else:
      tem_path = os.path.join(Config.ROOT_DIR, Config.FILE_TEM_PATH)
    
    if not secure_filename(f.filename) or not tail_name in ["pdf", "doc", "docx"]:
        raise NewComException("bad file type", 500)
    if tail_name in ["doc", "docx"]:
        filename = f.filename.replace(",", "，")
        tem_word_path = os.path.join(tem_path, "{}.{}".format(str(uuid1()), filename))
        f.save(tem_word_path)
        return tem_word_path.split("/")[-1], tem_word_path
    else:
        tem_filename = "%s.%s" % (str(uuid1()), f.filename)
        path = os.path.join(tem_path, tem_filename)
        f.save(path)
        return tem_filename, path


@api_response
def upload_contract():
    if not current_user.role in (Roles.om, Roles.company_om):
        raise NewComException("非法身份", 402)
    return upload_file("contract")[0]


@api_response
def upload_cv():
    if current_user.role not in (Roles.om, Roles.engineer, Roles.company_om):
        raise NewComException("非法身份", 402)
    tem_filename, path = upload_file("cv")
    return tem_filename


@api_response
def download_contract():
    """
    下载也要有权限控制，所以，不能放静态文件夹，要通过本函数获取
    :return:
    """
    if not current_user.role == Roles.om:
        raise NewComException("非法身份", 401)
    company_id = int(request.args.get("company_id"))
    contract_dir = os.path.join(Config.ROOT_DIR, Config.FILE_CONTRACT_PATH)
    company_model = Company.query.filter_by(id=company_id).first()
    contract_path = os.path.join(contract_dir, company_model.contract_uuid)
    with open(contract_path, "rb") as f:
        response = make_response(f.read())
    mime_type = "application/pdf"
    response.headers["Content-Type"] = mime_type
    file_name = quote(company_model.contract_name)  # .encode('utf-8'))
    response.headers["Content-Disposition"] = "attachment; filename*=utf-8''{}".format(
        file_name
    )
    return response


@api_response
def get_cv(engineer_id, page):
    """
    下载也要有权限控制，所以，不能放静态文件夹，要通过本函数获取
    :return:
    """
    cv_root_dir = os.path.join(Config.ROOT_DIR, Config.FILE_CV_PATH)
    cv_path = os.path.join(cv_root_dir, str(engineer_id))
    img_path = os.path.join(cv_path, "page_{}.jpg".format(page))
    with open(img_path, "rb") as f:
        response = make_response(f.read())
    mime_type = "image/png"
    response.headers["Content-Type"] = mime_type
    # response.headers['Content-Length'] = ''
    file_name = "cv_{}_{}.jpg".format(engineer_id, page)  # .encode('utf-8'))
    response.headers["Content-Disposition"] = "attachment; filename*=utf-8''{}".format(
        file_name
    )
    return response


def _payments_excel(reader_type):
    if reader_type == "engineer":
        name_format = Config.EXCEL_FOR_ENGINEER_NAME_FORMAT
    if reader_type == "purchase":
        name_format = Config.EXCEL_FOR_PURCHASE_NAME_FORMAT
    company_id = int(request.args.get("company_id"))
    year_month = int(request.args.get("year_month"))
    company_name = Company.query.get(company_id).name
    path = os.path.join(Config.ROOT_DIR, Config.EXCEL_PATH)
    path = os.path.join(
        path, name_format.format(company_id, int(year_month / 100), year_month % 100)
    )

    with open(path, "rb") as f:
        response = make_response(f.read())
    mime_type = "application/excel"
    response.headers["Content-Type"] = mime_type

    file_name = name_format.format(
        company_name, int(year_month / 100), year_month % 100
    )
    response.headers["Content-Disposition"] = "attachment; filename*=utf-8''{}".format(
        quote(file_name)
    )
    return response


@api_response
def get_purchase_payments_excel():
    return _payments_excel("purchase")


@api_response
def get_engineer_payments_excel():
    return _payments_excel("engineer")


def upload_head_img():
    pass


def init_upload_url(app, url_prefix):
    app.add_url_rule(
        os.path.join(url_prefix, "contract"),
        endpoint="upload.contract",
        view_func=upload_contract,
        methods=["POST"],
    )

    app.add_url_rule(
        os.path.join(url_prefix, "contract"),
        endpoint="download.contract",
        view_func=download_contract,
        methods=["get"],
    )

    app.add_url_rule(
        os.path.join(url_prefix, "cv"),
        endpoint="upload.cv",
        view_func=upload_cv,
        methods=["POST"],
    )

    app.add_url_rule(
        os.path.join(url_prefix, "cv_<engineer_id>_<page>.png"),
        endpoint="engineer.cv",
        view_func=get_cv,
        methods=["get"],
    )

    app.add_url_rule(
        os.path.join(url_prefix, "payments_excel_for_purchase.xls"),
        endpoint="om.payments_excel_for_purchase",
        view_func=get_purchase_payments_excel,
        methods=["get"],
    )

    app.add_url_rule(
        os.path.join(url_prefix, "payments_excel_for_engineers.xls"),
        endpoint="om.payments_excel_for_engineer",
        view_func=get_engineer_payments_excel,
        methods=["get"],
    )
