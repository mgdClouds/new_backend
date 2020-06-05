import datetime as dt

from flask import current_app, url_for
from flask_login import current_user

# cobra-55555 -20-04-18
from sqlalchemy import UniqueConstraint, func
# // // // // //

from marshmallow import EXCLUDE

from ..util.work_dates import int_year_month, get_today
from ._base import Base, OfferShutDownReason, OfferStatus, PostSchema, fields, Schema, BaseStatus
from ..schema.base import re_phone, re_email, BaseActionSchema, BasePutSchema
from ..extention import db
from .engineer import Interview, InterviewStatus, Entry, AuditStatus, WorkReport, WorkReportWithPayment, Payment, \
  PaymentStatus, PaymentSimpleSchema, Resign, Career, WorkReportWithSimplePayment, EngineerCompanyOrder, Engineer, \
  EngineerStatus, CareerStatus, EnterProject, EnterProjectStatus, Education, WrittenInterviewInfo, JobExperience, \
  ProjectExperience, Language, Langcert, Ability
from ..util.personal_tax import cal as cal_personal_tax
from .user import User, Roles
from .pm import Pm
from ..exception import NewComException

__all__ = ["Company", "Position", "PositionLevel", "Project", "OfferStatus", "OfferShutDownReason",
       "Offer", "OfferStatistics", "CompanyOm", "OfferPostSchema", "PositionWithLevelsSchema",
       "ProjectAddPmSchema", 'ProjectPutSchema', 'PositionPutSchema', "PositionLevelPutSchema",
       "OfferDetailSchema", 'ProjectWithPmsEngineers', 'ProjectWithPms', 'ProjectChangePmSchema',
       'ProjectRemovePmSchema', 'CompanyChangeStatusSchema', 'WorkReportStatistic', 'UnChekcedPayments',
       'ProjectStatus', 'TotalPaymentsSchema']


class ShiftType(object):
  money = 0
  rest = 1

  @classmethod
  def int2str(cls, value):
    try:
      return cls.__dict__[value]
    except:
      raise NewComException('状态值不正确。', 403)


