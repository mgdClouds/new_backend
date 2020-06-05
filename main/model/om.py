from ._base import db, Base
from .user import User
from marshmallow import Schema, fields, EXCLUDE
from ..schema.base import BasePutSchema


class Om(User):
    __tablename__ = 'om'
    __mapper_args__ = {
        'polymorphic_identity': 'om',
    }


class OmPutSchema(BasePutSchema):
    ModelClass = Om
    _permission_roles = ['om']

    username = fields.Str()
    pre_username = fields.Str()
    real_name = fields.Str()
    gender = fields.Integer()
    email = fields.Str()
    phone = fields.Str()
