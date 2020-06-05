from marshmallow import Schema, fields, EXCLUDE
from .base import BaseSchema, IdNameSchema, BasePostSchema, BasePutSchema, BaseActionSchema
from .user import PmDefaultSchema, PmAppointTimeSchema, UserDefaultSchema
from ..model import Company, PositionLevel, Position, Project, Offer, InterviewStatus, OfferStatus, ProjectStatus, \
    JobWantedAttitude, EnterProjectStatus
from .user import AppointTime


class CompanyDefaultSchema(IdNameSchema):
    contact = fields.Str()
    phone = fields.Str()
    email = fields.Str()
    address = fields.Str()
    contract_name = fields.Str()
    contract_uuid = fields.Str()

    om_name = fields.String(required=True)

    billing_cycle = fields.Integer(required=True)  # 资金方式
    service_fee_rate = fields.Float(required=True)  # 平台服务费率
    tax_rate = fields.Float(required=True)  # 综合税率
    hr_fee_rate = fields.Float(required=True)  # HR服务费率
    finance_rate = fields.Float(required=True)  # 金融费率
    activate = fields.Integer()

    work_station_fee = fields.Float()  # 工位费
    shift_type = fields.Integer()  # 加班补偿方案

    work_day_shift_rate = fields.Float()  # 工作日加班补偿系数
    weekend_shift_rate = fields.Float()  # 周末加班补偿系数
    holiday_shift_rate = fields.Float()  # 节假日加班补偿系数
    charging_num = fields.Float()  # 计费天数

    entry_file_template = fields.String()
    ware_fare = fields.Float()
    tax_free_rate = fields.Float()
    break_up_fee_rate = fields.Float()


class CompanySimpleStatisticSchema(CompanyDefaultSchema):
    open_projects_count = fields.Int()
    open_offers_count = fields.Int()
    entry_file_checking_count = fields.Int()

    class ISS(Schema):
        cv_pass = fields.Integer()
        interview_pass = fields.Integer()

    interview_statistic = fields.Nested(ISS(many=False))

    class EPSS(Schema):
        purchase_agree = fields.Integer()
        pm_agree = fields.Integer()
        file_pm_count = fields.Integer()  # 等待确认入项材料
        file_company_agree_count = fields.Integer()

    enter_project_statistic = fields.Nested(EPSS(many=False))

    class PS(Schema):
        un_checked = fields.Integer()

    payment_statistic = fields.Nested(PS(many=False))

    class ES(Schema):
        leaving_count = fields.Integer()
        leave_count = fields.Integer()
        total = fields.Integer()
        on_duty_count = fields.Integer()

    engineer_statistic = fields.Nested(ES(many=False))

    class OSS(Schema):
        total = fields.Integer()
        ing_count = fields.Integer()
        ending_count = fields.Integer()

    order_statistic = fields.Nested(OSS(many=False))


class CompanyPostSchema(BasePostSchema):
    ModelClass = Company

    name = fields.Str(required=True)
    contact = fields.String(required=True)
    phone = fields.Str(required=True)
    email = fields.Str(required=True)
    address = fields.String(required=True)

    om_name = fields.String(required=True)

    billing_cycle = fields.Integer(required=True)
    service_fee_rate = fields.Float(required=True)
    tax_rate = fields.Float(required=True)
    hr_fee_rate = fields.Float(required=True)
    finance_rate = fields.Float(required=True)
    work_station_fee = fields.Float()
    shift_type = fields.Integer()

    work_day_shift_rate = fields.Float()
    weekend_shift_rate = fields.Float()
    holiday_shift_rate = fields.Float()
    charging_num = fields.Float()
    ware_fare = fields.Float()
    tax_free_rate = fields.Float()
    break_up_fee_rate = fields.Float()


class CompanyPutSchema(BasePutSchema):
    name = fields.Str(required=False)
    contact = fields.String(required=False)
    phone = fields.Str(required=False)
    email = fields.Str(required=False)
    address = fields.String(required=False)

    om_name = fields.String(required=True)
    billing_cycle = fields.Integer(required=True)
    service_fee_rate = fields.Float(required=True)
    tax_rate = fields.Float(required=True)
    hr_fee_rate = fields.Float(required=True)
    finance_rate = fields.Float(required=True)

    work_station_fee = fields.Float()
    shift_type = fields.Integer()

    work_day_shift_rate = fields.Float()
    weekend_shift_rate = fields.Float()
    holiday_shift_rate = fields.Float()
    charging_num = fields.Float()
    ware_fare = fields.Float()
    tax_free_rate = fields.Float()
    break_up_fee_rate = fields.Float()


