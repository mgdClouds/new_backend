import os
from functools import lru_cache

from flask import request, jsonify
from flask_login import current_user
from marshmallow import EXCLUDE, Schema, fields

from ..model import Roles, Payment, MonthlyBill, db, PaymentStatus, EnterProject, Engineer, User, EngineerStatus, \
    EnterProjectStatus, Offer, JobWantedAttitude
from ..model.engineer import EnterProjectPostSchema
from ..exception import NewComException
from ..schema.company import OfferDefaultSchema
from ..util.try_catch import api_response
from ..util.work_dates import get_last_year_month, get_today


@lru_cache()
def get_monthly_payments_of_pm(year_month, pm_id, today):
    payments = Payment.query.filter(Payment.pm_id == pm_id, Payment.year_month == year_month).all()
    if not payments:
        return None
    result = {"engineer_count": 0, "work_days_num": 0, "average_ability_score": 0, "average_attitude_score": 0,
              "total_money": 0, "projects": {}}
    projects = result['projects']
    for payment in payments:
        project_name = payment.project.name
        if project_name not in projects.keys():
            projects[project_name] = {'engineer_count': 0, 'work_days_num': 0, 'average_ability_score': 0,
                                      'average_attitude_score': 0, 'total_money': 0}
        projects[project_name]['engineer_count'] += 1
        projects[project_name]['work_days_num'] += payment.work_report.work_days
        projects[project_name]['average_ability_score'] += payment.work_report.ability_score
        projects[project_name]['average_attitude_score'] += payment.work_report.attitude_score
        projects[project_name]['total_money'] += payment.company_pay
        projects[project_name]['name'] = project_name

        result['engineer_count'] += 1
        result['work_days_num'] += payment.work_report.work_days
        result['average_ability_score'] += payment.work_report.ability_score
        result['average_attitude_score'] += payment.work_report.attitude_score
        result['total_money'] += payment.company_pay

    for value in projects.values():
        value['average_ability_score'] = value['average_ability_score'] / value['engineer_count']
        value['average_attitude_score'] = value['average_attitude_score'] / value['engineer_count']
    result['average_ability_score'] = result['average_ability_score'] / result['engineer_count']
    result['average_attitude_score'] = result['average_attitude_score'] / result['engineer_count']
    result['projects'] = list(result['projects'].values())
    result['total_money'] = round(result['total_money'], 2)
    return result


@lru_cache()
def get_monthly_payments(year_month, company_id, today):
    payments = Payment.query.filter(Payment.company_id == company_id, Payment.year_month == year_month,
                                    Payment.status == PaymentStatus.checked).all()
    result = {"engineer_count": 0, "work_days_num": 0, "average_ability_score": 0, "average_attitude_score": 0,
              "total_money": 0, "pms": []}
    pms = {}  # result['pms']
    if not payments:
        raise NewComException('未生成过月统计', 403)
    for payment in payments:
        pm_name = payment.pm.real_name or payment.pm.pre_username
        if pm_name not in pms.keys():
            pms[pm_name] = {'engineer_count': 0, 'work_days_num': 0, 'average_ability_score': 0,
                            'average_attitude_score': 0, 'total_money': 0}
        pms[pm_name]['engineer_count'] += 1
        pms[pm_name]['work_days_num'] += payment.work_report.work_days
        pms[pm_name]['average_ability_score'] += payment.work_report.ability_score
        pms[pm_name]['average_attitude_score'] += payment.work_report.attitude_score
        pms[pm_name]['total_money'] += payment.company_pay
        pms[pm_name]['real_name'] = pm_name
        pms[pm_name]['id'] = payment.pm.id

        result['engineer_count'] += 1
        result['work_days_num'] += payment.work_report.work_days
        result['average_ability_score'] += payment.work_report.ability_score
        result['average_attitude_score'] += payment.work_report.attitude_score
        result['total_money'] += payment.company_pay

    for value in pms.values():
        value['average_ability_score'] = value['average_ability_score'] / value['engineer_count']
        value['average_attitude_score'] = value['average_attitude_score'] / value['engineer_count']
    result['average_ability_score'] = result['average_ability_score'] / result['engineer_count']
    result['average_attitude_score'] = result['average_attitude_score'] / result['engineer_count']
    result['year_month'] = year_month
    result['pms'] = list(pms.values())
    result['total_money'] = round(result['total_money'], 2)
    return result


