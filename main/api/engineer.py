import os
from functools import lru_cache

from flask import request, jsonify
from flask_login import current_user
from marshmallow import EXCLUDE

from ..model import Roles, WorkReport, Engineer, Career, AuditStatus, DailyLog, DailyLogType, Payment, \
    int_year_month, dt, month_first_end_date, ExtraWork, Leave
from ..exception import NewComException
from ..schema.engineer import EngineerDefaultSchema, EngineerInfoSchema, WorkReportInforSchema, PaymentInfoSchema, \
    CareerInfoSchema
from ..util.try_catch import api_response
from ..util.work_dates import get_last_year_month, get_today, is_holiday, is_work_day
from ..schema.pm import WorkReportLatestMonthSchema, WorkReportLatestMonthDetailSchema, WorkReportDetailSchema, \
    WorkReportPostSchema, WorkReportMonthDetailEngineerSchema


# @lru_cache()  # 缓存【已取消】
def engineer_can_shift_duration(engieer_id, today_date):
    engineer_model = Engineer.query.get(engieer_id)
    extra_work = ExtraWork.query.filter_by(engineer_id=current_user.id, career_id=engineer_model.now_career_id,
                                           status=AuditStatus.checked).all()
    leave = Leave.query.filter_by(engineer_id=current_user.id, career_id=engineer_model.now_career_id,
                                  status=AuditStatus.checked).all()
    extra_work_days = WorkReport.filter_extra_work_days(extra_work, dict(), dict())

    work_extra_duration = extra_work_days[3]
    holiday_extra_duration = extra_work_days[4]
    weekend_extra_duration = extra_work_days[5]
    total_extra_duration = work_extra_duration * engineer_model.company.work_day_shift_rate + \
                           holiday_extra_duration * engineer_model.company.holiday_shift_rate + \
                           weekend_extra_duration * engineer_model.company.weekend_shift_rate

    shift_days = list(filter(lambda x: x.leave_type == DailyLogType.shift, leave))
    can_shift_duration = total_extra_duration - sum([x.duration for x in shift_days])
    shift_type = engineer_model.company.shift_type
    return can_shift_duration, shift_type


@api_response
def can_shift_duration():
    if not current_user.role == Roles.engineer:
        raise NewComException('bad role', 501)
    can_shift_duration, shift_type = engineer_can_shift_duration(current_user.id, get_today())
    result = {'can_shift_duration': can_shift_duration, 'shift_type': shift_type}
    return jsonify(result)


def latest_shown_month(engineer_id):
    # todo: 工程师逾期提交后撤销，此接口无法显示未提交工时
    engineer = Engineer.query.get(int(engineer_id))
    last_year_month = get_last_year_month()
    if not engineer.now_career_id:
        raise NewComException('该工程师没有在职的项目', 403)
    start_month = Career.query.get(engineer.now_career_id).start.strftime('%Y%m')
    if int(start_month) >= int(get_today().strftime('%Y%m')):
        shown_month = int(get_today().strftime('%Y%m'))
    else:

        last_month_checked = WorkReport.query.filter_by(career_id=engineer.now_career_id, year_month=last_year_month,
                                                        status=AuditStatus.checked).first()
        if last_month_checked:
            shown_month = int(get_today().strftime('%Y%m'))
        else:
            shown_month = last_year_month
    return last_year_month, shown_month


@api_response
def latest_work_report():
    engineer_id = current_user.id if current_user.role == Roles.engineer else request.args.get('engineer_id')
    last_year_month, shown_month = latest_shown_month(engineer_id)
    statistic = WorkReport.statistic_of(engineer_id=engineer_id, year_month=shown_month)
    statistic['need_submit'] = last_year_month == shown_month
    schema_type = request.args.get('schema', 'WorkReportLatestMonthSchema')
    schema = eval(schema_type)(many=False, unknown=EXCLUDE)
    return jsonify(schema.dump(statistic))


# 字典对象转换可以使用.语法
class Dict(dict):
    __setattr__ = dict.__setitem__
    __getattr__ = dict.__getitem__


