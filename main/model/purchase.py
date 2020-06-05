import datetime as dt

from flask import current_app
from flask_login import current_user

from ..extention import db
from config import load_config
from ..schema.base import re_phone, re_email
from ..exception import NewComException
from ..util.work_dates import month_first_end_date, get_today
from ._base import Base, PostSchema, fields, Schema
from .user import User
from .engineer import (
    Payment,
    PaymentStatus,
    WorkReport,
    Career,
    PaymentSimpleSchema,
    EngineerCompanyOrder,
)
from .company import OfferStatus, OfferStatistics, Offer, Company
from ._base import BaseStatus

Config = load_config()


class PurchasePostSchema(PostSchema):
    _permission_roles = ["om", "company_om"]

    company_id = fields.Int(required=True)
    real_name = fields.Str(required=True)
    pre_username = fields.Str()
    gender = fields.Integer()
    phone = fields.Str(required=True, validate=re_phone)
    email = fields.Str(validate=re_email)


class Purchase(User):
    __tablename__ = "purchase"

    id = db.Column(db.Integer, db.ForeignKey("user.id"), primary_key=True)
    company_id = db.Column(db.Integer, db.ForeignKey("company.id"))

    __mapper_args__ = {
        "polymorphic_identity": "purchase",
    }

    def __repr__(self):
        return self.real_name if self.real_name else "无名采购"

    @classmethod
    def post_data_modify(cls, **kwargs):
        user_phone = User.query.filter_by(phone=kwargs["phone"]).first()
        user_email = User.query.filter_by(email=kwargs["email"]).first()
        if user_phone and user_email:
            raise NewComException("手机号、邮箱已被注册，请更换！", 422)
        if user_phone:
            raise NewComException("手机号已被注册，请更换！", 422)
        if user_email:
            raise NewComException("邮箱号已被注册，请更换！", 422)

    @classmethod
    def post(cls, **kwargs):
        if current_user.role == "company_om":
            kwargs["company_id"] = current_user.company_id
        schema = PurchasePostSchema(many=False)
        data = schema.load(kwargs)
        cls.post_data_modify(**kwargs)
        m = cls(**data)
        if "password" not in kwargs:
            m.set_password(Config.DEFAULT_PWD)
        else:
            m.set_password(kwargs["password"])
        m.save()
        return m

    @property
    def ing_offers_count(self):
        count = len(
            list(filter(lambda x: x.status == OfferStatus.open, self.company.offers))
        )
        return count

    @property
    def finished_offer_count(self):
        count = len(
            list(filter(lambda x: x.status == OfferStatus.closed, self.company.offers))
        )
        return count

    @property
    def ing_offers_complete_rate(self):
        offers = Offer.query.filter(
            Offer.company_id == self.company_id, Offer.status == OfferStatus.open
        ).all()
        offers_statistic = OfferStatistics(offers)
        return offers_statistic.entry_rate


class MonthlyBillStatus(BaseStatus):
    unpay = 0
    payed = 1


class MonthlyBillPostSchema(PostSchema):
    payment_ids = fields.List(fields.Integer)


class MonthlyBillSchema(Schema):
    payments = fields.List(fields.Nested(PaymentSimpleSchema(many=False)))
    billing_cycle = fields.Integer()
    count = fields.Integer()
    service_fee_rate = fields.Float()
    service_fee = fields.Float()
    hr_fee = fields.Float()
    hr_fee_rate = fields.Float()
    use_hr_count = fields.Integer()
    tax_rate = fields.Float()
    tax = fields.Float()
    finance_rate = fields.Float()
    finance_fee = fields.Float()
    company_pay = fields.Float()
    year_month_date_format = fields.Date()
    created = fields.DateTime()