class PositionLevelDefaultSchema(Schema):
    id = fields.Integer()
    name = fields.String()
    money = fields.Float()
    engineer_count = fields.Integer()

    class PS(Schema):
        name = fields.String()
        salary_type = fields.Integer()

    position = fields.Nested(PS(many=False))


class OfferPositionDetailSchema(Schema):
    class PLS(PositionLevelDefaultSchema):
        expect_mmd = fields.Float()
        expect_mmm = fields.Float()
        expect_mdd = fields.Float()
        expect_mdm = fields.Float()

    position_levels = fields.List(fields.Nested(PLS(many=False)))

    class CM(Schema):
        billing_cycle = fields.Integer(required=True)  # 资金方式
        service_fee_rate = fields.Float(required=True)  # 平台服务费率
        tax_rate = fields.Float(required=True)  # 税金费率
        hr_fee_rate = fields.Float(required=True)  # HR服务费率
        finance_rate = fields.Float(required=True)  # 金融费率
        work_station_fee = fields.Float()  # 工位费
        shift_type = fields.Integer()  # 加班补偿方案
        charging_num = fields.Float()  # 计费天数
        tax_free_rate = fields.Float()  # 税优费率

    company = fields.Nested(CM(many=False))


class PositionPostSchema(BasePostSchema):
    ModelClass = Position
    name = fields.String()
    company_id = fields.Integer()


class PositionLevelPostSchema(BasePostSchema):
    ModelClass = PositionLevel
    name = fields.String()
    company_id = fields.Integer()


class PositionDefaultSchema(Schema):
    id = fields.Integer()
    name = fields.String()
    enineer_count = fields.Integer()


class ProjectDefaultSchema(Schema):
    id = fields.Integer()
    name = fields.String()
    company_id = fields.Integer()
    status = fields.Function(lambda x: ProjectStatus.int2str(x.status))


class ProjectDetailSchema(ProjectDefaultSchema):
    engineer_count = fields.Int()


class ProjectWithPmsSchema(ProjectDefaultSchema):
    pms = fields.List(fields.Nested(PmDefaultSchema(many=False)))


class ProjectPostSchema(BasePostSchema):
    ModelClass = Project

    name = fields.Str()
    company_id = fields.Integer()


class InterviewDefaultSchema(BaseSchema):
    company_id = fields.Integer()
    company = fields.String()
    project_id = fields.Integer()
    project = fields.String()
    pm_id = fields.Integer()
    pm = fields.Nested(PmAppointTimeSchema(many=False, unknown=EXCLUDE))
    engineer_id = fields.Integer()
    engineer = fields.String()
    position_id = fields.Integer()
    position = fields.String()
    note = fields.String()

    class OS(Schema):
        name = fields.String()
        id = fields.Integer()
        position = fields.String()

        class PLS(Schema):
            id = fields.Integer()
            name = fields.String()
            money = fields.Float()
            expect_mmd = fields.Float()
            expect_mmm = fields.Float()
            expect_mdd = fields.Float()
            expect_mdm = fields.Float()
            expect_ddd = fields.Float()
            expect_ddm = fields.Float()

        position_levels = fields.List(fields.Nested(PLS(many=False)))

    offer = fields.Nested(OS(many=False))
    entry_date = fields.Date()
    entry_before = fields.Date()

    class PLS(Schema):
        id = fields.Integer()
        name = fields.String()
        money = fields.Float()
        expect_mmd = fields.Float()
        expect_mmm = fields.Float()
        expect_mdd = fields.Float()
        expect_mdm = fields.Float()
        expect_ddd = fields.Float()
        expect_ddm = fields.Float()

        class PS(Schema):
            salary_type = fields.Integer()

        position = fields.Nested(PS(many=False))

    final_position_level = fields.Nested(PLS(many=False))

    status = fields.Function(lambda x: InterviewStatus.int2str(x.status))

    pm_free_time = fields.List(fields.Nested(AppointTime(many=True, unknown=EXCLUDE)), default=False)
    appoint_time = fields.Nested(AppointTime(many=False, unknown=EXCLUDE), default=False)


