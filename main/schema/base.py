import re

from marshmallow import Schema, fields, post_load
from flask_login import current_user

from ..model import *
from ..exception import NewComException


class BaseSchema(Schema):
    id = fields.Int()
    created = fields.DateTime()


class IdNameSchema(BaseSchema):
    name = fields.String()


class BasePostSchema(Schema):
    _permission_roles = ["om"]
    ModelClass = None

    def auth_require(self):
        if current_user.role not in self._permission_roles:
            raise Exception("bad role")

    @post_load
    def create_model(self, data):
        self.auth_require()
        return self.ModelClass(**data)


class BasePutSchema(Schema):
    _permission_roles = ["om"]
    ModelClass = None

    def auth_require(self):
        role = current_user.role
        _ = self._permission_roles
        if current_user.role not in self._permission_roles:
            raise Exception("bad role")

    def modify_model(self, model, kwargs):
        self.auth_require()
        kwargs = self.load(kwargs)
        model.update(**kwargs)


class BaseActionSchema(Schema):
    _permission_roles = ["om"]
    ModelClass = None
    action = None

    def auth_require(self):
        if current_user.role not in self._permission_roles:
            raise Exception("bad role")

    def act(self, model, kwargs):
        if not isinstance(model, self.ModelClass):
            raise NewComException("错误的schema", 500)
        self.auth_require()
        kwargs = self.load(kwargs)
        return getattr(model, "action_" + self.action)(**kwargs)


class BaseActionsSchema(BaseActionSchema):
    def act(self, models, kwargs):
        for model in models:
            if not isinstance(model, self.ModelClass):
                raise NewComException("错误的schema", 500)
        self.auth_require()
        kwargs = self.load(kwargs)
        return getattr(self.ModelClass, "actions_" + self.action)(models, **kwargs)


class BaseUserPost(BasePostSchema):
    username = fields.Str()
    pre_username = fields.Str()
    real_name = fields.Str(required=True)
    gender = fields.Integer(required=True)
    email = fields.Str(required=True)
    phone = fields.Str(required=True)


class BaseUserPut(BasePutSchema):
    ModelClass = User
    _permission_roles = ["om", "purchase", "company_om"]

    username = fields.Str()
    pre_username = fields.Str()
    real_name = fields.Str()
    gender = fields.Integer()
    email = fields.Str()
    phone = fields.Str()
    activate = fields.Integer()

    def modify_model(self, model, kwargs):
        self.auth_require()
        kwargs = self.load(kwargs)
        phone, email = kwargs.get("phone"), kwargs.get("email")
        erro = []
        if phone and phone != model.phone:
            user_by_phone = User.query.filter_by(phone=phone).first()
            if user_by_phone:
                erro.append("手机号已注册，请更换！")
        if email and email != model.email:
            user_by_email = User.query.filter_by(email=email).first()
            if user_by_email:
                erro.append("邮箱号已注册，请更换！")
        if len(erro) == 2:
            raise NewComException("手机号、邮箱号已被注册，请更换重试", 422)
        elif len(erro) == 1:
            raise NewComException(erro[0], 422)
        model.update(**kwargs)


class PageInfoSchema(Schema):
    total = fields.Integer()
    total_pages = fields.Integer()
    has_prev = fields.Bool()
    prev_page = fields.Integer()
    has_next = fields.Bool()
    next_page = fields.Integer()
    first_page = fields.Integer()
    last_page = fields.Integer()
    page_count = fields.Integer()
    current_page = fields.Integer()
    per_page = fields.Integer()
    pages = fields.List(fields.Integer())


class UserDefaultSchema(BaseSchema):
    username = fields.Str()
    pre_username = fields.Str()
    real_name = fields.Str()
    gender = fields.Integer()
    head_img = fields.Str()
    email = fields.Str()
    phone = fields.Str()
    role = fields.Str()
    activate = fields.Int()


def re_email(x):
    return not not re.match(
        r"^\w+([-+.]\w+)*@\w+([-.]\w+)*\.\w+([-.]\w+)*$", x
    )


def re_phone(x):
    return not not re.match(r"^1\d{10}$", x)
