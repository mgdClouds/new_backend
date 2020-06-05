from marshmallow import Schema, fields, EXCLUDE

from .base import BaseSchema, BasePostSchema, BasePutSchema, BaseActionSchema
from .engineer import DailyLogDefaultSchema, EngineerDefaultSchema, ProjectWithEngineers
from .user import AppointTime
from ..model import Interview, Pm, ExtraWork, Leave, Entry, WorkReport, MonthlyBill, InterviewStatus, \
    Resign, Payment, AuditStatus, PaymentStatus, MonthlyBillStatus, LeaveInfoSchema, ExtraWorkInfoSchema


class InterviewPostSchema(BasePostSchema):
    ModelClass = Interview
    engineer_id = fields.Integer()
    offer_id = fields.Int()


class InterviewPmPutSchema(Schema):
    status = fields.Function(lambda x: x, deserialize=lambda x: InterviewStatus.str2int(x))


class InterviewStatusPutSchema(BaseActionSchema):
    ModelClass = Interview
    _permission_roles = ['om', 'pm']
    action = 'status'

    status = fields.Function(lambda x: x, deserialize=lambda x: InterviewStatus.str2int(x), required=True)
    pm_free_time = fields.List(fields.Nested(AppointTime(many=False, unknown=EXCLUDE), required=False))
    appoint_time = fields.Nested(AppointTime(many=False, unknown=EXCLUDE), required=False)
    result_note = fields.Str(required=False, allow_none=True)
    final_position_level_id = fields.Integer()
    entry_before = fields.Date()
    note = fields.Str(required=False, allow_none=True)


class InterviewEntryPutSchema(BaseActionSchema):
    ModelClass = Interview
    _permission_roles = ['om', 'pm']
    action = 'entry'

    date = fields.Date(required=True)
    position_level_id = fields.Integer()
    note = fields.Str(required=False, allow_none=True)


class PmCanAppointTimePutSchema(BaseActionSchema):
    _permission_roles = ['pm']
    ModelClass = Pm
    action = 'set_can_appoint_time'

    set_info = fields.List(fields.Nested(AppointTime(many=False, unknown=EXCLUDE)))
    set_default = fields.Bool()


class AuditDetailSchema(BaseSchema):
    company_id = fields.Integer()
    company = fields.String()
    project_id = fields.Integer()
    project = fields.String()
    pm_id = fields.Integer()
    pm = fields.String()
    engineer_id = fields.Integer()
    engineer = fields.String()
    audit_type = fields.String()
    status = fields.Function(lambda x: x['status'] if type(x) is dict else AuditStatus.int2str(x.status))
    comment = fields.String()


class LeaveDefaultSchema(AuditDetailSchema):
    leave_type = fields.String(required=False)
    start_date = fields.DateTime(required=False)
    end_date = fields.DateTime(required=False)
    duration = fields.Float()
    reason = fields.String()


class LeaveCheckPutSchema(BaseActionSchema):
    ModelClass = Leave
    _permission_roles = ['pm']
    action = 'check'

    status = fields.Function(lambda x: x, deserialize=lambda x: AuditStatus.str2int(x))
    comment = fields.String(required=False)


class ExtraWorkDefaultSchema(AuditDetailSchema):
    reason = fields.String()
    start_date = fields.DateTime(required=False)
    end_date = fields.DateTime(required=False)
    duration = fields.Float()


class ExtraWorkPostSchema(BasePostSchema):
    _permission_roles = ['engineer']
    ModelClass = ExtraWork

    start_date = fields.DateTime(required=True)
    end_date = fields.DateTime(required=True)
    duration = fields.Float(required=True)
    reason = fields.String(required=True)


class ExtraWorkCheckPutSchema(BaseActionSchema):
    ModelClass = ExtraWork
    _permission_roles = ['pm']
    action = 'check'

    status = fields.Function(lambda x: x, deserialize=lambda x: AuditStatus.str2int(x))
    comment = fields.String(required=False)


class WorkReportDefaultSchema(AuditDetailSchema):
    class EngineerSchema(BaseSchema):
        pre_username = fields.String()
        real_name = fields.String()
        project = fields.String()

    year_month = fields.Int()
    work_days = fields.Float()
    leave_days = fields.Float()
    extra_work_days = fields.Float()
    absent_days = fields.Float()
    shift_days = fields.Float()

    work_duration = fields.Float()
    leave_duration = fields.Float()
    extra_work_duration = fields.Float()
    shift_duration = fields.Float()

    work_extra_duration = fields.Float()
    holiday_extra_duration = fields.Float()
    weekend_extra_duration = fields.Float()
    extra_station_duration = fields.Float()

    attitude_score = fields.Float()
    ability_score = fields.Float()
    total_score = fields.Float()
    rest_days = fields.Float()
    engineer = fields.Nested(EngineerSchema(many=False))
    rank = fields.Int()


