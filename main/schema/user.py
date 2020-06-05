from marshmallow import Schema, fields, EXCLUDE
from .base import UserDefaultSchema, BasePostSchema, BasePutSchema, BaseUserPut, re_phone, re_email
from ..model import *


class AppointTime(Schema):
    am = fields.Bool()
    pmA = fields.Bool()
    pmB = fields.Bool()
    disable = fields.Bool()
    need_init = fields.Bool()
    date = fields.Str()


class PasswordSchema(Schema):
    old_password = fields.String()
    new_password = fields.String()


class PmDefaultSchema(UserDefaultSchema):
    company_id = fields.Integer()


class PmWithProjectsStatistics(UserDefaultSchema):
    class PmProjectSchema(Schema):
        id = fields.Integer()
        status = fields.Function(lambda x: ProjectStatus.int2str(x.status))
        engineer_count = fields.Integer()
        average_ability_score = fields.Float()
        average_attitude_score = fields.Float()
        total_daily_logs = fields.Float()

    statistic_of_project = fields.List(fields.Nested(PmProjectSchema(many=False)))


class PmAppointTimeSchema(PmDefaultSchema):
    use_default_free_time = fields.Bool()
    default_can_appoint_time = fields.List(fields.Nested(AppointTime(many=True, unknown=EXCLUDE)))
    need_set_appoint_time = fields.Bool()


class PmPostSchema(BasePostSchema):
    ModelClass = Pm

    company_id = fields.Int(required=True)
    real_name = fields.Str(required=True)
    pre_username = fields.Str()
    gender = fields.Integer(required=True)
    phone = fields.Str(required=True, validate=re_phone)
    email = fields.Str(required=True, validate=re_email)


class PmPutSchema(BaseUserPut):
    ModelClass = Pm
    _permission_roles = ['om', 'company_om']


class PurchasePutSchema(BaseUserPut):
    ModelClass = Purchase
    _permission_roles = ['om', 'company_om', 'purchase']


class CompanyOmPutSchema(BaseUserPut):
    ModelClass = CompanyOm
    _permission_roles = ['om', 'company_om']


class PurchaseDefaultSchema(UserDefaultSchema):
    class INS(Schema):
        id = fields.Integer()
        name = fields.String()

    company = fields.Nested(INS(many=False))


class PurchaseDetailSchema(PurchaseDefaultSchema):
    ing_offers_count = fields.Str()
    finished_offer_count = fields.Str()
    ing_offers_complete_rate = fields.Str()


class PurchasePostSchema(BasePostSchema):
    ModelClass = Purchase

    company_id = fields.Int()
    real_name = fields.Str()
    pre_username = fields.Str()
    gender = fields.Integer()
    phone = fields.Str(validate=re_phone)
    email = fields.Str(validate=re_email)


class ModifySelfSchema(BasePutSchema):
    _permission_roles = [Roles.om, Roles.purchase, Roles.pm, Roles.engineer]
    ModelClass = User

    def modify_model(self, model, kwargs):
        if not model.id == current_user.id:
            raise NewComException('bad user id', 500)
        super(ModifySelfSchema, self).modify_model(model, kwargs)

    real_name = fields.String()
    gender = fields.Integer()
    phone = fields.String(validate=re_phone)
    email = fields.Str(validate=re_email)