class MonthlyBill(Base):
    __tablename__ = "monthly_bill"
    company_id = db.Column(db.Integer, db.ForeignKey("company.id"))
    year_month = db.Column(db.Integer)
    money = db.Column(db.Float("20,2"))
    station_salary = db.Column(db.Float("20,2"))
    pay_method = db.Column(db.String(8))
    pay_code = db.Column(db.String(64))
    status = db.Column(db.Integer, index=True, default=MonthlyBillStatus.unpay)
    billing_cycle = db.Column(db.Integer)
    engineer_count = db.Column(db.Integer)
    service_fee_rate = db.Column(db.Integer)
    service_fee = db.Column(db.Float("20,2"))
    hr_fee = db.Column(db.Float("20,2"))
    hr_fee_rate = db.Column(db.Integer)
    use_hr_count = db.Column(db.Integer)
    tax_rate = db.Column(db.Float)
    tax = db.Column(db.Float("20,2"))
    finance_rate = db.Column(db.Float)
    finance_fee = db.Column(db.Float("20,2"))
    company_pay = db.Column(db.Float("20,2"))

    @property
    def year_month_date_format(self):
        return dt.date(year=self.year_month // 100, month=self.year_month % 100, day=1)

    @classmethod
    def post(cls, **kwargs):
        company_id = current_user.company_id
        c = Company.query.filter_by(id=company_id).first()
        # if MonthlyBill.query.filter_by(company_id=company_id, year_month=year_month).all():
        #     raise NewComException('已经生成的月结算单', 500)

        year_month = kwargs.get("year_month")
        payments = Payment.query.filter(
            Payment.year_month == year_month,
            Payment.company_id == company_id,
            Payment.status == PaymentStatus.submit,
        ).all()
        if not payments:
            raise NewComException("无可生成的账单", 500)

        for p in payments:
            # if not p.company_id == company_id or not p.year_month == year_month:
            #     raise NewComException('选择的账单应为本公司{}的账单。'.format(year_month), 501)
            if p.monthly_bill_id:
                raise NewComException("{}的账单已经生成结算单".format(p.engineer), 501)

        ps = payments
        result = dict()
        sc = PaymentSimpleSchema(many=True)
        ps = sc.dump(ps)
        for p in ps:
            if str(p["year_month"]) in result.keys():
                result[str(p["year_month"])]["payments"].append(p)
            else:
                result[str(p["year_month"])] = {
                    "statistic": {
                        "service_fee_rate": c.service_fee_rate,
                        "tax_rate": c.tax_rate,
                        "finance_rate": c.finance_rate,
                        "hr_fee_rate": c.hr_fee_rate,
                        "billing_cycle": c.billing_cycle,
                    },
                    "payments": [
                        p
                    ],  # filter(lambda x: x.year_month == p['year_month'], ps),
                    "year_month": dt.date(
                        year=int(p["year_month"]) // 100,
                        month=int(p["year_month"]) % 100,
                        day=1,
                    ),
                }
        for ym, data in result.items():
            ps = data["payments"]
            # data['statistic']["count"] = len(ps)
            data["statistic"]["company_pay"] = sum([p["company_pay"] for p in ps])
            # data['statistic']["service_fee"] = sum([p['service_fee'] for p in ps])
            data["statistic"]["tax"] = sum([p["tax"] for p in ps])
            data["statistic"]["hr_fee"] = sum([p["hr_fee"] for p in ps])
            data["statistic"]["finance_fee"] = sum([p["finance_fee"] for p in ps])
            data["statistic"]["use_hr_count"] = sum([p["use_hr_service"] for p in ps])
            data["statistic"]["service_fee"] = sum([p["service_fee"] for p in ps])
            data["statistic"]["station_salary"] = sum([p["station_salary"] for p in ps])

        # work_reports = WorkReport.query.filter_by(company_id=company_id, year_month=year_month).all()
        # 如果本月还有未生成的月账单，则应该阻止生成账单，先找到所有属于本公司的career，然后查看这些career是否在本月有工时。
        # careers = Career.query.filter_by(company_id=company_id).all()
        # careers_in_this_month = []
        # for c in careers:
        #     month_begin, month_end = month_first_end_date(int(year_month / 100), year_month % 100)
        #     # 如果start 在下月，则不包含
        #     if c.start > month_end:
        #         continue
        #     # 如果start 在本月及本月之前，且end在本月或本月之后：
        #     if c.end is None or c.end >= month_begin:
        #         careers_in_this_month.append(c)

        # if not len(careers_in_this_month) == len(work_reports):
        #     all_engineers = [c.engineer.real_name for c in careers_in_this_month]
        #     submit_work_report_engineers = [w.engineer.real_name for w in work_reports]
        #     un_submit_engieers = list(set(all_engineers) - set(submit_work_report_engineers))
        #     raise NewComException("尚有员工({})未提交该月工时报告".format(','.join(un_submit_engieers)), 500)

        # if not len(work_reports) == len(payments):
        #     raise NewComException('尚有工作报告未审核通过', 500)

        company_pay = sum([payment.company_pay for payment in payments])
        mb = MonthlyBill(
            company_id=company_id, year_month=year_month, company_pay=company_pay
        )
        mb.save()
        try:
            mb.update(**data["statistic"])

            for p in payments:
                p.status = PaymentStatus.checked
                p.monthly_bill_id = mb.id
                p.save()
                epos = EngineerCompanyOrder.query.filter_by(
                    engineer_id=p.engineer_id, career_id=p.career_id
                ).all()
                for epo in epos:
                    epo.complete_part(p)
            return mb
        except Exception as e:
            # todo 还应做payment和order的回撤
            mb.delete()
            return None

    def action_pay(self, status):
        if status == MonthlyBillStatus.payed:
            self.status = status
            current_app.logger.error("len payments: {}".format(len(self.payments)))
            for p in self.payments:
                p.status = PaymentStatus.checked
                p.save()
        self.save()

    def action_export(self):
        pass

    @property
    def payments(self):
        if not hasattr(self, "_payments"):
            _payments = Payment.query.filter_by(monthly_bill_id=self.id).all()
            setattr(self, "_payments", _payments)
        return getattr(self, "_payments")

    @property
    def project_count(self):
        ps = []
        for p in self.payments:
            if p.project_id not in ps:
                ps.append(p)
        return len(ps)

    @property
    def count(self):
        return len(self.payments)