class WorkReportPostSchema(Schema):
    year_month = fields.Int()
    work_days = fields.Float()
    leave_days = fields.Float()
    extra_work_days = fields.Float()

    work_duration = fields.Float()
    leave_duration = fields.Float()
    extra_work_duration = fields.Float()
    shift_duration = fields.Float()

    work_extra_duration = fields.Float()
    holiday_extra_duration = fields.Float()
    weekend_extra_duration = fields.Float()
    extra_station_duration = fields.Float()

    absent_days = fields.Float()
    shift_days = fields.Float()
    rest_days = fields.Float()
    out_project_days = fields.Float()


class WorkReportLatestMonthSchema(WorkReportDefaultSchema):
    need_submit = fields.Bool()


class WorkReportDetailSchema(WorkReportDefaultSchema):
    work_days_list = fields.List(fields.Nested(DailyLogDefaultSchema(many=False)))
    leave_days_list = fields.List(fields.Nested(LeaveInfoSchema(many=False)))
    extra_work_days_list = fields.List(fields.Nested(ExtraWorkInfoSchema(many=False)))
    absent_days_list = fields.List(fields.Nested(DailyLogDefaultSchema(many=False)))
    shift_days_list = fields.List(fields.Nested(LeaveInfoSchema(many=False)))
    rest_days_list = fields.List(fields.Nested(DailyLogDefaultSchema(many=False)))


class WorkReportLatestMonthDetailSchema(WorkReportDetailSchema):
    need_submit = fields.Bool()


class WorkReportMonthDetailEngineerSchema(WorkReportDefaultSchema):
    class Eg(Schema):
        real_name = fields.Str()
        email = fields.Str()
        phone = fields.Str()
        cv_name = fields.String()
        cv_path = fields.List(fields.String())
        ability_score = fields.Float()
        attitude_score = fields.Float()
        total_score = fields.Float()
        rank = fields.Integer()

    engineer = fields.Nested(Eg(many=False))

    class CA(Schema):
        position = fields.String()
        position_level = fields.String()
        s_money = fields.Float()
        interview_id = fields.Integer()
        salary_type = fields.Integer()
        start = fields.Date()

    career = fields.Nested(CA(many=False))


class WorkReportCheckPutSchema(BaseActionSchema):
    ModelClass = WorkReport
    action = 'status'
    _permission_roles = ['pm']

    status = fields.Function(lambda x: x, deserialize=lambda x: AuditStatus.str2int(x))
    ability_score = fields.Float()
    attitude_score = fields.Float()
    comment = fields.String()


class WorkReportReSubmitPutSchema(BaseActionSchema):
    ModelClass = WorkReport
    action = 'resubmit'
    _permission_roles = ['engineer']


class EntryDefaultSchema(AuditDetailSchema):
    date = fields.Date()

    position_level = fields.String()
    interview_id = fields.Integer()

    reject_position_level_id = fields.Integer()
    position_level_id = fields.Integer()


class EntryFileAuditSchema(AuditDetailSchema):
    date = fields.Date()

    class ES(Schema):
        ef_name = fields.String()
        ef_path = fields.List(fields.String())
        id = fields.Integer()
        real_name = fields.String()

    engineer = fields.Nested(ES(many=False))


class EntryDetailSchema(EntryDefaultSchema):
    class PLS(Schema):
        id = fields.Integer()
        name = fields.String()
        money = fields.Float()
        position = fields.String()

    position_level = fields.Nested(PLS(many=False))
    reject_position_level = fields.Nested(PLS(many=False))

    class IS(Schema):
        entry_before = fields.Date()

    interview = fields.Nested(IS(many=False))


class EntryCheckSchema(BaseActionSchema):
    ModelClass = Entry
    _permission_roles = ['om', 'pm']
    action = 'check'

    status = fields.Function(lambda x: x, deserialize=lambda x: AuditStatus.str2int(x))
    comment = fields.Str(required=False)