class Company(Base):
  __tablename__ = 'company'

  name = db.Column(db.String(64), unique=True)
  contact = db.Column(db.String(16))
  phone = db.Column(db.String(11), unique=True)
  email = db.Column(db.String(64), unique=True)
  address = db.Column(db.String(128))
  contract_uuid = db.Column(db.String(256))
  contract_name = db.Column(db.String(256))
  om_name = db.Column(db.String(16))
  entry_file_template = db.Column(db.String(64))
  activate = db.Column(db.Integer())

  billing_cycle = db.Column(db.Integer(), doc='资金成本')
  service_fee_rate = db.Column(db.Float(), doc='平台服务费率')
  tax_rate = db.Column(db.Float(), doc='综合税率')
  hr_fee_rate = db.Column(db.Float(), doc='HR服务费率')
  finance_rate = db.Column(db.Float(), doc='金融费率')

  work_station_fee = db.Column(db.Float(), doc='工位费')
  charging_num = db.Column(db.Float(), doc='计费天数')
  ware_fare = db.Column(db.Float, nullable=False, doc='社保')
  tax_free_rate = db.Column(db.Float, doc='税优费率')
  break_up_fee_rate = db.Column(db.Float, doc='离职补偿费率')

  shift_type = db.Column(db.Integer(), doc='补偿方案')  # 0 补偿调休 1补偿加班费
  work_day_shift_rate = db.Column(db.Float, doc='工作日加班补偿系数')
  weekend_shift_rate = db.Column(db.Float, doc='周末加班补偿系数')
  holiday_shift_rate = db.Column(db.Float, doc='假日加班补偿系数')

  purchases = db.relationship('Purchase', backref='company')
  pms = db.relationship('Pm', backref='company')
  projects = db.relationship('Project', backref='company')
  position_levels = db.relationship('PositionLevel', backref='company')
  engineers = db.relationship('Engineer', backref='company')
  interviews = db.relationship('Interview', backref='company')
  enter_projects = db.relationship('EnterProject', backref='company')
  offers = db.relationship('Offer', backref='company')

  def __repr__(self):
    return self.name

  @property
  def open_projects_count(self):
    return len(list(filter(lambda x: x.status == ProjectStatus.open, self.projects)))

  @property
  def open_offers_count(self):
    return len(list(filter(lambda x: x.status == OfferStatus.open, self.offers)))

  @property
  def entry_file_checking_count(self):
    return len(list(filter(lambda x: x.status == EnterProjectStatus.file_submit, self.enter_projects)))

  @property
  def interview_statistic(self):
    # 此处的cv_pass 和 interview_pass 不是全部，是当前
    result = dict()
    try:
      ivs = list(self.interviews)
      cv_pass_count = len(list(filter(lambda x: abs(x.status) < 3, ivs)))
      result['cv_pass'] = cv_pass_count
      interview_pass_count = len(list(filter(lambda x: abs(x.status) in [9, 11], ivs)))
      result['interview_pass'] = interview_pass_count
    except:
      result['cv_pass'] = 0
      result['interview_pass'] = 0
    return result

  @property
  def enter_project_statistic(self):
    eps = list(self.enter_projects)
    result = dict()
    result['purchase_agree'] = len(list(filter(lambda x: x.status == "purchase_agree", eps)))
    result['pm_agree'] = len(list(filter(lambda x: x.status == "pm_agree", eps)))
    result['file_pm_count'] = len(list(filter(lambda x: x.status == 'file_pm_count', eps)))
    result['file_company_agree_count'] = len(
      list(filter(lambda x: x.status == EnterProjectStatus.file_company_agree, eps)))
    return result

  @property
  def engineer_statistic(self):
    es = self.engineers
    result = dict(total=len(es))
    leave = Resign.query.filter_by(company_id=self.id, status=AuditStatus.submit).all()
    leaving_count = len(list(filter(lambda x: x.status == AuditStatus.submit, leave)))
    leave_count = len(list(filter(lambda x: x.status == AuditStatus.checked, leave)))
    result['leaving_count'] = leaving_count
    result['leave_count'] = leave_count
    result['on_duty_count'] = len(list(filter(lambda x: x.now_career.status == CareerStatus.on_duty, es)))
    return result

  @property
  def payment_statistic(self):
    ps = Payment.query.filter_by(status=PaymentStatus.submit, company_id=self.id).all()
    result = dict(un_checked=len(list(ps)))
    return result

  @property
  def order_statistic(self):
    es = self.engineers
    ending_count = len(list(filter(lambda x: x.now_career and x.now_career.s_need_renew_order == 1, es)))
    result = dict(ending_count=ending_count)
    return result

  def now_engineer(self, year_month):  # 获取输入月份在职人员
    if not year_month:
      year_month = int_year_month(get_today())
    if isinstance(year_month, int) and len(str(year_month)) > 6:
      raise NewComException("错误的时间格式", 403)
    careers = Career.query.filter_by(company_id=self.id).all()
    result = []
    if careers:
      for career in careers:
        if career.end:
          if int_year_month(career.start) <= year_month and int_year_month(career.end) >= year_month:
            result.append(career)
        else:
          if int_year_month(career.start) <= year_month:
            result.append(career)
      return result
    return result

  def action_change_status(self, **kwargs):
    now_status = kwargs.get('activate')
    if now_status == self.activate:
      return {}
    self.activate = now_status
    self.save()
    from main.model import Pm, Purchase, CompanyOm
    for p in Pm.query.filter_by(company_id=self.id).all():
      p.activate = now_status
      p.save()
    for p in Purchase.query.filter_by(company_id=self.id).all():
      p.activate = now_status
      p.save()
    for p in CompanyOm.query.filter_by(company_id=self.id).all():
      p.activate = now_status
      p.save()
    return {}

  def action_payment_statistic(self, **kwargs):
    year_month = kwargs.get('year_month')
    wrs = WorkReport.query.filter_by(year_month=year_month, company_id=self.id).all()
    wrs = list(filter(lambda x: not not x.Payment, wrs))
    result = dict(work_reports=[])
    sc = WorkReportWithPayment(many=True)
    result['work_reports'] = sc.dump(wrs)
    PS = PaymentStatus
    statistic = dict()
    statistic['total'] = len(self.now_engineer(year_month))
    statistic['work_report_check_count'] = len(list(filter(lambda x: x.status == AuditStatus.checked, wrs)))
    statistic['work_report_uncheck_count'] = statistic['total'] - statistic['work_report_check_count']
    statistic['payment_send_count'] = len(list(filter(
      lambda x: len(x.Payment) > 0 and not x.Payment[0].status == PS.new,
      wrs)))
    statistic['payment_unsend_count'] = len(list(filter(
      lambda x: len(x.Payment) > 0 and x.Payment[0].status == PaymentStatus.new,
      wrs)))
    statistic['payment_check_count'] = len(
      list(filter(lambda x: len(x.Payment) > 0 and x.Payment[0].status in (PS.checked, PS.payed), wrs)))
    statistic['payment_uncheck_count'] = len(
      list(filter(lambda x: len(x.Payment) > 0 and x.Payment[0].status in (PS.submit, PS.new), wrs)))
    statistic['uncheck_money'] = sum(
      [x.Payment[0].company_pay for x in
       list(filter(lambda x: len(x.Payment) > 0 and x.Payment[0].status in (PS.submit, PS.new), wrs))]
    )
    statistic['checked_money'] = sum(
      [x.Payment[0].company_pay for x in
       list(filter(
         lambda x: len(x.Payment) > 0 and x.Payment[0].status in (PaymentStatus.checked, PaymentStatus.payed),
         wrs))]
    )
    statistic['shift_type'] = self.shift_type
    for w in wrs:
      # todo 未审核工时报告时平台端工时管理此处报错
      if w.Payment and w.Payment[0].status == PaymentStatus.new:
        statistic['need_send'] = 1
    result['statistic'] = statistic
    return result

  def action_unchecked_payments(self, **kwargs):
    ps = Payment.query.filter_by(company_id=self.id, status=PaymentStatus.submit).all()
    result = dict()
    sc = PaymentSimpleSchema(many=True)
    ps = sc.dump(ps)
    for p in ps:
      if str(p['year_month']) in result.keys():
        result[str(p['year_month'])]['payments'].append(p)
      else:
        result[str(p['year_month'])] = \
          {'statistic': {
            "service_fee_rate": self.service_fee_rate,
            "tax_rate": self.tax_rate,
            "finance_rate": self.finance_rate,
            "hr_fee_rate": self.hr_fee_rate,
            "billing_cycle": self.billing_cycle
          },
            'payments': [],  # filter(lambda x: x.year_month == p['year_month'], ps),
            "year_month": dt.date(year=int(p['year_month']) // 100, month=int(p['year_month']) % 100, day=1)
          }
        result[str(p['year_month'])]['payments'].append(p)
    for ym, data in result.items():
      ps = data['payments']
      data['statistic']["count"] = len(ps)
      data['statistic']["company_pay"] = sum([p['company_pay'] for p in ps])
      # data['statistic']["service_fee"] = sum([p['service_fee'] for p in ps])
      data['statistic']["tax"] = sum([p['tax'] for p in ps])
      data['statistic']["hr_fee"] = sum([p['hr_fee'] for p in ps])
      data['statistic']["finance_fee"] = sum([p['finance_fee'] for p in ps])
      data['statistic']["use_hr_count"] = sum([p['use_hr_service'] for p in ps])
      data['statistic']["service_fee"] = sum([p['service_fee'] for p in ps])
      data['statistic']["station_salary"] = sum([p['station_salary'] for p in ps])

    return list(result.values())

  def action_total_payments(self):
    ps = Payment.query.filter(Payment.company_id == self.id,
                  Payment.status.in_([PaymentStatus.submit, PaymentStatus.checked])).all()
    result = dict()
    sc = PaymentSimpleSchema(many=True)
    ps = sc.dump(ps)
    for p in ps:
      if str(p['year_month']) in result.keys():
        result[str(p['year_month'])]['payments'].append(p)
      else:
        result[str(p['year_month'])] = \
          {'statistic': {
            "service_fee_rate": self.service_fee_rate,
            "tax_rate": self.tax_rate,
            "finance_rate": self.finance_rate,
            "hr_fee_rate": self.hr_fee_rate,
            'submit': {},
            'checked': {}
          },
            'payments': [],  # filter(lambda x: x.year_month == p['year_month'], ps),
            "year_month": dt.date(year=int(p['year_month']) // 100, month=int(p['year_month']) % 100,
                        day=1)
          }
        result[str(p['year_month'])]['payments'].append(p)
    for ym, data in result.items():
      ps = data['payments']
      data['statistic']['submit']["count"] = len([p for p in ps if p['status'] == PaymentStatus.submit])
      data['statistic']['submit']["company_pay"] = sum(
        [p['company_pay'] for p in ps if p['status'] == PaymentStatus.submit])
      data['statistic']['submit']["tax"] = sum([p['tax'] for p in ps if p['status'] == PaymentStatus.submit])
      data['statistic']['submit']["hr_fee"] = sum(
        [p['hr_fee'] for p in ps if p['status'] == PaymentStatus.submit])
      data['statistic']['submit']["finance_fee"] = sum(
        [p['finance_fee'] for p in ps if p['status'] == PaymentStatus.submit])
      data['statistic']['submit']["use_hr_count"] = sum(
        [p['use_hr_service'] for p in ps if p['status'] == PaymentStatus.submit])
      data['statistic']['submit']["service_fee"] = sum(
        [p['service_fee'] for p in ps if p['status'] == PaymentStatus.submit])
      data['statistic']['submit']["station_salary"] = sum(
        [p['station_salary'] for p in ps if p['status'] == PaymentStatus.submit])

      data['statistic']['checked']["count"] = len([p for p in ps if p['status'] == PaymentStatus.checked])
      data['statistic']['checked']["company_pay"] = sum(
        [p['company_pay'] for p in ps if p['status'] == PaymentStatus.checked])
      data['statistic']['checked']["tax"] = sum([p['tax'] for p in ps if p['status'] == PaymentStatus.checked])
      data['statistic']['checked']["hr_fee"] = sum(
        [p['hr_fee'] for p in ps if p['status'] == PaymentStatus.checked])
      data['statistic']['checked']["finance_fee"] = sum(
        [p['finance_fee'] for p in ps if p['status'] == PaymentStatus.checked])
      data['statistic']['checked']["use_hr_count"] = sum(
        [p['use_hr_service'] for p in ps if p['status'] == PaymentStatus.checked])
      data['statistic']['checked']["service_fee"] = sum(
        [p['service_fee'] for p in ps if p['status'] == PaymentStatus.checked])
      data['statistic']['checked']["station_salary"] = sum(
        [p['station_salary'] for p in ps if p['status'] == PaymentStatus.checked])
    engineer_count = len(
      list(Career.query.filter(Career.company_id == self.id, Career.status != CareerStatus.finish,
                   Career.status != CareerStatus.entering).all()))
    result['engineer_count'] = engineer_count

    return list(result.values())

  def _before_delete(self):
    if current_user.role != Roles.om:
      raise NewComException('无权进行此操作', 500)
    ps = Position.query.filter_by(company_id=self.id).all()
    for p in ps:
      p.delete()
    cm = CompanyOm.query.filter_by(company_id=self.id).first()
    if cm:
      cm.delete()
    return True


class WorkReportStatistic(BaseActionSchema):
  ModelClass = Company
  _permission_roles = ['company_om', 'purchase', 'om']
  action = 'payment_statistic'

  year_month = fields.Integer()


class UnChekcedPayments(BaseActionSchema):
  ModelClass = Company
  _permission_roles = ['company_om', 'purchase', 'om']
  action = 'unchecked_payments'


class TotalPaymentsSchema(BaseActionSchema):
  ModelClass = Company
  _permission_roles = ['company_om', 'purchase', 'om']
  action = 'total_payments'


class CompanyChangeStatusSchema(BaseActionSchema):
  ModelClass = Company
  _permission_roles = ['om']
  action = 'change_status'

  activate = fields.Integer()


class CompanyOm(User):
  __tablename__ = 'company_om'

  id = db.Column(db.Integer, db.ForeignKey('user.id'), primary_key=True)
  company_id = db.Column(db.Integer, db.ForeignKey('company.id'))
  company = db.relationship('Company', backref='company_om', cascade='delete')

  __mapper_args__ = {
    'polymorphic_identity': 'company_om',
  }

  def __repr__(self):
    return self.real_name if self.real_name else '无名采购'


class PositionPostSchema(PostSchema):
  _permission_roles = ['company_om', 'purchase']

  company_id = fields.Int(required=True)
  name = fields.String(required=True)
  salary_type = fields.Int(required=True)

  class PLPSchema(Schema):
    name = fields.String()
    money = fields.Float()

  position_levels = fields.List(fields.Nested(PLPSchema(unknown=EXCLUDE)))


class PositionWithLevelsSchema(Schema):
  id = fields.Integer(required=True)
  company_id = fields.Int(required=True)
  name = fields.String(required=True)
  salary_type = fields.Int(required=True)
  engineer_count = fields.Integer()

  class PLSchema(Schema):
    id = fields.Integer()
    name = fields.String()
    engineer_count = fields.Integer()
    money = fields.Float()

  position_levels = fields.List(fields.Nested(PLSchema()))


class Position(Base):
  __tablename__ = 'position'
  company_id = db.Column(db.Integer, db.ForeignKey('company.id'), nullable=False)
  name = db.Column(db.String(32))
  salary_type = db.Column(db.Integer)

  offer = db.relationship('Offer', backref='position')
  interview = db.relationship('Interview', backref='position')
  position_levels = db.relationship('PositionLevel', backref='position', cascade='delete')
  engineers = db.relationship('Engineer', backref="position")

  @property
  def engineer_count(self):
    return len(self.engineers)

  def __repr__(self):
    return self.name

  @classmethod
  def post(cls, **kwargs):
    kwargs['company_id'] = current_user.company_id
    schema = PositionPostSchema(many=False, unknown=EXCLUDE)
    data = schema.load(kwargs)
    pls = data.pop('position_levels', [])
    m = cls(**data)
    m.save()
    for ol in pls:
      ol['position_id'] = m.id
      PositionLevel.post(**ol)
    return m


class PositionPutSchema(BasePutSchema):
  _permission_roles = ['om', 'company_om', 'purchase']
  ModelClass = Position

  name = fields.Str()


class PositionLevelPostSchema(PostSchema):
  _permission_roles = ['company_om', 'purchase']

  company_id = fields.Int(required=True)
  position_id = fields.Int(required=True)
  name = fields.String(required=True)
  money = fields.Float(required=True)
  engineer_count = fields.Integer()


class PositionLevel(Base):
  __tablename__ = 'position_level'
  company_id = db.Column(db.Integer, db.ForeignKey('company.id'), nullable=False)
  position_id = db.Column(db.Integer, db.ForeignKey('position.id'), nullable=False)
  name = db.Column(db.String(32))
  money = db.Column(db.Float())
  rank = db.Column(db.Integer)

  engineers = db.relationship('Engineer', backref="position_level")

  def __repr__(self):
    return self.position.name + '-' + self.name

  @classmethod
  def post(cls, **kwargs):
    kwargs['company_id'] = current_user.company_id
    schema = PositionLevelPostSchema(many=False, unknown=EXCLUDE)
    data = schema.load(kwargs)
    m = cls(**data)
    m.save()
    return m

  @property
  def engineer_count(self):
    return len(self.engineers)

  def _before_delete(self):
    os = Offer.query.filter_by(position_id=self.position_id).all()
    for o in os:
      if self.id in [x.id for x in o.position_levels]:
        return False
    cs = Career.query.filter_by(position_level_id=self.id).all()
    if cs:
      return False
    return True

  def position_cal_kwargs(self, salary_type, employ_type):
    cal_kwargs = dict()
    cal_kwargs['salary_type'] = salary_type
    cal_kwargs['employ_type'] = employ_type
    cal_kwargs['service_type'] = '现场'
    cal_kwargs['work_station_fee'] = self.company.work_station_fee
    cal_kwargs['tax_rate'] = self.company.tax_rate
    cal_kwargs['money'] = self.money
    cal_kwargs['work_duration'] = self.company.charging_num * 8
    cal_kwargs['out_duty_days'] = 0
    cal_kwargs['service_fee_rate'] = self.company.service_fee_rate
    cal_kwargs['finance_rate'] = self.company.finance_rate
    cal_kwargs['shift_type'] = self.company.shift_type
    cal_kwargs['charging_num'] = self.company.charging_num
    cal_kwargs['hr_fee_rate'] = self.company.hr_fee_rate
    cal_kwargs['use_hr_service'] = True
    cal_kwargs['ware_fare'] = self.company.ware_fare
    cal_kwargs['tax_free_rate'] = self.company.tax_free_rate
    cal_kwargs['break_up_fee_rate'] = self.company.break_up_fee_rate
    return cal_kwargs

  @classmethod
  def expect_cal_payment(cls, salary_type=None, employ_type=None, money=None, work_duration=None,
               charging_num=None, out_duty_days=None, service_fee_rate=None, tax_rate=None, shift_type=None,
               use_hr_service=None, hr_fee_rate=None, finance_rate=None, work_station_fee=None,
               tax_free_rate=None, ware_fare=None, break_up_fee_rate=None, service_type=None):
    station_salary = 0
    if salary_type == 0:
      # 如果是日结
      duration_salary = money / 8  # 单价按小时
      on_duty_duration = work_duration
      labor_salary = on_duty_duration * duration_salary
    else:
      # 如果月结
      labor_salary = money

    if service_type == '远程':
      if shift_type == 0:
        station_salary = (work_station_fee / 8) * work_duration  # 工位费
      else:
        station_salary = (work_station_fee / 8) * work_duration
      station_salary = station_salary if station_salary < 800 else 800
    company_pay = labor_salary + station_salary  # 人员服务费

    service_fee = service_fee_rate * labor_salary
    tax = tax_rate * company_pay
    if use_hr_service:
      hr_fee = hr_fee_rate * labor_salary
    else:
      hr_fee = 0
    finance_fee = finance_rate * labor_salary
    engineer_income_with_tax = labor_salary * (
        1 - service_fee_rate - tax_rate - finance_rate) - hr_fee  # 人员可支配费用
    tax_fee = engineer_income_with_tax * tax_free_rate
    if employ_type == 0:
      engineer_get = engineer_income_with_tax * (1 - tax_free_rate)
      engineer_tax = 0
      break_up_fee = 0
    else:
      engineer_tax = cal_personal_tax(engineer_income_with_tax - ware_fare)
      _engineer_get = engineer_income_with_tax - ware_fare - engineer_tax
      engineer_get = _engineer_get * break_up_fee_rate
      break_up_fee = _engineer_get * (1 - break_up_fee_rate)  # 离职补偿费

    return dict(company_pay=company_pay, hr_fee=hr_fee, service_fee_rate=service_fee_rate,
          finance_fee=finance_fee, tax=tax, engineer_income_with_tax=engineer_income_with_tax,
          engineer_get=engineer_get, engineer_tax=engineer_tax, break_up_fee_rate=break_up_fee_rate,
          break_up_fee=break_up_fee, out_duty_days=out_duty_days, tax_rate=tax_rate,
          station_salary=station_salary, hr_fee_rate=hr_fee_rate, finance_rate=finance_rate,
          use_hr_service=use_hr_service, tax_free_rate=tax_free_rate, ware_fare=ware_fare,
          service_fee=service_fee, tax_fee=tax_fee)

  # 四种预期收入，命名规则：三位字母，第一位表示salary_type, 第二位表示employ_type
  @property
  def expect_mmm(self):
    # 按月结算员工模式下的预期月收入
    if self.position.salary_type == 1:
      cal_kwargs = self.position_cal_kwargs(1, 1)
      result = self.expect_cal_payment(**cal_kwargs)
      return result['engineer_get']
    return 0

  @property
  def expect_mmd(self):
    if self.position.salary_type == 1:
      # 按月结算牛咖模式下的预期月收入
      cal_kwargs = self.position_cal_kwargs(1, 0)
      result = self.expect_cal_payment(**cal_kwargs)
      return result['engineer_get']
    return 0

  @property
  def expect_mdd(self):
    if self.position.salary_type == 0:
      # 按日结算牛咖模式下的预期日收入
      cal_kwargs = self.position_cal_kwargs(0, 0)
      result = self.expect_cal_payment(**cal_kwargs)
      return result['engineer_get'] / cal_kwargs['charging_num']
    return 0

  @property
  def expect_mdm(self):
    if self.position.salary_type == 0:
      # 按日结算员工模式下的预期日收入
      cal_kwargs = self.position_cal_kwargs(0, 1)
      result = self.expect_cal_payment(**cal_kwargs)
      return result['engineer_get'] / cal_kwargs['charging_num']
    return 0

  @property
  def expect_ddm(self):
    return 0

  @property
  def expect_ddd(self):
    return 0


class PositionLevelPutSchema(BasePutSchema):
  _permission_roles = ['om', 'company_om', 'purchase']
  ModelClass = Position

  name = fields.Str()
  money = fields.Float()


class ProjectStatus(BaseStatus):
  open = 1
  finish = 0


class ProjectPostSchema(PostSchema):
  _permission_roles = ['om', 'company_om', 'purchase']

  company_id = fields.Int(required=True)
  name = fields.Str(required=True)


class ProjectWithPms(Schema):
  class PMS(Schema):
    id = fields.Integer()
    real_name = fields.String()
    engineers_in_project_count = fields.Integer()

  name = fields.Str()
  id = fields.Integer()
  engineer_count = fields.Integer()
  pms_count = fields.Integer()
  pms = fields.List(fields.Nested(PMS(many=False, unknown=EXCLUDE)))


class ProjectWithPmsEngineers(Schema):
  class PMS(Schema):
    id = fields.Integer()
    real_name = fields.String()
    engineers_in_project_count = fields.Integer()
    audit_in_project_count = fields.Integer()
    interview_in_project_count = fields.Integer()
    enter_in_project_count = fields.Integer()

    class ES(Schema):
      id = fields.Integer()
      real_name = fields.String()
      phone = fields.String()
      email = fields.String()

      class CS(Schema):
        start = fields.Date()
        interview_id = fields.Integer()
        use_hr_service = fields.Integer()
        salary_type = fields.Integer()

        class PLS(Schema):
          position = fields.String()
          name = fields.String()
          money = fields.Float()

        position_level = fields.Nested(PLS(many=False, unknown=EXCLUDE))

      now_career = fields.Nested(CS(many=False, unknown=EXCLUDE))

    engineers_in_project = fields.List(fields.Nested(ES(many=False, unknown=EXCLUDE)))
    offers_in_project_count = fields.Integer()

  name = fields.Str()
  id = fields.Integer()
  engineer_count = fields.Integer()
  pms_count = fields.Integer()
  pms_engineers = fields.List(fields.Nested(PMS(many=False, unknown=EXCLUDE)))


class Project(Base):
  __tablename__ = 'project'

  company_id = db.Column(db.Integer, db.ForeignKey('company.id'), nullable=False)
  name = db.Column(db.String(32))
  status = db.Column(db.Integer, default=ProjectStatus.open, index=True)

  interview = db.relationship('Interview', backref='project')
  offer = db.relationship('Offer', backref='project')
  audit = db.relationship('Audit', backref='project')
  engineers = db.relationship('Engineer', backref='project')
  pms = db.relationship('Pm', secondary='pm_project', backref='project')

  def __repr__(self):
    return self.name

  @classmethod
  def post(cls, **kwargs):
    if current_user.role in ['company_om', 'purchase']:
      kwargs['company_id'] = current_user.company_id
    schema = ProjectPostSchema(many=False, unknown=EXCLUDE)
    data = schema.load(kwargs)
    m = cls(**data)
    m.save()
    return m

  @property
  def engineer_count(self):
    return len(self.engineers)

  def action_add_pm(self, **kwargs):
    pm_id = int(kwargs.get('pm_id'))
    _pm = Pm.query.filter_by(id=pm_id).first()
    if pm_id not in [p.id for p in self.pms]:
      self.pms.append(_pm)
      self.save()
    return {}

  def action_remove_pm(self, **kwargs):
    pm_id = int(kwargs.get('pm_id'))
    _pm = Pm.query.filter_by(id=pm_id).first()
    es = self.engineers
    for e in es:
      if e.pm_id == pm_id:
        raise NewComException('尚有未转出到其他项目经理下的工程师。', 501)
    for o in self.offer:
      if o.pm_id == pm_id:
        raise NewComException('尚有需求未转移至其他项目经理之下。请先交接业务。', 501)
    self.pms.remove(_pm)
    self.save()

  def action_change_pm(self, **kwargs):
    project_id = self.id
    old_pm_id = int(kwargs.get('old_pm_id'))
    new_pm_id = int(kwargs.get('new_pm_id'))
    es = self.engineers
    for e in es:
      if e.pm_id == old_pm_id:
        raise NewComException('尚有未转出到其他项目经理下的工程师。', 501)

    sql = 'update {} set pm_id = {}  where pm_id={} and project_id={}'
    # offer
    db.session.execute(sql.format('offer', new_pm_id, old_pm_id, project_id))
    # interview
    db.session.execute(sql.format('interview', new_pm_id, old_pm_id, project_id))
    # audit
    db.session.execute(sql.format('audit', new_pm_id, old_pm_id, project_id))
    # daily_logs
    db.session.execute(sql.format('daily_log', new_pm_id, old_pm_id, project_id))
    # enter_project
    db.session.execute(sql.format('enter_project', new_pm_id, old_pm_id, project_id))

    db.session.execute(sql.format('payment', new_pm_id, old_pm_id, project_id))

    try:
      db.session.commit()
    except Exception as e:
      db.session.rollback()
      raise NewComException('更换项目经理失败。', 501)

  @property
  def pms_engineers(self):
    """
    某个项目下的所有项目经理，和项目经理下属于这个项目的工程师
    :return:
    """
    es = self.engineers

    for _pm in self.pms:
      engineers_in_project = list(filter(lambda x: x.pm_id == _pm.id, es))
      setattr(_pm, 'engineers_in_project', engineers_in_project)
      setattr(_pm, 'engineers_in_project_count', len(engineers_in_project))
      offers_in_project = list(filter(lambda x: x.pm_id == _pm.id, self.offer))
      setattr(_pm, 'offers_in_project_count', len(offers_in_project))
      audit_in_project = list(filter(lambda x: x.pm_id == _pm.id and x.status == AuditStatus.submit, self.audit))
      setattr(_pm, 'audit_in_project_count', len(audit_in_project))
      interview_in_project = list(
        filter(lambda x: x.pm_id == _pm.id and abs(x.status <= InterviewStatus.enter_project_pass),
             self.interview))
      setattr(_pm, 'interview_in_project_count', len(interview_in_project))
      enter_in_project = list(
        EnterProject.query.filter(EnterProject.pm_id == _pm.id, EnterProject.project_id == self.id,
                      EnterProject.status <= EnterProjectStatus.file_pm_agree).all())
      setattr(_pm, 'enter_in_project_count', len(enter_in_project))
    return self.pms


class ProjectPutSchema(BasePutSchema):
  _permission_roles = ['om', 'company_om', 'purchase']
  ModelClass = Project
  name = fields.Str()


class ProjectAddPmSchema(BaseActionSchema):
  ModelClass = Project
  _permission_roles = ['purchase', 'om', 'company_om']
  action = 'add_pm'

  pm_id = fields.Integer()


class ProjectRemovePmSchema(ProjectAddPmSchema):
  action = 'remove_pm'


class ProjectChangePmSchema(BaseActionSchema):
  #
  ModelClass = Project
  _permission_roles = ['purchase', 'company_om']
  action = 'change_pm'

  project_id = fields.Integer()
  new_pm_id = fields.Integer()
  old_pm_id = fields.Integer()


class OfferPositionLevel(db.Model):
  __tablename__ = 'offer_position_levels'
  offer_id = db.Column(db.Integer, db.ForeignKey('offer.id'), primary_key=True)
  position_level_id = db.Column(db.Integer, db.ForeignKey('position_level.id'), primary_key=True)


class OfferPostSchema(PostSchema):
  _permission_roles = ['om', 'company_om', 'purchase']

  name = fields.String(required=True)
  work_place = fields.String(required=True)
  salary_type = fields.Integer()
  company_id = fields.Integer(required=True)
  project_id = fields.Int(required=True)
  pm_id = fields.Integer(required=True)
  position_id = fields.Integer(required=True)
  position_levels = fields.List(fields.Integer(required=True))
  amount = fields.Integer(required=True)
  description = fields.String(required=True)


class OfferDetailSchema(Schema):
  class NIS(Schema):
    id = fields.Str()
    name = fields.Str()

  class PSTS(NIS):
    class PSS(Schema):
      id = fields.Str()
      name = fields.Str()
      money = fields.Float()

    position_levels = fields.List(fields.Nested(PSS(many=False)))

  class PLS(NIS):
    money = fields.Float()

  class PmS(Schema):
    id = fields.Str()
    real_name = fields.Str()

  class SS(Schema):
    demand_amount = fields.Int()
    cv_push_amount = fields.Int()
    cv_pass_amount = fields.Int()
    interview_pass_amount = fields.Int()
    entry_amount = fields.Int()
    cv_push_rate = fields.Float()
    cv_pass_rate = fields.Float()
    interview_pass_rate = fields.Float()
    entry_rate = fields.Float()

  updated = fields.DateTime()
  created = fields.DateTime()
  name = fields.String(required=True)
  work_place = fields.String(required=True)
  salary_type = fields.Integer()
  company_id = fields.Integer(required=True)
  project_id = fields.Int(required=True)
  pm_id = fields.Integer(required=True)
  position = fields.Nested(PSTS(many=False, unknown=EXCLUDE))
  pm = fields.Nested(PmS(many=False, unknown=EXCLUDE))
  project = fields.Nested(NIS(many=False, unknown=EXCLUDE))
  position_levels = fields.List(fields.Nested(PLS(many=False, unknown=EXCLUDE)))
  amount = fields.Integer(required=True)
  description = fields.String(required=True)
  statistics = fields.Nested(SS(many=False))

  


class Offer(Base):
  __tablename__ = 'offer'

  company_id = db.Column(db.Integer, db.ForeignKey('company.id'))
  project_id = db.Column(db.Integer, db.ForeignKey('project.id'))
  pm_id = db.Column(db.Integer, db.ForeignKey('pm.id'))
  name = db.Column(db.String(64))
  position_id = db.Column(db.Integer, db.ForeignKey('position.id'))
  position_levels = db.relationship('PositionLevel', secondary='offer_position_levels', backref="offer")
  work_place = db.Column(db.String(128), doc="工作地点")

  amount = db.Column(db.Integer, doc="需求人数")
  description = db.Column(db.Text, nullable=False, doc="职位描述")
  status = db.Column(db.Integer, index=True, doc="需求状态")
  shut_down_reason = db.Column(db.String(256))
  shut_down_note = db.Column(db.String(256))
  salary_type = db.Column(db.Integer)
  # cobra-55555
  unit_price = db.Column(db.Integer)

  interview = db.relationship('Interview', backref='offer')
  career = db.relationship('Career', backref='offer')
  position_name = db.Column(db.String(64), doc="职位名称")
  position_type = db.Column(db.String(64), doc="职位类型")
  service_type = db.Column(db.String(64), doc="服务方式")
  experience = db.Column(db.String(64), doc="经验")
  education = db.Column(db.String(64), doc="学历")
  # need_resume = db.Column(db.Boolean, doc="是否需要代找简历")
  need_resume = db.Column(db.Integer, doc="是否需要代找简历")
  hiring_schedule = db.relationship('HiringSchedule', backref="offer")
  offer_data = db.relationship('OfferData', backref="offer")
  offer_schedule_data = db.relationship('OfferScheduleData', backref="offer")

  def __init__(self, *args, **kwargs):
    super(Offer, self).__init__(*args, **kwargs)
    self._interviews = None

  def __repr__(self):
    return self.name

  @classmethod
  def post(cls, **kwargs):
    if 'mode' in kwargs.keys():
      if kwargs['mode'] == 'offerData':
        offerdata = OfferData()
        offerdata.engineer_id = kwargs['engineer_id']
        offerdata.offer_id = kwargs['offer_id']
        offerdata.created = dt.datetime.now()
        offerdata.save()

        today = dt.date.today().strftime('%Y-%m-%d')
        offerscdData = OfferScheduleData.query.filter_by(offer_id=kwargs['offer_id'], date=today).first()
        if offerscdData is not None:
          offerscdData.resume_collection_num = offerscdData.resume_collection_num + 1
          offerscdData.update()
        else:
          offerscdData = OfferScheduleData()
          offerscdData.offer_id = kwargs['offer_id']
          offerscdData.date = today
          offerscdData.resume_collection_num = 1
          offerscdData.written_pass_num = 0
          offerscdData.interview_pass_num = 0
          offerscdData.offer_pass_num = 0
          offerscdData.save()

      m = cls()
    else:
      if current_user.role in ['company_om', 'purchase']:
        kwargs['company_id'] = current_user.company_id

      # if kwargs["amount"] == '0':
      #   raise NewComException("需求人数不能为0", 403)

      schema = OfferPostSchema(many=False, unknown=EXCLUDE)

      # data = schema.load(kwargs)
      data = kwargs
      pls = []

      # for pl_id in data['position_levels']:
      #   pls.append(PositionLevel.query.filter_by(id=pl_id).first())
      data['position_levels'] = pls
      m = cls(**data)
      m.status = OfferStatus.open
      m.save()
    return m


  @property
  def cv_push_amount(self):
    return len(self.interview)

  @property
  def cv_pass_amount(self):
    return len(list(filter(
      lambda x: abs(x.status) > 2,
      self.interview)))

  @property
  def interview_pass_amount(self):
    return len(list(filter(
      lambda x: abs(x.status) > 8,
      self.interview
    )))

  @property
  def entry_amount(self):
    return len(list(filter(
      lambda x: abs(x.status) == 15 and x.interview_id is not None,
      list(EnterProject.query.filter_by(offer_id=self.id).all())
    )))

  @property
  def entry_interviews(self):
    return list(filter(lambda x: x.status > 16, self.interview))

  def action_modify(self, **kwargs):
    if 'amount' in kwargs:
      if kwargs['amount'] < self.entry_amount:
        raise NewComException('不能将需求数量修改的少于当前入职数量', 500)
      if kwargs['amount'] < self.amount:
        raise NewComException('需求人数不可调少', 500)
      if kwargs['amount'] > self.amount:
        kwargs['status'] = OfferStatus.open
    pls = kwargs.get('position_levels', [])
    if pls:
      pls = PositionLevel.query.filter(PositionLevel.id.in_(pls)).all()
    kwargs['position_levels'] = pls

    self.update(**kwargs)

  def action_shut_down(self, shut_down_reason, shut_down_note=None):
    # 检查不适合关闭的原因
    self.status = OfferStatus.closed
    self.shut_down_note = shut_down_note
    self.shut_down_reason = shut_down_reason
    self.save()

  @property
  def statistics(self):
    return OfferStatistics(self)

  def delete(self):
    if self.entry_amount > 0:
      raise NewComException('已有入职的需求不可删除.', 500)
    super().delete()

  # getting detail information of the offer
  # cobra-55555 -20-04-17
  @classmethod
  def get_offer_detail(self,  **kwargs):
    result = {}
    o_id = kwargs.get('id')
    offer = self.query.filter_by(id=o_id).first()
    company_list = Company.query.filter_by(id=offer.company_id).all()
    if len(company_list) > 0:
      company = company_list[0]
      result['position'] = str(offer.name)
      result['position_type'] = str(offer.position_type)
      result['service_method'] = str(offer.service_type)
      result['company'] = str(company.name)
      result['created'] = str(offer.created)
      result['work_space'] = str(offer.work_place)
      result['status'] = str(offer.status)
      result['experience'] = str(offer.experience)
      result['education'] = str(offer.education)
      result['description'] = str(offer.description)
      result['need_resume'] = offer.need_resume
      result['unit_price'] = offer.unit_price
    else:
      result['position'] = ''
      result['position_type'] = ''
      result['service_method'] = ''
      result['company'] = ''
      result['created'] = ''
      result['work_space'] = ''
      result['status'] = ''
      result['experience'] = ''
      result['education'] = ''
      result['description'] = ''
      result['need_resume'] = ''
      result['unit_price'] = ''
    
    return result
  
  # getting resume data of the offer
  # cobra-55555-setting --- i need to ask the logic to the client
  @classmethod
  def get_offer_data_list(self, **kwargs):
    result = []
    o_id = kwargs.get('id')
    offer = self.query.filter_by(id=o_id)[0]
    offer_data_list = OfferData.query.filter_by(offer_id = offer.id).order_by(OfferData.created.desc()).all()

    for offer_data_item in offer_data_list:
      row = {}
      row['name'] = ''
      row['totalmark'] = ''
      engineer_list = Engineer.query.filter_by(id = offer_data_item.engineer_id).all()

      if len(engineer_list) > 0:
        engineer = engineer_list[0]

        row['name'] = engineer.real_name
        totalmark = 0
        if (offer_data_item.written_score is not None):
          totalmark = totalmark + int(offer_data_item.written_score)
        if (offer_data_item.Interview_score is not None):
          totalmark = totalmark + int(offer_data_item.Interview_score)
          
        if totalmark is not None:
          row['totalmark'] = str(totalmark)
        else:
          row['totalmark'] = '0'

        written_result = offer_data_item.written_score
        row['written_result'] = str(written_result)
        interview_result = offer_data_item.Interview_score
        row['interview_result'] = str(interview_result)
        salery = engineer.s_money
        row['salery'] = str(salery)
        education = engineer.s_education
        row['education'] = str(education)
        row['engineer_id'] = engineer.id

        if row['name'] is not '':
          result.append(row)

    return result

  # getting count tracking data
  @classmethod
  def get_count_track(self, **kwargs):
    result_data = []
    o_id = kwargs.get('id')
    offer = self.query.filter_by(id=o_id).first()

    result = {}
    result['re_total'] = 0
    result['wp_total'] = 0
    result['ip_total'] = 0
    result['op_total'] = 0
    
    today = dt.date.today()
    today_date = today.strftime("%Y-%m-%d")

    # changed cobra-55555 -20-05-01
    # group_by(OfferScheduleData.date).order_by(OfferScheduleData.date.asc()).all()
    offer_schedule_data_list = OfferScheduleData.query. \
      filter(OfferScheduleData.offer_id==o_id). \
      order_by(OfferScheduleData.date.asc()).all()

    if len(offer_schedule_data_list) > 0:
      for item in offer_schedule_data_list:
        cur_date = item.date

        if cur_date > today:
          break
        else:
          if item.date == today:
            result['re'] = item.resume_collection_num
            result['wp'] = item.written_pass_num
            result['ip'] = item.interview_pass_num
            result['op'] = item.offer_pass_num
          elif cur_date < today:
            result['re'] = 0
            result['wp'] = 0
            result['ip'] = 0
            result['op'] = 0

          result['re_total'] = result['re_total'] + item.resume_collection_num
          result['wp_total'] = result['wp_total'] + item.written_pass_num
          result['ip_total'] = result['ip_total'] + item.interview_pass_num
          result['op_total'] = result['op_total'] + item.offer_pass_num
    else:
      result['re'] = 0
      result['wp'] = 0
      result['ip'] = 0
      result['op'] = 0

    result1 = {}
    result2 = {}
    result3 = {}
    result4 = {}

    result1['today'] = result['re']
    result1['total'] = result['re_total']
    result1['type'] = '简历收集'
    result_data.append(result1)
    result2['today'] = result['wp']
    result2['total'] = result['wp_total']
    result2['type'] = '笔试通过'
    result_data.append(result2)
    result3['today'] = result['ip']
    result3['total'] = result['ip_total']
    result3['type'] = '面试完成'
    result_data.append(result3)
    result4['today'] = result['op']
    result4['total'] = result['op_total']
    result4['type'] = '需求满足'
    result_data.append(result4)

    return result_data
  
  # getting chat data
  @classmethod
  def get_chat_information(self, **kwargs):
    result_data = {}
    result = {}
    result1 = {}
    o_id = kwargs.get('id')
    offer = self.query.filter_by(id=o_id).first()

    result['re'] = []  # resume_collection_num data
    result['wp'] = []  # written_pass_num data
    result['ip'] = []  # interview_pass_num data
    result['op'] = []  # offer_pass_num data

    result1['re'] = []  # resume_collection_num data
    result1['wp'] = []  # written_pass_num data
    result1['ip'] = []  # interview_pass_num data
    result1['op'] = []  # offer_pass_num data

    row_tr = 0
    row_tw = 0
    row_ti = 0
    row_to = 0

    today = dt.date.today()
    limit_date = today - dt.timedelta(days=300)  # getting only data of recent 14 days
    # offer_schedule_data_list = OfferScheduleData.query.filter(OfferScheduleData.offer_id==o_id).\
    #     group_by(OfferScheduleData.date).order_by(OfferScheduleData.id.asc()).all()
    offer_schedule_data_list = OfferScheduleData.query.filter(OfferScheduleData.offer_id==o_id).\
        order_by(OfferScheduleData.id.asc()).all()
    
    for item in offer_schedule_data_list:
      cur_date = item.date

      if cur_date > today:
        continue

      row_r = {}
      row_w = {}
      row_i = {}
      row_o = {}

      row_r1 = {}
      row_w1 = {}
      row_i1 = {}
      row_o1 = {}

      date_cur_sql = cur_date.strftime('%Y-%m-%d')
      date_cur_str = cur_date.strftime('%Y/%m/%d')

      row_r['x'] = date_cur_str
      row_w['x'] = date_cur_str
      row_i['x'] = date_cur_str
      row_o['x'] = date_cur_str

      row_r1['x'] = date_cur_str
      row_w1['x'] = date_cur_str
      row_i1['x'] = date_cur_str
      row_o1['x'] = date_cur_str

      row_r1['y'] = item.resume_collection_num
      row_w1['y'] = item.written_pass_num
      row_i1['y'] = item.interview_pass_num
      row_o1['y'] = item.offer_pass_num

      row_tr = row_tr + item.resume_collection_num
      row_tw = row_tw + item.written_pass_num
      row_ti = row_ti + item.interview_pass_num
      row_to = row_to + item.offer_pass_num

      row_r['y'] = row_tr
      row_w['y'] = row_tw
      row_i['y'] = row_ti
      row_o['y'] = row_to
      
      if cur_date >= limit_date:
        result['re'].append(row_r)
        result['wp'].append(row_w)
        result['ip'].append(row_i)
        result['op'].append(row_o)

        result1['re'].append(row_r1)
        result1['wp'].append(row_w1)
        result1['ip'].append(row_i1)
        result1['op'].append(row_o1)
    
    if(len(result['re']) < 8 and len(result['re']) > 0):
      result['re'].insert(0, {'x': '', 'y': 0})
      result['re'].append({'x': ' ', 'y': 0})
      result['wp'].insert(0, {'x': ' ', 'y': 0})
      result['wp'].append({'x': ' ', 'y': 0})
      result['ip'].insert(0, {'x': ' ', 'y': 0})
      result['ip'].append({'x': ' ', 'y': 0})
      result['op'].insert(0, {'x': ' ', 'y': 0})
      result['op'].append({'x': ' ', 'y': 0})

      result1['re'].insert(0, {'x': ' ', 'y': 0})
      result1['re'].append({'x': ' ', 'y': 0})
      result1['wp'].insert(0, {'x': ' ', 'y': 0})
      result1['wp'].append({'x': ' ', 'y': 0})
      result1['ip'].insert(0, {'x': ' ', 'y': 0})
      result1['ip'].append({'x': ' ', 'y': 0})
      result1['op'].insert(0, {'x': ' ', 'y': 0})
      result1['op'].append({'x': ' ', 'y': 0})

    result_data['total_data'] = result
    result_data['per_data'] = result1
    return result_data

  # getting interview data
  @classmethod
  def get_interview_pass_data(self, **kwargs):
    result = []
    o_id = kwargs.get('id')
    offer = self.query.filter_by(id=o_id).first()

    # cobra-55555 test --setting
    i = 1
    interview_list = Interview.query.filter_by(offer_id=o_id)
    for interview_item in interview_list:
      engineer = Engineer.query.filter_by(id=interview_item.engineer_id).first()
      if engineer is not None:
        career = Career.query.filter_by(id=engineer.now_career_id).first()
        if career is not None:
          row = {}
          row['name'] =career.real_name

          # setting
          if i < 5:
            row['online'] = True
          else:
            row['online'] = False
          result.append(row)
          i = i + 1
    
    result1 = []
    i = 0
    page = []
    for item in result:
      page.append(item)
      i = i + 1
      if i is 7:
        add_page = []
        for page_item in page:
          add_page.append(page_item)

        result1.append(add_page)
        i = 0
        page.clear()

    if len(page) > 0:
      result1.append(page)

    result0 = {}
    result0['total'] = len(result)
    # setting
    if len(result) > 4:
      result0['online'] = 4
    else:
      result0['online'] = 0

    return result0, result1

  # getting person data
  @classmethod
  def get_offer_person_data(self, **kwargs):
    items = []
    o_id = kwargs.get('id')
    offer = self.query.filter_by(id=o_id).first()

    data = []
    offer_data = OfferData.query.filter_by(offer_id=offer.id).all()
    i = 1
    for od_item in offer_data:
      person_data = {}
      engineer = Engineer.query.filter_by(id=od_item.engineer_id).first()
      if engineer is not None:
        career = Career.query.filter_by(id=engineer.now_career_id).first()
        if career is not None and career.real_name is not None:
          person_data['email'] = engineer.email
          person_data['living_address'] = engineer.living_address
          person_data['computer_level'] = engineer.computer_level
          person_data['work_salary'] = engineer.work_salary
          person_data['expect_jstatus'] = engineer.expect_jstatus
          person_data['phone'] = engineer.phone
          person_data['hukou_address'] = engineer.hukou_address
          person_data['work_location'] = engineer.work_location
          person_data['expect_jlocation'] = engineer.expect_jlocation
          person_data['gender'] = engineer.gender
          person_data['id_card'] = engineer.id_card
          person_data['work_company'] = engineer.work_company
          # person_data['salery'] = engineer.s_money
          person_data['expect_salary'] = engineer.expect_salary
          person_data['age'] = engineer.age
          person_data['race'] = engineer.race
          person_data['work_industry'] = engineer.work_industry
          person_data['expect_industry'] = engineer.expect_industry
          if engineer.age is not None:
            person_data['birthday'] = engineer.birthday.strftime('%Y-%m-%d')
          else:
            person_data['birthday'] = ''
          person_data['english_level'] = engineer.english_level
          person_data['work_status'] = engineer.work_status
          person_data['expect_time'] = engineer.expect_time

#-------------PART I COMPLETED ---------------------


          person_data['name'] = engineer.real_name
          writteninterviewinfo = WrittenInterviewInfo.query.filter_by(engineer_id=engineer.id).first()
          if writteninterviewinfo is not None:
            person_data['single_choice_score'] = writteninterviewinfo.single_choice_score
            person_data['written_rank'] = writteninterviewinfo.written_rank
            person_data['interview_rank'] = writteninterviewinfo.interview_rank
            #邮箱
            person_data['problem_score'] = writteninterviewinfo.problem_score
            person_data['interview_score'] = writteninterviewinfo.interview_score
            person_data['interview_time'] = writteninterviewinfo.interview_time
            if writteninterviewinfo.recommend_time is not None:
              person_data['recommend_time'] = writteninterviewinfo.recommend_time.strftime('%Y-%m-%d')
            else:
              person_data['recommend_time'] = ''
            person_data['design_problem_score'] = writteninterviewinfo.design_problem_score
            person_data['interview_num'] = writteninterviewinfo.interview_num
            person_data['written_score'] = writteninterviewinfo.written_score
            person_data['written_time'] = writteninterviewinfo.written_time
            person_data['interview_skill_score'] = writteninterviewinfo.interview_skill_score
            person_data['written_num'] = writteninterviewinfo.written_num
            person_data['written_cut_num'] = writteninterviewinfo.written_cut_num
            person_data['interview_quality_score'] = writteninterviewinfo.interview_quality_score


            person_data['recommend_person'] = writteninterviewinfo.recommend_person
            person_data['written_total_num'] = writteninterviewinfo.written_total_num
            person_data['thought_score'] = writteninterviewinfo.thought_score
            if writteninterviewinfo.written_start is not None:
              person_data['written_start'] = writteninterviewinfo.written_start.strftime('%Y-%m-%d')
            else:
              person_data['written_start'] = ''
            if writteninterviewinfo.written_end is not None:
              person_data['written_end'] = writteninterviewinfo.written_end.strftime('%Y-%m-%d')
            else:
              person_data['written_end'] = ''

            if writteninterviewinfo.interview_start is not None:
              person_data['interview_start'] = writteninterviewinfo.interview_start.strftime('%Y-%m-%d')
            else:
              person_data['interview_start'] = ''
            if writteninterviewinfo.interview_end is not None:
              person_data['interview_end'] = writteninterviewinfo.interview_end.strftime('%Y-%m-%d')
            else:
              person_data['interview_end'] = ''
          else:
            person_data['single_choice_score'] = ''
            person_data['written_rank'] = ''
            person_data['interview_rank'] = ''
            person_data['problem_score'] = ''
            person_data['interview_score'] = ''
            person_data['interview_time'] = ''
            person_data['recommend_time'] = ''
            person_data['design_problem_score'] = ''
            person_data['interview_num'] = ''
            person_data['written_score'] = ''
            person_data['written_time'] = ''
            person_data['interview_skill_score'] = ''
            person_data['written_num'] = ''
            person_data['written_cut_num'] = ''
            person_data['interview_quality_score'] = ''


            person_data['recommend_person'] = ''
            person_data['written_total_num'] = ''
            person_data['thought_score'] = ''
            person_data['written_start'] = ''
            person_data['written_end'] = ''
            person_data['interview_start'] = ''
            person_data['interview_end'] = ''


#-------------PART II COMPLETED ---------------------


          education = Education.query.filter_by(engineer_id=engineer.id).first()
          if education is not None:
            if education.start_date is not None:
              person_data['education_start'] = education.start_date.strftime('%Y-%m-%d')
            else:
              person_data['education_start'] = ''
            person_data['edu_gpa'] = education.edu_gpa
            if education.end_date is not None:
              person_data['education_end'] = education.end_date.strftime('%Y-%m-%d')
            else:
              person_data['education_end'] = ''
            if education.edu_major is not None:
              person_data['education_major'] = education.edu_major
            else:
              person_data['education_major'] = ''
            if education.degree is not None:
              person_data['education_degree'] = education.degree
            else:
              person_data['education_degree'] = ''
            if education.school is not None:
              person_data['education_school'] = education.school
            else:
              person_data['education_school'] = ''
            
            if education.edu_recruit is not None:
              person_data['edu_recruit'] = education.edu_recruit
            else:
              person_data['edu_recruit'] = ''

            if education.edu_college_type is not None:
              person_data['edu_college_type'] = education.edu_college_type
            else:
              person_data['edu_college_type'] = ''

          else:
            person_data['education_start'] = ''
            person_data['edu_gpa'] = ''
            person_data['education_end'] = ''
            person_data['education_major'] = ''
            person_data['education_degree'] = ''
            person_data['education_school'] = ''
            person_data['edu_recruit'] = ''

            person_data['edu_college_type'] = ''
          

#-------------PART III COMPLETED ---------------------

          jobexperience = JobExperience.query.filter_by(engineer_id=engineer.id).first()
          if jobexperience is not None:
            if jobexperience.start_date is not None:
              person_data['start_date'] = jobexperience.start_date.strftime('%Y-%m-%d')
            else:
              person_data['start_date'] = ''
            person_data['company_desc'] = jobexperience.company_desc
            person_data['company_nature'] = jobexperience.company_nature
            person_data['duaration'] = jobexperience.duaration
            if jobexperience.end_date is not None:
              person_data['end_date'] = jobexperience.end_date.strftime('%Y-%m-%d')
            else:
              person_data['end_date'] = ''
            person_data['industry'] = jobexperience.industry
            person_data['staff'] = jobexperience.staff
            person_data['capacity'] = jobexperience.capacity
            person_data['company_name'] = jobexperience.company_name
            person_data['position'] = jobexperience.position
            person_data['report_to'] = jobexperience.report_to
            person_data['content'] = jobexperience.content
            person_data['company_size'] = jobexperience.company_size
            person_data['dept'] = jobexperience.dept
            person_data['why_leave'] = jobexperience.start_date


            person_data['nature'] = jobexperience.nature
            person_data['location'] = jobexperience.location
          else:
            person_data['start_date'] = ''
            person_data['end_date'] = ''
            person_data['company_name'] = ''
            person_data['company_nature'] = ''
            person_data['company_size'] = ''
            person_data['company_desc'] = ''
            person_data['industry'] = ''
            person_data['position'] = ''
            person_data['dept'] = ''
            person_data['nature'] = ''
            person_data['staff'] = ''
            person_data['report_to'] = ''
            person_data['location'] = ''
            person_data['why_leave'] = ''
            person_data['duaration'] = ''
            person_data['capacity'] = ''
            person_data['content'] = ''

#-------------PART IV COMPLETED ---------------------   

          projectexp = ProjectExperience.query.filter_by(engineer_id=engineer.id).first()
          if projectexp is not None:
            if projectexp.start_date is not None:
              person_data['pro_start_date'] = projectexp.start_date.strftime('%Y-%m-%d')
            else:
              person_data['pro_start_date'] = ''
            person_data['pro_position'] = projectexp.position
            if projectexp.end_date is not None:
              person_data['pro_end_date'] = projectexp.end_date.strftime('%Y-%m-%d')
            else:
              person_data['pro_end_date'] = ''
            person_data['pro_content'] = projectexp.content
            person_data['pro_name'] = projectexp.name
            person_data['pro_resp'] = projectexp.resp
            person_data['pro_company_name'] = projectexp.company_name
          else:
            person_data['pro_start_date'] = ''
            person_data['pro_end_date'] = ''
            person_data['pro_name'] = ''
            person_data['pro_company_name'] = ''
            person_data['pro_position'] = ''
            person_data['pro_content'] = ''
            person_data['pro_resp'] = ''

#-------------PART V COMPLETED ---------------------   
          ability = Ability.query.filter_by(engineer_id=engineer.id).first()
          if ability is not None:
            person_data['skill_name'] = ability.name
            person_data['skill_level'] = ability.level
            person_data['skill_time'] = ability.skills_time
          else:
            person_data['skill_name'] = ''
            person_data['skill_level'] = ''
            person_data['skill_time'] = ''
#-------------PART VI COMPLETED ---------------------

          lang = Language.query.filter_by(engineer_id=engineer.id).first()
          if lang is not None:
            person_data['lang_name'] = lang.name
            person_data['lang_level'] = lang.level
            person_data['lang_read_write'] = lang.read_write
            person_data['lang_listen_speak'] = lang.listen_speak
          else:
            person_data['lang_name'] = ''
            person_data['lang_level'] = ''
            person_data['lang_read_write'] = ''
            person_data['lang_listen_speak'] = ''   

          langcert = Langcert.query.filter_by(engineer_id=engineer.id).first()
          if langcert is not None:
            person_data['lang'] = langcert.lang
            person_data['langcert_name'] = langcert.name
            person_data['langcert_score'] = langcert.score
          else: 
            person_data['lang'] = ''
            person_data['langcert_name'] = ''
            person_data['langcert_score'] = ''  

#-------------PART VII COMPLETED ---------------------        

          person_data['work_location'] = engineer.career[0].work_place
          person_data['education'] = engineer.s_education

          person_data['work_position'] = engineer.work_position
          person_data['work_location'] = engineer.work_location
          person_data['work_year'] = engineer.work_year
          
          if career.start is not None:
            person_data['careerStart'] = career.start.strftime('%Y-%m-%d')
          else:
            person_data['careerStart'] = ''
          if career.end is not None:
            person_data['careerEnd'] = career.end.strftime('%Y-%m-%d')
          else:
            person_data['careerEnd'] = ''

          company = Company.query.filter_by(id=career.company_id).first()
          if company is not None:
            person_data['companyName'] = company.name
          else:
            person_data['companyName'] = ''
          
          position = Position.query.filter_by(id=career.position_id).first()
          if position is not None:
            person_data['positionName'] = position.name
          else:
            person_data['positionName'] = ''
          
          person_data['work_content'] = career.work_content

          resign = Resign.query.filter_by(career_id=career.id).first()
          if resign is not None:
            person_data['resignReason'] = resign.reason
          else:
            person_data['resignReason'] = ''

          project = Project.query.filter_by(id=career.project_id).first()
          if project is not None:
            person_data['projectName'] = project.name
          else:
            person_data['projectName'] = ''

          for key in person_data:
            if person_data[key] is None:
              person_data[key] = ''
          
          data.append(person_data)
          items.append(i)
          i = i + 1
      
    return items, data

  # getting statistics modal data
  @classmethod
  def get_statistics_modal_data(self, **kwargs):
    result = {}
    o_id = kwargs.get('id')
    offer = self.query.filter_by(id=o_id).first()

    offer_data_list = OfferData.query.filter_by(offer_id=offer.id).order_by(OfferData.created).all()

    if len(offer_data_list) > 0:
      start_datetime = offer_data_list[0].created
      totalmark_w = 0
      totalmark_i = 0
      interviewWeeklyData = []
      w = 1
      count = 0

      for od_item in offer_data_list:
        end_datetime = start_datetime + dt.timedelta(days=7)

        iwData = {}
        iwData['week'] = '第' + str(w) + '周'
        cur_date = od_item.created
        if cur_date < end_datetime:
          cur_w_mark = od_item.written_score
          cur_i_mark = od_item.Interview_score
          if cur_w_mark is not None:
            totalmark_w = totalmark_w + cur_w_mark
          if cur_i_mark is not None:
            totalmark_i = totalmark_i + cur_i_mark
          count = count + 1
        else:
          start_datetime = end_datetime
          iwData['笔试成绩平均分'] = int(totalmark_w / count)
          iwData['面试成绩平均分'] = int(totalmark_i / count)
          interviewWeeklyData.append(iwData)
          w = w + 1
          totalmark_i = 0
          totalmark_w = 0
      if len(interviewWeeklyData) == 0:
        iwData['week'] = '第一周'
        if count > 0:
          iwData['笔试成绩平均分'] = int(totalmark_w / count)
          iwData['面试成绩平均分'] = int(totalmark_i / count)
        else:
          iwData['笔试成绩平均分'] = int(totalmark_w / count)
          iwData['面试成绩平均分'] = int(totalmark_i / count)
        interviewWeeklyData.append(iwData)
      
      interview_list = Interview.query.filter_by(offer_id=o_id).order_by(Interview.updated).all()
      if len(interview_list) > 0:
        start_datetime = interview_list[0].updated
      else:
        start_datetime = dt.datetime.now()
      attendenceWeeklyData = []
      totalcount_w = 0
      totalcount_i = 0
      w = 1
      for od_item in interview_list:
        end_datetime = start_datetime + dt.timedelta(days=7)
        iwData = {}
        iwData['week'] = '第' + str(w) + '周'
        cur_date = od_item.updated
        if cur_date < end_datetime:
          totalcount_i = totalcount_i + 1
        else:
          start_datetime = end_datetime
          iwData['累积参加笔试人数'] = totalcount_w
          iwData['累积参加面试人数'] = totalcount_i
          attendenceWeeklyData.append(iwData)
          w = w + 1

      if len(attendenceWeeklyData) == 0:
        iwData['week'] = '第一周'
        iwData['累积参加笔试人数'] = totalcount_w
        iwData['累积参加面试人数'] = totalcount_i
        attendenceWeeklyData.append(iwData)

      result['interviewWeeklyData'] = interviewWeeklyData
      result['attendenceWeeklyData'] = attendenceWeeklyData
    return result

  @classmethod
  def updateData(self, id, data):
    old_data = Offer.query.filter_by(id = id).first()
    new_data = dict(data)

    old_data.name = new_data['name']
    old_data.position_type = new_data['position_type']
    old_data.description = new_data['description']
    old_data.education = new_data['education']
    old_data.experience = new_data['experience']
    old_data.need_resume = new_data['need_resume']
    old_data.service_type = new_data['service_type']
    old_data.work_place = new_data['work_place']
    old_data.unit_price = new_data['unit_price']
    
    old_data.update()
    

  @classmethod
  def closeOffer(self, id):
    old_data = Offer.query.filter_by(id = id).first()
    old_data.status = 0
    old_data.update()

  @classmethod
  def get_logs(self, **kwargs):
    result = []
    o_id = kwargs.get('id')
    
    date1 = kwargs.get('date')
    if date1 == 'today' or date1 == '':
      start_time = dt.date.today().strftime('%Y-%m-%d') + ' 00:00:00'
      end_time = dt.date.today().strftime('%Y-%m-%d') + ' 23:59:59'
    else: 
      start_time = date1 + ' 00:00:00'
      end_time = date1 + ' 23:59:59'

    start_timeT = dt.datetime.strptime(start_time, '%Y-%m-%d %H:%M:%S')
    end_timeT = dt.datetime.strptime(end_time, '%Y-%m-%d %H:%M:%S')

    offer = self.query.filter_by(id=o_id).first()

    # cobra-55555 -20-04-24
    log_recs = HiringSchedule.query.filter(HiringSchedule.offer_id == o_id).filter(HiringSchedule.created >= start_timeT).filter(HiringSchedule.created <= end_timeT).order_by(HiringSchedule.created.asc()).all()

    for item in log_recs:
      engineer = Engineer.query.filter_by(id=item.engineer_id).first()
      log = str(item.created)[-8:][:5] + '  ' + str(item.plan_status) + '  ' + str(item.note) + '  ' + '"' + engineer.real_name + '"'
      result.append(log)

    return result

  @classmethod
  def get_written_num(self, o_id):
    schedulelist = OfferScheduleData.query.filter(OfferScheduleData.offer_id == o_id).all()
    result = 0
    result1 = 0
    result2 = 0
    for item in schedulelist:
      result = result + item.written_pass_num
      result1 = result1 + item.resume_collection_num
      result2 = result2 + item.interview_pass_num
    return result, result1, result2
  # // // // // //
    

class OfferData(Base):
  """需求数据"""
  __tablename__ = "offer_data"
  created = db.Column(db.DateTime, nullable=False)  # cobra-55555
  engineer_id = db.Column(db.Integer, db.ForeignKey('engineer.id'), nullable=False, doc="人员外键")
  offer_id = db.Column(db.Integer, db.ForeignKey('offer.id'), nullable=False, doc="需求外键")
  written_score = db.Column(db.Integer, doc="笔试分数")
  Interview_score = db.Column(db.Integer, doc="面试分数")
  nk_result = db.Column(db.String(12), doc="牛咖面试结果:推荐/不推荐")
  nk_evaluate = db.Column(db.String(256), doc="牛咖评价")
  finally_result = db.Column(db.String(12), doc="最终客户评定结果:未评定-未通过-通过")
  customer_evaluate = db.Column(db.String(256), doc="客户评价")
  expect_salary = db.Column(db.Integer, doc="工资")
  entry_time = db.Column(db.String(20), doc="入职时间")


class HiringSchedule(Base):
  """招聘进度表"""
  __tablename__ = 'hiring_schedule'
  engineer_id = db.Column(db.Integer, db.ForeignKey('engineer.id'), nullable=False, doc="人员外键")
  offer_id = db.Column(db.Integer, db.ForeignKey('offer.id'), nullable=False, doc="需求外键")
  plan_status = db.Column(db.String(32), doc="进度状态:[收集-笔试开始/结束-面试开始/结束-面试评价[推荐/不推荐]-评定结果]")
  note = db.Column(db.String(12), doc="备注")


class OfferScheduleData(Base):
  """需求进度数据"""
  __tablename__ = "offer_schedule_data"
  offer_id = db.Column(db.ForeignKey("offer.id"), nullable=False, doc="需求外键")
  resume_collection_num = db.Column(db.Integer, doc="简历收集数量")
  written_pass_num = db.Column(db.Integer, doc="笔试通过数量")
  interview_pass_num = db.Column(db.Integer, doc="面试完成数量")
  offer_pass_num = db.Column(db.Integer, doc="需求满足数量")
  date = db.Column(db.Date, doc="日期")


class OfferPutSchema(BasePutSchema):
  _permission_roles = ['om', 'company_om', 'purchase']
  ModelClass = Offer

  name = fields.Str()
  work_place = fields.String(required=True)
  amount = fields.Integer(required=True)
  description = fields.String(required=True)


class OfferStatistics(object):
  def __init__(self, offers):
    if isinstance(offers, Offer):
      offers = [offers]

    self.demand_amount = 0
    self.cv_push_amount = 0
    self.cv_pass_amount = 0
    self.interview_pass_amount = 0
    self.entry_amount = 0

    for offer in offers:
      if offer.amount is not None:
        self.demand_amount += offer.amount
      self.cv_push_amount += offer.cv_push_amount
      self.cv_pass_amount += offer.cv_pass_amount
      self.interview_pass_amount += offer.interview_pass_amount
      self.entry_amount += offer.entry_amount

    self.cv_push_rate = self.cv_push_amount / self.demand_amount if self.demand_amount else 0
    self.cv_pass_rate = self.cv_pass_amount / self.cv_push_amount if self.cv_push_amount else 0
    self.interview_pass_rate = self.cv_pass_amount / self.cv_push_amount if self.cv_pass_amount else 0
    self.entry_rate = self.entry_amount / self.demand_amount if self.demand_amount else 0
