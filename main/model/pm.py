import json
import datetime as dt
from flask import current_app
from flask_login import current_user
from marshmallow import EXCLUDE

from ._base import db, Base, PostSchema, fields, Schema
from .user import User
from ..schema.base import re_phone, re_email
from config import load_config
from ..util.work_dates import WorkDay, this_and_next_weeks, get_today
from .engineer import DailyLog
from ..exception import NewComException

Config = load_config()


class PmProject(db.Model):
    __tablename__ = "pm_project"
    pm_id = db.Column(db.Integer, db.ForeignKey("pm.id"), primary_key=True)
    project_id = db.Column(db.Integer, db.ForeignKey("project.id"), primary_key=True)


class PmFreeTime(object):
    def __init__(self, date=None, am=None, pmA=None, pmB=None):
        self.date = date
        self.am = am
        self.pmA = pmA
        self.pmB = pmB
        self.disable = False
        self.weekday = 1
        self.need_init = True


class PmPostSchema(PostSchema):
    _permission_roles = ["om", "company_om"]

    company_id = fields.Int(required=True)
    real_name = fields.Str(required=True)
    pre_username = fields.Str()
    gender = fields.Integer()
    phone = fields.Str(required=True, validate=re_phone)
    email = fields.Str(validate=re_email)


class PmWithProjects(Schema):
    id = fields.Integer()
    real_name = fields.String()
    phone = fields.String()
    email = fields.String()
    project = fields.List(fields.String())
    activate = fields.Integer()


class PmDeleteInfo(Schema):
    real_name = fields.String(required=True)

    class _P(Schema):
        name = fields.String(required=True)

        class _E(Schema):
            id = fields.Int(required=True)
            real_name = fields.String(required=True)

        engineers = fields.List(fields.Nested(_E()))

    project = fields.List(fields.Nested(_P()))


class Pm(User):
    __tablename__ = "pm"
    id = db.Column(db.Integer, db.ForeignKey("user.id"), primary_key=True)
    company_id = db.Column(db.Integer, db.ForeignKey("company.id"))

    use_default_free_time = db.Column(db.Integer)
    _default_can_appoint_time = db.Column(db.Text)

    interview = db.relationship("Interview", backref="pm")
    offers = db.relationship("Offer", backref="pm")
    audit = db.relationship("Audit", backref="pm")

    __mapper_args__ = {
        "polymorphic_identity": "pm",
    }

    def __repr__(self):
        return self.real_name

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
        schema = PmPostSchema(many=False, unknown=EXCLUDE)
        data = schema.load(kwargs)
        cls.post_data_modify(**kwargs)
        m = cls(**data)
        if "password" not in kwargs:
            m.set_password(Config.DEFAULT_PWD)
        else:
            m.set_password(kwargs["password"])
        m.save()
        return m

    def action_deactive(self):
        for p in self.projects:
            if len(p.engineers) > 0:
                raise NewComException("项目经理依然有负责的项目", 501)
        self.update(activate=False)

    @property
    def projects_count(self):
        return len(self.project)

    @property
    def engineers_count(self):
        return len(self.engineers)

    @property
    def statistic_of_project(self):
        result = [
            {"id": p.id, "name": p.name, "status": p.status, "engineer_count": 0}
            for p in self.project
        ]
        for item in result:
            es = list(filter(lambda x: x.project_id == item["id"], self.engineers))
            item["engineer_count"] = len(es)
            valid_num = len(list(filter(lambda x: x.ability_score, es)))
            item["average_ability_score"] = (
                0
                if not valid_num
                else sum([e.ability_score or 0 for e in es]) / valid_num
            )
            valid_num = len(list(filter(lambda x: x.attitude_score, es)))
            item["average_attitude_score"] = (
                0
                if not valid_num
                else sum([e.attitude_score or 0 for e in es]) / valid_num
            )
            item["total_daily_logs"] = sum(
                x.duration
                for x in DailyLog.query.filter_by(
                    project_id=item["id"], pm_id=self.id
                ).all()
            )
        return result

    @property
    def offers_count(self):
        return len(self.offers)

    def action_set_can_appoint_time(self, set_info=None, set_default=None):
        # 前端传递来的set_info是个数组， 转化为字典
        set_info = dict(zip([x["date"] for x in set_info], set_info))
        two_weeks_days = this_and_next_weeks()
        if (
                not len(
                    set([day.strftime("%Y-%m-%d") for day in two_weeks_days])
                    - set(set_info.keys())
                )
                    == 0
        ):
            raise NewComException("需传递两周的完整数据", 501)
        for day in set_info:
            set_info[day]["need_init"] = False
        self.use_default_free_time = set_default
        self._default_can_appoint_time = json.dumps(set_info)
        self.save()

    @property
    def default_can_appoint_time(self):
        """
        am: true
        date: "2019-01-25"
        disable: false (已过去的日期和非工作日都会设置成True, )
        need_init: False（说明这天是否需要初始化)
        pmA: true
        pmB: true
        :return:
        """
        today = get_today()
        two_weeks_days = this_and_next_weeks()
        result = []

        if not self._default_can_appoint_time:
            setted_days = {}
        else:
            setted_days = json.loads(self._default_can_appoint_time)

        for day in two_weeks_days:
            format_day_str = day.strftime("%Y-%m-%d")
            if day < today or not WorkDay.is_work_day(day):
                result.append(
                    {
                        "disable": True,
                        "need_init": False,
                        "date": format_day_str,
                        "am": False,
                        "pmA": False,
                        "pmB": False,
                    }
                )
            else:
                if format_day_str in setted_days.keys():
                    result.append(setted_days[format_day_str])
                else:
                    result.append(
                        {
                            "disable": False,
                            "need_init": True,
                            "date": format_day_str,
                            "am": False,
                            "pmA": False,
                            "pmB": False,
                        }
                    )

        return result

    @property
    def need_set_appoint_time(self):
        if not self.use_default_free_time:
            return True
        if not self._default_can_appoint_time:
            return True
        default_appoint_time = self.default_can_appoint_time
        for day in default_appoint_time:
            if day["need_init"]:
                return True
        return False