class ResignDefaultSchema(AuditDetailSchema):
    date = fields.Date()
    reason = fields.String()
    position_level = fields.String()


class ResignPostSchema(BasePostSchema):
    ModelClass = Resign
    _permission_roles = ['om']

    date = fields.Date(required=True)
    reason = fields.String(required=False)
    engineer_id = fields.Integer(required=True)


class ResignCheckSchema(BaseActionSchema):
    ModelClass = Resign
    _permission_roles = ['om', 'pm']
    action = 'check'

    status = fields.Function(lambda x: x, deserialize=lambda x: AuditStatus.str2int(x))
    comment = fields.String()


class WorkReportSchema(BaseSchema):
    year_month = fields.Int()
    work_days = fields.Float()
    leave_days = fields.Float()
    extra_work_days = fields.Float()
    absent_days = fields.Float()
    shift_days = fields.Float()
    rest_days = fields.Float()
    rank = fields.Int()
    status = fields.Function(lambda x: AuditStatus.int2str(x.status))


class PaymentDefaultSchema(BaseSchema):
    year_month = fields.Int()
    engineer = fields.String()
    company_pay = fields.Float()
    engineer_get = fields.Float()
    tax = fields.Float()
    fee = fields.Float()
    income = fields.Float()
    work_report = fields.Nested(WorkReportSchema(many=False))


class PaymentTableSchema(BaseSchema):
    class WD(WorkReportSchema):
        work_days_list = fields.List(fields.Nested(DailyLogDefaultSchema(many=False)))
        leave_days_list = fields.List(fields.Nested(LeaveInfoSchema(many=False)))
        extra_work_days_list = fields.List(fields.Nested(ExtraWorkInfoSchema(many=False)))
        absent_days_list = fields.List(fields.Nested(DailyLogDefaultSchema(many=False)))
        shift_days_list = fields.List(fields.Nested(LeaveInfoSchema(many=False)))
        rest_days_list = fields.List(fields.Nested(DailyLogDefaultSchema(many=False)))

    class C(Schema):
        class OS(Schema):
            position = fields.String()
            position_level = fields.String()
            money = fields.Float()

        s_money = fields.Float()

        offer = fields.Nested(OS(many=False))

    class E(Schema):
        real_name = fields.String()
        welfare_rate = fields.String()

    class PLS(Schema):
        money = fields.Float()
        name = fields.String()

    career = fields.Nested(C(many=False))
    position_level = fields.Nested(PLS(many=False))
    year_month = fields.Int()
    engineer = fields.Nested(E(many=False))
    engineer_id = fields.Int()
    company_pay = fields.Float()
    income = fields.Float()
    tax = fields.Float()
    fee = fields.Float()
    welfare = fields.Float()
    amerce = fields.Float()
    status = fields.Function(lambda x: PaymentStatus.int2str(x.status))
    engineer_tax = fields.Float()
    engineer_get = fields.Float()
    break_up_fee = fields.Float()
    engineer_income_with_tax = fields.Float()
    finance_fee = fields.Float()
    hr_fee = fields.Float()
    service_fee_rate = fields.Float()
    employ_type = fields.Integer()
    out_duty_days = fields.Float()
    finance_rate = fields.Float()
    tax_fee_rate = fields.Float()
    tax_rate = fields.Float()
    use_hr_servce = fields.Integer()
    ware_fare = fields.Float()
    pm = fields.String()
    project = fields.String()
    work_report = fields.Nested(WD(many=False))
    station_salary = fields.Float()
    extra_salary = fields.Float()
    tax_free_rate = fields.Float()

class PaymentTableSchemaWithDayList(PaymentTableSchema):
    class WD(WorkReportSchema):
        work_days_list = fields.List(fields.Nested(DailyLogDefaultSchema(many=False)))
        leave_days_list = fields.List(fields.Nested(LeaveInfoSchema(many=False)))
        extra_work_days_list = fields.List(fields.Nested(ExtraWorkInfoSchema(many=False)))
        absent_days_list = fields.List(fields.Nested(DailyLogDefaultSchema(many=False)))
        shift_days_list = fields.List(fields.Nested(LeaveInfoSchema(many=False)))
        rest_days_list = fields.List(fields.Nested(DailyLogDefaultSchema(many=False)))

    work_report = fields.Nested(WD(many=False))


class PaymentPurchaseExcelSchema(BaseActionSchema):
    ModelClass = Payment
    _permission_roles = ['om']
    action = "purchase_schema"


