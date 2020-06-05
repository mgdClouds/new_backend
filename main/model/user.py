#!/usr/bin/env python
# coding=utf-8

import re

from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import current_user, login_user, logout_user, UserMixin  # ,AnonymousUserMixin

from ..extention import db, login_manager
from ..exception import NewComException
from ._base import Base


class Roles(object):
    om = 'om'
    pm = 'pm'
    engineer = 'engineer'
    purchase = 'purchase'
    company_om = 'company_om'

    choose = ['om', 'pm', 'engineer', 'purchase', 'company_om']
    show_name = (('om', '运营'), ('pm', '项目经理'), ('engineer', '工程师'), ('purchase', '采购'), ('company_om', '管理员'))


class User(Base, UserMixin):
    # Set the name for table
    __tablename__ = 'user'

    pre_username = db.Column(db.String(16), unique=True)
    username = db.Column(db.String(16), unique=True)
    phone = db.Column(db.String(11), nullable=True, unique=True)
    email = db.Column(db.String(64), nullable=True, unique=True)
    real_name = db.Column(db.String(16), nullable=True)
    gender = db.Column(db.Integer)
    head_img = db.Column(db.String(256), nullable=True)
    password = db.Column(db.String(256), nullable=False)
    role = db.Column(db.String(16), nullable=False)
    age = db.Column(db.Integer)
    birthday = db.Column(db.Date)
    activate = db.Column(db.Integer, nullable=False, default=1)

    __mapper_args__ = {
        'polymorphic_identity': 'normal',
        'polymorphic_on': role
    }

    def __init__(self, **kwargs):
        for key in kwargs:
            setattr(self, key, kwargs[key])

    def __repr__(self):
        """Define the string format for instance of User."""
        return "{}:{}".format(self.role, self.real_name)

    def set_password(self, password):
        self.password = generate_password_hash(password)

    def verify_password(self, password):  # pragma: no cover
        return check_password_hash(self.password, password)

    @classmethod
    def logout(cls):
        if current_user and current_user.is_authenticated:
            logout_user()

    @classmethod
    def login(cls, user):
        login_user(user)

    @classmethod
    def if_user_exist(cls, username=None, phone=None):
        if User.query.filter(db.or_(User.username == username, User.phone == phone,
                                    User.username == phone, User.phone == username)).all():
            return True
        return False

    @classmethod
    def create(cls, **kwargs):
        username = kwargs.get('username', None)
        if username:
            if not re.match('[a-zA-Z][a-zA-Z0-9_-]{4,15}', username):
                raise NewComException('账户名不符合要求！', 501)
        user = cls(**kwargs)
        if 'password' in kwargs:
            user.password = kwargs['password']
            kwargs.pop('password')
        db.session.add(user)
        db.session.flush()
        db.session.commit()


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))  # should return None not raise an exception