class InterviewClassifySchema(InterviewDefaultSchema):
    pass


class OfferDefaultSchema(Schema):
    updated = fields.DateTime()
    id = fields.Integer()
    name = fields.String()
    company_id = fields.Integer()
    company = fields.String()
    project_id = fields.Integer()
    project = fields.String()
    pm_id = fields.Integer()
    pm = fields.Nested(PmDefaultSchema(many=False))
    position_id = fields.Integer()
    position = fields.String()
    position_levels = fields.List(
        fields.Nested(PositionLevelDefaultSchema(many=False, exclude=("position", "engineer_count"))))
    amount = fields.Integer()  # 需求人数
    money = fields.Float()
    salary_type = fields.Integer()
    status = fields.Function(lambda x: '' if not hasattr(x, 'status') else OfferStatus.int2str(x.status))
    shut_down_reason = fields.String()
    description = fields.String()


class OfferModifySchema(BaseActionSchema):
    ModelClass = Offer
    _permission_roles = ['purchase', 'om', 'pm', 'company_om']
    action = 'modify'

    name = fields.String()
    amount = fields.Integer()
    description = fields.String()
    work_place = fields.String()

    position_levels = fields.List(fields.Integer())


class OfferShutDownSchema(BaseActionSchema):
    ModelClass = Offer
    _permission_roles = ['om', 'purchase', 'pm', 'company_om']
    action = 'shut_down'

    shut_down_reason = fields.String(required=True)
    shut_down_note = fields.String()


class OfferDefaultSchemaWithStatistics(OfferDefaultSchema):
    created = fields.DateTime()
    updated = fields.DateTime()
    amount = fields.Int()
    cv_push_amount = fields.Int()
    cv_pass_amount = fields.Int()
    interview_pass_amount = fields.Int()
    entry_amount = fields.Int()


class OfferStatisticSchema(OfferDefaultSchema):
    demand_amount = fields.Int()
    cv_push_amount = fields.Int()
    cv_pass_amount = fields.Int()
    interview_pass_amount = fields.Int()
    entry_amount = fields.Int()

    cv_push_rate = fields.Float()
    cv_pass_rate = fields.Float()
    interview_pass_rate = fields.Float()
    entry_rate = fields.Float()


class CompanyRelationShipSchema(CompanyDefaultSchema):
    pms = fields.List(fields.Nested(PmDefaultSchema(many=True)))
    projects = fields.List(fields.Nested(ProjectDefaultSchema(many=True)))
    position_levels = fields.List(fields.Nested(PositionLevelDefaultSchema(many=True)))


class CompanyOmSchema(UserDefaultSchema):
    company_id = fields.Int()
    company = fields.Nested(CompanyDefaultSchema(many=False))


class PmDetailSchema(PmDefaultSchema):
    company_id = fields.Integer()
    engineers_count = fields.Integer()
    projects_count = fields.Integer()
    offers_count = fields.Integer()
    projects = fields.List(fields.Nested(ProjectDefaultSchema(many=True)))


class PmProjectStatistic(Schema):
    id = fields.Integer()
    name = fields.String()
    status = fields.Function(
        lambda x: ProjectStatus.int2str(x.status) if type(x) is not dict else ProjectStatus.int2str(x['status']))
    engineer_count = fields.Integer()
    average_ability_score = fields.Float()
    average_attitude_score = fields.Float()
    total_daily_logs = fields.Float()


class PmWithProjectStatistic(Schema):
    statistic_of_project = fields.List(fields.Nested(PmProjectStatistic(many=False)))


class CvSearchSchema(BaseSchema):
    class AbilitySchema(Schema):
        name = fields.String(required=True)  # validate=lambda x: not x.index('-') or not x.index(','))
        level = fields.String(required=True)

    real_name = fields.String()
    pre_username = fields.String()
    major = fields.String()
    highest_degree = fields.String()
    gender = fields.Integer()
    email = fields.String()
    cv_name = fields.String()
    job_wanted_status = fields.Function(lambda x: JobWantedAttitude.int2str(x.job_wanted_status))
    ability = fields.List(fields.Nested(AbilitySchema(many=False)))
    pushed = fields.Bool(default=False)