class PaymentForPurchaseSchema(BaseSchema):
    class WS(Schema):
        class CS(Schema):
            class OS(Schema):
                position = fields.String()
                position_level = fields.String()
                money = fields.Float()

            offer_sheet = fields.Nested(OS(many=False))

        career = fields.Nested(CS(many=False))
        pm = fields.String()
        project = fields.String()
        work_days = fields.Float()
        rest_days = fields.Float()
        shift_days = fields.Float()
        extra_work_days = fields.Float()
        absent_days = fields.Float()
        leave_days = fields.Float()
        ability_score = fields.Float()
        attitude_score = fields.Float()
        total_score = fields.Float()
        rank = fields.Int()
        status = fields.Function(lambda x: AuditStatus.int2str(x.status))

    year_month = fields.Int()
    engineer = fields.String()
    engineer_id = fields.Integer()
    company_pay = fields.Float()
    tax = fields.Float()
    fee = fields.Float()
    income = fields.Float()
    work_report = fields.Nested(WS(many=False))
    status = fields.Function(lambda x: PaymentStatus.int2str(x.status))


class PaymentWithWorkReportDetailSchema(PaymentDefaultSchema):
    work_report = fields.Nested(WorkReportDetailSchema(many=False))


class EngineerForPaymentListSchema(BaseSchema):
    class CareerSchema(BaseSchema):
        class O(BaseSchema):
            money = fields.Float()

        position = fields.String()
        position_level = fields.String()
        offer_sheet = fields.Nested(O(many=False))

    id = fields.Int()
    real_name = fields.String()
    project = fields.String()
    rank = fields.Integer()
    now_career = fields.Nested(CareerSchema(many=False))


class WorkReportForPaymentListSchema(BaseSchema):
    work_days = fields.Float()
    leave_days = fields.Float()
    absent_days = fields.Float()
    extra_work_days = fields.Float()
    shift_days = fields.Integer()
    attitude_score = fields.Float()
    ability_score = fields.Float()
    total_score = fields.Float()
    rank = fields.Int()
    income = fields.Float()


class PaymentListSchema(BaseSchema):
    # todo 项目经理端项目详情用这个
    engineer_id = fields.Integer()

    class ES(Schema):
        real_name = fields.String()

    engineer = fields.Nested(ES(many=False))
    company_pay = fields.Float()
    tax = fields.Float()
    fee = fields.Float()
    income = fields.Float()

    class CA(Schema):
        project = fields.String()
        s_money = fields.String()

        class PLS(Schema):
            position = fields.String()
            name = fields.String()

        position_level = fields.Nested(PLS(many=False))

    career = fields.Nested(CA(many=False))

    class WRS(Schema):
        year_month = fields.Int()
        work_days = fields.Float()
        leave_days = fields.Float()
        extra_work_days = fields.Float()
        absent_days = fields.Float()
        shift_days = fields.Float()
        attitude_score = fields.Float()
        ability_score = fields.Float()
        total_score = fields.Float()
        rest_days = fields.Float()
        rank = fields.Int()

    work_report = fields.Nested(WRS(many=False))


class MonthlyBillDefaultSchema(BaseSchema):
    company_id = fields.Integer()
    money = fields.Float(required=True)
    year_month = fields.Integer(required=True)


class MonthlyBillPostSchema(BasePostSchema):
    _permission_roles = ['om']
    ModelClass = MonthlyBill
    year_month = fields.Integer(required=True)
    company_id = fields.Integer(required=True)


class MonthlyBillPutSchema(BaseActionSchema):
    _permission_roles = ['purchase']
    ModelClass = MonthlyBill
    action = 'pay'

    status = fields.Function(lambda x: x, lambda x: MonthlyBillStatus.str2int(x))


class PmEngineerListSchema(BaseSchema):
    class CS(Schema):
        class OS(Schema):
            money = fields.String()
            position = fields.String()
            position_level = fields.String()

        offer_sheet = fields.Nested(OS(many=False))

    real_name = fields.String()
    project = fields.String()
    now_career = fields.Nested(CS(many=False))


class PmOfferInterviewList(BaseSchema):
    class EI(Schema):
        engineer = fields.String()
        position = fields.String()

        class PLS(Schema):
            name = fields.String()

        final_position_level = fields.Nested(PLS(many=False))
        entry_date = fields.Date()
        id = fields.Integer()

    entry_interviews = fields.List(fields.Nested(EI(many=False)))
