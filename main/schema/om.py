from marshmallow import Schema, fields, EXCLUDE

from .base import BaseSchema, BasePostSchema, BasePutSchema, BaseActionSchema, BaseActionsSchema
from .engineer import DailyLogDefaultSchema, EngineerDefaultSchema, ProjectWithEngineers
from .user import AppointTime, Om
from ..model import Interview, Pm, ExtraWork, Leave, Entry, WorkReport, MonthlyBill, Resign, Payment


class OmPutSchema(BasePutSchema):
    ModelClass = Om
    _permission_roles = ['om']

    real_name = fields.Str()
    gender = fields.Integer()
    email = fields.Str()
    phone = fields.Str()


class OmDefaultSchema(BaseSchema):
    username = fields.Str()
    real_name = fields.Str()
    gender = fields.Integer()
    email = fields.Str()
    phone = fields.Str()


class PaymentsForPurchaseExcelSchema(BaseActionsSchema):
    ModelClass = Payment
    _permission_roles = ['om']
    action = 'purchase_excel'


class PaymentsForEngineerExcelSchema(BaseActionsSchema):
    ModelClass = Payment
    _permission_roles = ['om']
    action = 'engineer_excel'


class PaymentSchemaForOmEngineerDetail(BaseSchema):
    class E(Schema):
        welfare_rate = fields.Float()

    year_month = fields.Int()
    engineer = fields.Nested(E(many=False))
    company_pay = fields.Float()
    tax = fields.Float()
    fee = fields.Float()
    income = fields.Float()
