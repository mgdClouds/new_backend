#!/usr/bin/env python
# coding=utf-8

from marshmallow import Schema, fields, EXCLUDE
from .base import BasePostSchema, BaseActionSchema, BasePutSchema, UserDefaultSchema, BaseUserPost, BaseSchema, \
    BaseUserPut
from ..model import DailyLog, Leave, LeaveType, Education, Engineer, MonthlyBill, WorkReport, EngineerStatus, \
    JobWantedAttitude, ProjectStatus, PaymentStatus
from .company import ProjectDefaultSchema, OfferDefaultSchema, InterviewDefaultSchema


class CareerDefaultSchema(Schema):
    company = fields.String()
    start = fields.Date()
    end = fields.Date()
    project_id = fields.Integer()
    project = fields.Nested(ProjectDefaultSchema(many=False))
    interview = fields.Nested(InterviewDefaultSchema(many=False))
    use_hr_service = fields.Integer()
    salary_type = fields.Integer()
    employ_type = fields.Integer()

    # todo 加上orders

    class PLS(Schema):
        position = fields.String()
        id = fields.Integer()
        name = fields.String()
        money = fields.String()

    position_level = fields.Nested(PLS(many=False))


class EducationDefaultSchema(Schema):
    id = fields.Integer()
    school = fields.String(required=True)
    major = fields.String(required=True)
    degree = fields.String(required=True)
    start_date = fields.Date()
    end_date = fields.Date()
    is_highest = fields.Integer()


class EngineerDefaultSchema(UserDefaultSchema):
    company_id = fields.Int()
    pm_id = fields.Int()
    project_id = fields.Int()

    cv_name = fields.String()
    cv_path = fields.List(fields.String())
    job_wanted_status = fields.Function(lambda x: JobWantedAttitude.int2str(x.job_wanted_status))
    status = fields.Function(lambda x: EngineerStatus.int2str(x.status))
    ability_score = fields.Float()
    attitude_score = fields.Float()
    total_score = fields.Float()
    motivation = fields.Integer()
    rank = fields.Integer()
    now_career_id = fields.Integer()
    highest_degree = fields.String()
    highest_education = fields.Nested(EducationDefaultSchema(many=False))
    major = fields.String()
    pm = fields.String()

    pay_welfare = fields.Integer()
    welfare_rate = fields.Float()
    bank_code = fields.String()
    contract_confirm = fields.Integer()

    now_career = fields.Nested(CareerDefaultSchema(many=False))


class EngineerCvListSchema(BaseSchema):
    class AbilitySchema(Schema):
        name = fields.String(required=True)  # validate=lambda x: not x.index('-') or not x.index(','))
        level = fields.String(required=True)

    real_name = fields.String()
    pre_username = fields.String()
    gender = fields.Integer()
    email = fields.String()
    cv_name = fields.String()
    job_wanted_status = fields.Function(lambda x: JobWantedAttitude.int2str(x.job_wanted_status))
    abilities = fields.List(fields.Nested(AbilitySchema(many=False)))


class ProjectWithEngineers(Schema):
    id = fields.Int()
    name = fields.String()
    status = fields.Function(lambda x: ProjectStatus.int2str(x.status))
    engineers = fields.List(fields.Nested(EngineerDefaultSchema(many=False)))


class EducationPostSchema(BasePostSchema):
    _permission_roles = ['om']
    ModelClass = Education

    engineer_id = fields.Int(required=True)
    start_date = fields.Date(required=True)
    end_date = fields.Date(required=True)
    school = fields.String(required=True)
    major = fields.String(required=True)
    degree = fields.String(required=True)


class AbilitySchema(Schema):
    id = fields.Integer()
    name = fields.String(required=True)  # validate=lambda x: not x.index('-') or not x.index(','))
    level = fields.String(required=True)


class OrderSchema(Schema):
    start_date = fields.Date()
    end_date = fields.Date()
    renew_cycle = fields.Integer()
    auto_renew = fields.Integer()
    expect_total_fee = fields.Float()
    finished_fee = fields.Float()
    status = fields.Integer()


class EngineerDetailSchema(EngineerDefaultSchema):
    ability = fields.List(fields.Nested(AbilitySchema(many=False)))
    education = fields.List(fields.Nested(EducationDefaultSchema(many=False)))
    now_career = fields.Nested(CareerDefaultSchema(many=False))
    project = fields.String()
    now_order = fields.Nested(OrderSchema(many=False))
    company = fields.String()


class EngineerInterviewInfoSchema(Schema):
    id = fields.Integer()
    real_name = fields.String()
    cv_path = fields.List(fields.String())


class InterviewWithCvSchema(InterviewDefaultSchema):
    engineer = fields.Nested(EngineerInterviewInfoSchema(many=False))


