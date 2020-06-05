import os
from datetime import datetime, timedelta

from flask import jsonify, request
from flask_login import current_user
from flasgger import SwaggerView
import jwt
from sqlalchemy import and_
from enum import Enum
from config import load_config
from ..model import User, Roles, CompanyOm, EnterProject, EnterProjectStatus
from ..util.try_catch import api_response
from ..exception import NewComException


Config = load_config()


class PortRole(list, Enum):
    om = ["om"]
    cm = ["company_om"]
    m = ["pm", "engineer"]


class HelloToken(SwaggerView):
    description = "验证token有效性"
    tags = ["鉴权"]

    def get(self):
        return "hello {}!".format(current_user.username)


class GetToken(SwaggerView):
    tags = ["鉴权"]
    parameters = [
        {
            "name": "username",
            "in": "body",
            "type": "string",
            "required": True,
            "description": "用户名",
        },
        {"name": "password", "in": "body", "type": "string", "required": True,},
    ]

    responses = {200: {"description": "token", "examples": {"token": "j.w.t",}}}

    @api_response
    def post(self):
        """
        获得token
        """
        username = request.json.get("username")
        password = request.json.get("password")
        port = request.json.get("port")
        user = User.query.filter_by(pre_username=username).first()
        if not username or not password:
            raise NewComException("用户名或密码错误", 402)
        if not user:
            user = User.query.filter_by(username=username).first()
            if not user:
                user = User.query.filter_by(phone=username).first()
                if not user:
                    raise NewComException("错误的用户名或密码.", 402)

        if not user.verify_password(password):
            raise NewComException("用户名或密码错误", 402)
        if not user.activate:
            raise NewComException("当前用户状态为禁用！", 401)
        if user.role not in PortRole[port]:
            raise NewComException("用户没有登录此页面的权限！", 402)
        payload = {
            "uid": user.id,
            "role": user.role,
            "exp": datetime.utcnow() + timedelta(weeks=2),
        }
        token = jwt.encode(payload, Config.SECRET_KEY, Config.JWT_ALGORITHM)
        if user.role == "engineer":
            ep = EnterProject.query.filter(
                EnterProject.engineer_id == user.id, EnterProject.ing != 0
            ).all()
            if ep is None:
                raise NewComException("当前用户尚未入项！", 401)
            status = EnterProjectStatus.int2str(ep[0].status)
            return jsonify(
                {
                    "token": token.decode(),
                    "uid": user.id,
                    "role": user.role,
                    "enter_project_status": status,
                }
            )
        return jsonify({"token": token.decode(), "uid": user.id, "role": user.role})


@api_response
def change_password():
    current_user_model = User.query.get(current_user.id)
    new_password = request.json.get("new_password", 0)
    if not new_password:
        raise NewComException("请输入新密码", 500)
    user_id = int(request.args.get("user_id", 0))
    company_id = int(request.args.get("company_id", 0))

    # 如果没有传递user_id 和 company_id， 则说明在修改自身密码
    if user_id == 0 and company_id == 0:
        involve_user = User.query.get(current_user.id)
        involve_user.set_password(new_password)
        involve_user.save()

    # 如果传递了company_id 说明是运营在修改甲方管理员的密码
    elif current_user_model.role == Roles.om:
        if company_id:
            if not current_user_model.role == Roles.om:
                raise NewComException("无此权限", 501)
            com = CompanyOm.query.filter_by(company_id=company_id).first()
            involve_user = User.query.get(com.id)
        else:
            if not user_id:
                raise NewComException("请指定要修改的用户", 500)
            involve_user = User.query.get(user_id)
        involve_user.set_password(new_password)
        involve_user.save()

    # 采购和甲方管理员可以修改本公司人员的密码
    elif current_user_model.role in (Roles.company_om, Roles.purchase):
        if not user_id:
            raise NewComException("请指定要修改的用户", 500)
        involve_user = User.query.get(user_id)
        if not hasattr(involve_user, "company_id"):
            raise NewComException("非本公司用户", 501)
        if not involve_user.company_id == current_user_model.company_id:
            raise NewComException("非本公司用户", 501)
        involve_user = User.query.get(user_id)
        involve_user.set_password(new_password)
        involve_user.save()
    return jsonify({})


def init_api(app, url_prefix):
    # `获取token
    app.add_url_rule(
        "/api/v1/auth/token", view_func=GetToken.as_view("token_post"), methods=["POST"]
    )

    app.add_url_rule(
        "/api/v1/auth/change_password",
        endpoint="auth.change_password",
        view_func=change_password,
        methods=["PUT"],
    )