def dict_to_object(dictobj):
    if not isinstance(dictobj, dict):
        return dictobj
    inst = Dict()
    for k, v in dictobj.items():
        inst[k] = dict_to_object(v)
    return inst


@api_response
def engineer_details():
    engineer_id = request.args.get('engineer_id')
    involve_engineer = Engineer.query.filter_by(id=engineer_id).first()
    involve_engineer_info = EngineerInfoSchema(many=False, unknown=EXCLUDE).dump(involve_engineer)
    year_month = request.args.get('year_month', int_year_month(get_today()))
    involve_work_report = WorkReport.query.filter_by(year_month=year_month,
                                                     career_id=involve_engineer.now_career_id).first()
    involve_career_info = CareerInfoSchema(many=False, unknown=EXCLUDE).dump(involve_engineer.now_career)

    if involve_work_report is None and involve_engineer.now_career is None:  # 人员已出项，可查询历史记录
        histroy_career = Career.query.filter_by(engineer_id=involve_engineer.id).all()
        for c in histroy_career:
            if int(year_month) in list(range(int_year_month(c.start), int_year_month(c.end) + 1)):
                involve_career_info = CareerInfoSchema(many=False, unknown=EXCLUDE).dump(c)
                involve_work_report = WorkReport.query.filter_by(year_month=year_month, career_id=c.id).first()

    if involve_work_report:
        involve_work_info = WorkReportInforSchema(many=False, unknown=EXCLUDE).dump(involve_work_report)
        involve_payment = Payment.query.filter_by(year_month=year_month, engineer_id=engineer_id).first()
        if involve_payment:
            involve_payment_info = PaymentInfoSchema(many=False, unknown=EXCLUDE).dump(involve_payment)
        else:
            cal_kwargs = Payment.get_cal_kwargs(involve_engineer, involve_work_report)
            involve_payment = Payment.cal_payment(**cal_kwargs)
            involve_payment['status'] = 'unmake'
            involve_payment_info = PaymentInfoSchema(many=False, unknown=EXCLUDE).dump(involve_payment)
    else:
        try:
            statistic = WorkReport.statistic_of(engineer_id=engineer_id, year_month=year_month)
        except Exception as e:
            return jsonify({"debug": str(e)})
        statistic = dict_to_object(statistic)
        workreport_year_month = dict_to_object({'year_month': year_month})
        if involve_engineer.now_career is None: return jsonify({"debug": "该人员当前月份无在职信息"})
        if int_year_month(involve_engineer.now_career.start) == year_month:
            out_project_days = WorkReport.cal_out_project_days(workreport_year_month, involve_engineer)
        else:
            out_project_days = 0
        statistic['out_project_days'] = out_project_days
        involve_work_info = WorkReportInforSchema(many=False, unknown=EXCLUDE).dump(statistic)
        cal_kwargs = Payment.get_cal_kwargs(involve_engineer, statistic)
        involve_payment = Payment.cal_payment(**cal_kwargs)
        involve_payment['status'] = 'unmake'
        involve_payment_info = PaymentInfoSchema(many=False, unknown=EXCLUDE).dump(involve_payment)
    involve_engineer_info['career'] = involve_career_info
    involve_engineer_info['work_report'] = involve_work_info
    involve_engineer_info['payment'] = involve_payment_info
    return jsonify(involve_engineer_info)


def init_api(app, url_prefix):
    app.add_url_rule(os.path.join(url_prefix, 'engineer/can_shift_duration'),
                     endpoint='engineer.can_shift_duration', view_func=can_shift_duration, methods=['GET'])

    app.add_url_rule(os.path.join(url_prefix, 'engineer/latest_work_report'),
                     endpoint='engineer.latest_work_report', view_func=latest_work_report, methods=['GET'])

    app.add_url_rule(os.path.join(url_prefix, 'engineer/details'),
                     endpoint='engineer.details', view_func=engineer_details, methods=['GET'])