class EngineerPutSchema(BaseUserPut):
    real_name = fields.Str()
    gender = fields.Integer()
    phone = fields.Str()
    email = fields.Str()

    job_wanted_status = fields.Function(lambda x: JobWantedAttitude.str2int(x.job_wanted_status),
                                        deserialize=lambda x: JobWantedAttitude.str2int(x))
    pay_welfare = fields.Integer(default=0, allow_none=True)
    welfare_rate = fields.Float()
    bank_code = fields.String(default='', allow_none=True)
    contract_confirm = fields.Integer(default=0, allow_none=True)
    activate = fields.Integer()


class EngineerUploadCvSchema(BaseActionSchema):
    ModelClass = Engineer
    action = 'upload_cv'
    _permission_roles = ['om', 'engineer']

    cv_upload_result = fields.String()


class DailyLogDefaultSchema(Schema):
    id = fields.Int()
    date = fields.Date()
    duration = fields.Float()
    content = fields.Str()
    note = fields.Str()
    origin_type = fields.Str()
    engineer_company_order_id = fields.Integer()
    is_workday = fields.Boolean()


class DailyLogPutSchema(BaseActionSchema):
    ModelClass = DailyLog
    _permission_roles = ['engineer']
    action = 'modify'

    content = fields.Str()
    duration = fields.Float()


class DailyLogEngineerPutSchema(Schema):
    content = fields.Str()


class LeavePostSchema(BasePostSchema):
    ModelClass = Leave
    _permission_roles = ['engineer']

    leave_type = fields.Str(required=True)
    start_date = fields.DateTime(required=True)
    end_date = fields.DateTime(required=True)
    duration = fields.Float(required=True)
    reason = fields.Str(required=True)


class EngineerDetailForPm(UserDefaultSchema):
    class CareerSchema(BaseSchema):
        start = fields.Date()
        position = fields.String()
        interview_id = fields.Integer()
        use_hr_service = fields.Integer()

        class PLS(Schema):
            name = fields.String()
            id = fields.Integer()
            money = fields.Float()
            position = fields.String()

        position_level = fields.Nested(PLS(many=False, unknown=EXCLUDE))

    now_career = fields.Nested(CareerSchema(many=False))
    status = fields.Function(lambda x: EngineerStatus.int2str(x.status))
    ability_score = fields.Float()
    attitude_score = fields.Float()
    total_score = fields.Float()
    rank = fields.Int()
    cv_name = fields.String()
    cv_path = fields.List(fields.String())
    project = fields.String()


class WorkReportCancelSchema(BaseActionSchema):
    ModelClass = WorkReport
    _permission_roles = ['engineer']
    action = 'cancel'


class EngineerInfoSchema(Schema):
    id = fields.Integer()
    position = fields.String()
    position_level = fields.String()  # 级别
    ability_score = fields.Float()  # 能力分
    attitude_score = fields.Float()  # 态度分
    rank = fields.Integer()  # 排名


class CareerInfoSchema(Schema):
    id = fields.Integer()
    start = fields.Date()  # 入项时间
    end = fields.Date()  # 出项时间
    pm = fields.String()  # 项目经理
    project = fields.String()  # 项目名称
    salary_type = fields.Integer(required=False)  # 计费方式  0 日结 1 月结
    s_money = fields.Float()  # 单价
    employ_type = fields.Float()  # 加入模式：0牛咖模式  1员工模式
    use_hr_service = fields.Bool()  # 招聘方式

    class CM(Schema):
        service_fee_rate = fields.Float(required=True)  # 平台服务费
        hr_fee_rate = fields.Float(required=True)  # HR服务费率
        finance_rate = fields.Float(required=True)  # 金融费率
        tax_rate = fields.Float(required=True)  # 综合税率
        work_station_fee = fields.Float()  # 工位费
        work_day_shift_rate = fields.Float()  # 工作日加班补偿系数
        weekend_shift_rate = fields.Float()  # 周末加班补偿系数
        holiday_shift_rate = fields.Float()  # 节假日加班补偿系数
        shift_type = fields.Float()  # 加班模式 0 调休 1 加班

    company = fields.Nested(CM(many=False))


class WorkReportInforSchema(Schema):
    absent_days = fields.Float()  # 矿工天数*8 ==时长
    shift_days = fields.Float()
    rest_days = fields.Float()
    work_duration = fields.Float()  # 出勤时长
    extra_work_duration = fields.Float()  # 加班时长
    shift_duration = fields.Float()  # 倒休
    out_project_days = fields.Float()  # 未入项天数*8


class PaymentInfoSchema(Schema):
    status = fields.Function(lambda x: x['status'] if type(x) is dict else PaymentStatus.int2str(x.status))
    company_pay = fields.Float()  # 人员服务费
    service_fee = fields.Float()  # 平台服务费
    tax = fields.Float()  # 税金费
    engineer_tax = fields.Float()
    break_up_fee = fields.Float()
    engineer_income_with_tax = fields.Float()
    finance_fee = fields.Float()  # 金融费
    hr_fee = fields.Float()  # Hr服务费
    ware_fare = fields.Float()  # 社保
    station_salary = fields.Float()  # 工位费
    extra_salary = fields.Float()  # 加班费