@api_response
def monthly_payments():
    if not current_user.role == Roles.purchase:
        raise NewComException('权限错误', 500)
    year_month = request.args.get('year_month', None)
    if not year_month:
        latest_monthly_bill = MonthlyBill.query.filter_by(
            company_id=current_user.company_id,
        ).order_by(db.desc(MonthlyBill.year_month)).first()
        if not latest_monthly_bill:
            raise NewComException('未生成过月统计', 404)
        year_month = latest_monthly_bill.year_month
    result = get_monthly_payments(year_month, current_user.company_id, get_today())
    return jsonify(result)


@api_response
def monthly_pm_payments():
    if not current_user.role == Roles.purchase:
        raise NewComException('权限错误', 500)
    year_month = request.args.get('year_month', None)
    pm_id = request.args.get('pm_id', None)
    if not year_month or not pm_id:
        raise NewComException('参数缺失', 500)
    result = get_monthly_payments_of_pm(year_month, pm_id, get_today())
    if not result:
        raise NewComException('无该月信息', 403)
    return jsonify(result)


class DirectEnterProjectSchema(Schema):
    class SimpleEngineerSchema(Schema):
        real_name = fields.String()
        gender = fields.Integer()
        phone = fields.String()
        email = fields.String()
        cv_upload_result = fields.String()

    engineer = fields.Nested(SimpleEngineerSchema(many=False, unknown=EXCLUDE))

    project_id = fields.Integer()
    pm_id = fields.Integer()
    position_level_id = fields.Integer()
    salary_type = fields.Integer()
    work_content = fields.String()
    start_date = fields.Date()
    service_type = fields.String()
    work_place = fields.String()


@api_response
def direct_enter_project():
    data = request.json
    data = DirectEnterProjectSchema(many=False).load(data)
    eg = data['engineer']
    already = User.query.filter(User.phone == eg['phone']).first()
    if already:
        _enp = EnterProject.query.filter(EnterProject.engineer_id == already.id, EnterProject.ing != 0).first()
        if _enp:
            raise NewComException('该员工已存在入项中的流程。', 501)
        if already.role == Roles.engineer:
            if already.status == EngineerStatus.on_duty:
                raise NewComException('该手机号的绑定的用户已在平台内任职。', 501)
            already.update(**eg)
        else:
            raise NewComException('手机号已被占用，且占用者非工程师!', 501)
        engineer_id = already.id
    else:
        result = Engineer.post(**eg)
        engineer_id = result.id
    engineer = Engineer.query.get(engineer_id)
    data.pop('engineer')
    data['start_date'] = request.json['start_date']
    data['engineer_id'] = engineer_id
    data['company_id'] = current_user.company_id
    data['new_engineer'] = 0 if already else 1
    # todo 检查输入的项目，项目经理等是否是本公司的，是否符合其他约束。
    result = EnterProject.post(**data)
    engineer.update(status=EngineerStatus.entering, job_wanted_status=JobWantedAttitude.negative)
    result.update(status=EnterProjectStatus.purchase_agree)  # 设置增员人员状态为人员提交材料中
    return jsonify(dict(id=result.id))


@api_response
def enter_project_statistic():
    company_id = current_user.company_id if current_user.role != Roles.om else request.args.get('company_id')
    result = EnterProject.company_statistic(company_id)
    return jsonify(result)


def init_api(app, url_prefix):
    app.add_url_rule(os.path.join(url_prefix, 'purchase/monthly_payments'),
                     endpoint='purchase.monthly_payments', view_func=monthly_payments, methods=['GET'])
    app.add_url_rule(os.path.join(url_prefix, 'purchase/monthly_pm_payments'),
                     endpoint='purchase.monthly_pm_payments', view_func=monthly_pm_payments, methods=['GET'])
    app.add_url_rule(os.path.join(url_prefix, 'purchase/direct_enter_project'),
                     endpoint='purchase.direct_enter_project', view_func=direct_enter_project, methods=['POST'])
    app.add_url_rule(os.path.join(url_prefix, 'purchase/enter_project_statistic'),
                     endpoint='purchase.enter_project_statistic', view_func=enter_project_statistic, methods=['GET'])
