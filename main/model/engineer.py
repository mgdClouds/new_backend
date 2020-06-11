import os
import json
import datetime as dt
import tempfile
from functools import lru_cache

from marshmallow import fields, Schema, EXCLUDE
import xlwt
from sqlalchemy import and_, UniqueConstraint, not_
from pdf2image import convert_from_path
from flask import current_app, request
from flask import url_for

from config import load_config
from .user import User, Roles
from ._base import Base, OfferShutDownReason, OfferStatus, PostSchema, BaseStatus
from ..schema.base import BasePutSchema, BaseActionSchema
from ..extention import db
# from .company import OfferData
from ..util.work_dates import month_first_end_date, get_today, workdays_between, get_last_year_month, is_work_day, \
    int_year_month, month_work_days, months_later, change_datetime_date, is_holiday, days_num_between, days_between, \
    str_to_date
from ..exception import NewComException
from ..util.personal_tax import cal as cal_personal_tax

Config = load_config()

class EngineerStatus(BaseStatus):
    ready = 0
    interview = 1
    on_duty = 2
    leaving = 3
    finish = 4
    entering = 5

    show_name = [('on_duty', '在职'), ('interview', '面试中'), ('ready', '待选'), ("leaving", "待出项"), ('entering', "入项中"),]


class JobWantedAttitude(BaseStatus):
    positive = 1  # 积极找工作
    negative = -1  # 暂时不换工作
    neutral = 0  # 随便看看


class AbilityPostSchema(PostSchema):
    engineer_id = fields.Int(required=True)
    name = fields.Str()
    level = fields.Str()


class EducationPostSchema(PostSchema):
    engineer_id = fields.Int(required=True)
    start_date = fields.Date(required=True)
    end_date = fields.Date(required=True)
    school = fields.String(required=True)
    edu_college_type = fields.String()
    edu_college_rank = fields.String()
    edu_college_dept = fields.String()
    edu_major = fields.String(required=True)
    edu_recruit = fields.String()
    edu_gpa = fields.Float()
    degree = fields.String(required=True)
    degree_norm = fields.String(required=True)
    is_highest = fields.Int()

class EngineerPostSchema(PostSchema):
    _permission_roles = ['om']

    class ES(EducationPostSchema):
        engineer_id = fields.Int()

    class AS(AbilityPostSchema):
        engineer_id = fields.Int()

    username = fields.Str()
    pre_username = fields.Str()
    real_name = fields.Str(required=True)
    gender = fields.Integer(required=True)
    email = fields.Str(required=True)
    phone = fields.Str(required=True)

    ability = fields.List(fields.Nested(AS(many=False, unknown=EXCLUDE)))
    education = fields.List(fields.Nested(ES(many=False, unknown=EXCLUDE)))
    job_wanted_status = fields.Function(lambda x: x,
                                        deserialize=lambda x: JobWantedAttitude.str2int(x))
    cv_upload_result = fields.Str()


class EngineerManageSchema(Schema):
    id = fields.Integer()
    real_name = fields.String()
    phone = fields.String()
    status = fields.Function(lambda x: EngineerStatus.int2str(x.status))
    project = fields.String()
    pm = fields.String()
    ability_score = fields.Float()
    attitude_score = fields.Float()
    cv_name = fields.String()
    cv_path = fields.List(fields.String())

    class PLS(Schema):
        id = fields.Integer()
        name = fields.String()
        money = fields.Float()
        position = fields.String()

    position_level = fields.Nested(PLS(many=False))

    class CS(Schema):
        class COS(Schema):
            id = fields.Integer()
            start_date = fields.Date()
            end_date = fields.Date()
            expect_total_fee = fields.Float()
            finished_fee = fields.Float()
            status = fields.Function(lambda x: EngineerCompanyOrderStatus.int2str(x.status))
            auto_renew = fields.Integer()
            renew_cycle = fields.Float()

        orders = fields.List(fields.Nested(COS(many=False)))
        auto_renew = fields.Integer()
        renew_cycle = fields.Integer()
        salary_type = fields.String()
        id = fields.Integer()
        use_hr_service = fields.Bool()

    now_career = fields.Nested(CS(many=False))


class Engineer(User):
  id = db.Column(db.Integer, db.ForeignKey('user.id'), primary_key=True)
  # 简历名称
  cv_name = db.Column(db.String(256))
  # 图片简历数量
  cv_img_amount = db.Column(db.Integer, default=0)
  # 入项材料名称
  ef_name = db.Column(db.String(256))
  # 入项材料图片数量
  ef_img_amount = db.Column(db.Integer, default=0)
  status = db.Column(db.Integer, index=True)
  job_wanted_status = db.Column(db.Integer, index=True)

  major = db.Column(db.String(32))
  highest_degree = db.Column(db.String(8))
  highest_education_id = db.Column(db.Integer())
  pay_welfare = db.Column(db.Integer())
  welfare_rate = db.Column(db.Float())
  bank_code = db.Column(db.String(24))
  contract_confirm = db.Column(db.Integer())

  ability_score = db.Column(db.Float)
  attitude_score = db.Column(db.Float)
  total_score = db.Column(db.Float)
  # 激励
  motivation = db.Column(db.Float)
  rank = db.Column(db.Integer)
  now_career_id = db.Column(db.Integer)

  living_address = db.Column(db.String(32), doc="当前所在地")
  hukou_address = db.Column(db.String(32), doc="户口所在地")
  id_card = db.Column(db.String(18), doc="身份证号")
  race = db.Column(db.String(10), doc="民族")
  english_level = db.Column(db.String(8), doc="英语水平")
  computer_level = db.Column(db.String(8), doc="计算机水平")
  work_position = db.Column(db.String(8), doc="当前职位")
  work_company = db.Column(db.String(16), doc="当前单位")
  work_industry = db.Column(db.String(8), doc="所处行业")
  work_status = db.Column(db.String(5), doc="在职状态")
  work_salary = db.Column(db.String(8), doc="当前薪资")
  work_location = db.Column(db.String(12), doc="工作地点")
  expect_salary = db.Column(db.String(8), doc="期望薪资")
  expect_industry = db.Column(db.String(8), doc="期望行业")
  expect_time = db.Column(db.Date, doc="到岗时间")
  expect_jstatus = db.Column(db.String(5), doc="当前离职/在职状态 ")
  expect_jlocation = db.Column(db.String(12), doc="期望工作地址")
  work_year = db.Column(db.String(32), doc="工作年限")

  company_id = db.Column(db.Integer, db.ForeignKey('company.id'))
  project_id = db.Column(db.Integer, db.ForeignKey('project.id'))

  position_level_id = db.Column(db.Integer, db.ForeignKey('position_level.id'))
  position_id = db.Column(db.Integer, db.ForeignKey('position.id'))

  pm_id = db.Column(db.Integer, db.ForeignKey('pm.id'))
  interview = db.relationship('Interview', backref='engineer')
  career = db.relationship('Career', backref='engineer')
  education = db.relationship('Education', backref='engineer')
  ability = db.relationship('Ability', backref='engineer')
  payment = db.relationship('Payment', backref='engineer')
  audit = db.relationship('Audit', backref='engineer')
  hiring_schedule = db.relationship('HiringSchedule', backref='engineer')
  pm = db.relationship('Pm', backref='engineers', foreign_keys=pm_id)

  written_interview_info = db.relationship('WrittenInterviewInfo', backref='engineer')
  job_experience = db.relationship('JobExperience', backref='engineer')
  project_experience = db.relationship('ProjectExperience', backref='engineer')
  language = db.relationship('Language', backref='engineer')
  langcert = db.relationship('Langcert', backref='engineer')

  s_ability = db.Column(db.String(64), index=True, default='')
  s_education = db.Column(db.String(64), index=True)
  s_order_auto_renew = db.Column(db.Integer(), index=True)
  s_use_hr_service = db.Column(db.Integer(), index=True)
  s_money = db.Column(db.Float(), index=True)
  s_salary_type = db.Column(db.Integer(), index=True)
  s_need_renew_order = db.Column(db.Integer(), index=True, default=0)

  __mapper_args__ = {
      'polymorphic_identity': 'engineer',
  }

  def search_index(self):
    self.s_ability = ','.join([x.name for x in self.ability])[:64]
    self.s_education = ','.join([x.school + "-" + x.degree + '-' + x.major for x in self.education])[:64]
    # self.s_need_renew_order = self.now_career
    if self.now_career:
      self.s_order_auto_renew = self.now_career.auto_renew
      self.s_use_hr_service = self.now_career.use_hr_service
      self.s_money = self.now_career.position_level.money
      # todo
      self.s_salary_type = self.now_career.salary_type
      # self.s_need_renew_order = 0
    self.save()

  def copy2career(self):
      if not self.now_career:
          return
      now_career = self.now_career
      now_career.real_name = self.real_name
      now_career.engineer_status = self.status
      keys = ['phone', 'ability_score', 'attitude_score', 'position_id']
      for k in keys:
          v = getattr(self, k)
          setattr(now_career, k, v)
      now_career.save()

  def __repr__(self):
      return self.real_name

  def supplement_daily_logs(self):
      pass

  @property
  def entering_status(self):
    ep = EnterProject.query.filter_by(career_id=self.now_career_id).first()
    if not ep:
        return None
    else:
        return EnterProjectStatus.int2str(ep.status)

  @property
  def highest_education(self):
    if self.highest_education_id:
        return Education.query.filter_by(id=self.highest_education_id).first()
    return None

  @property
  def now_order(self):
      orders = EngineerCompanyOrder.query.filter_by(career_id=self.now_career_id).all()
      for order in orders:
          if not order.start_date or not order.end_date:
              # todo 有可能没这么简单
              continue
          if order.is_ing() == EngineerCompanyOrderStatus.underway:
              return order
      return None

  @property
  def last_order(self):
      orders = EngineerCompanyOrder.query.filter_by(career_id=self.now_career_id).all()
      last_order = orders[0]
      for order in orders:
          if order.start_date > last_order.start_date:
              last_order = order
      return last_order

  def action_renew_order(self, **kwargs):
      cycle = kwargs.get('renew_cycle')
      auto_renew = kwargs.get('auto_renew', 0)
      work_content = kwargs.get('work_content')
      service_type = kwargs.get('service_type')

      last_order = self.last_order
      last_end_date = last_order.end_date
      one_day = dt.timedelta(days=1)
      today = get_today()
      start_date = last_end_date + one_day
      end_date = months_later(start_date, cycle)

      data = dict(work_content=work_content, service_type=service_type)
      data['auto_renew'] = auto_renew
      data['renew_cycle'] = cycle
      data['company_id'] = self.company_id
      data['engineer_id'] = self.id
      data['project_id'] = self.project_id
      data['career_id'] = self.now_career_id
      data['start_date'] = start_date.strftime('%Y-%m-%d')
      data['end_date'] = end_date.strftime('%Y-%m-%d')
      result = EngineerCompanyOrder.post(**data)
      last_order.next_id = result.id
      last_order.save()

  def auto_renew_order(self):
      if not self.now_career_id:
          return
      renew_cycle = self.now_career.renew_cycle
      # auto_renew = self.now_career.auto_renew
      work_content = self.now_order.work_content
      service_type = self.now_order.service_type
      if not self.last_order.id == self.now_order.id:
          return
      self.action_renew_order(renew_cycle=renew_cycle,
                              work_content=work_content, service_type=service_type,
                              auto_renew=1)

  def in_career_check(self):
      if not self.now_career_id:
          return False
      if not self.now_career.start <= get_today():
          return False
      if self.now_career.end:
          if not self.now_career.end >= get_today():
              return False
      return True

  @property
  def now_career(self):
      if not self.now_career_id:
          return None
      return Career.query.get(self.now_career_id)

  def turn_cv2img(self, cv_name):
      cv_path = os.path.join(os.path.join(Config.ROOT_DIR, Config.FILE_TEM_PATH), cv_name)
      with tempfile.TemporaryDirectory() as path:
          images = convert_from_path(cv_path)
          cv_root_path = os.path.join(os.path.join(Config.ROOT_DIR, Config.FILE_CV_PATH), str(self.id))
          if not os.path.exists(cv_root_path):
              os.mkdir(cv_root_path)
          for index, image in enumerate(images):
              image.save('%s/page_%s.jpg' % (cv_root_path, index + 1), quality=65)
          self.cv_img_amount = len(images)
      self.cv_name = '.'.join(cv_name.split('.')[1:])
      self.save()

  @property
  def cv_path(self):
      all_images = [url_for("engineer.cv", page=index + 1, engineer_id=self.id) for index in
                    range(self.cv_img_amount)]
      return all_images

  @property
  def ef_path(self):
      all_images = [url_for("engineer.ef", page=index + 1, engineer_id=self.id) for index in
                    range(self.ef_img_amount)] if self.ef_img_amount is not None else []
      return all_images

  def action_upload_cv(self, cv_upload_result):
      self.turn_cv2img(cv_upload_result)

  def action_update_engineer_score(self):
      work_reports = WorkReport.query.filter_by(engineer_id=self.id).all()
      total_attitude_score = sum(
          [work_report.attitude_score if work_report.attitude_score is not None else 0 for work_report in
            work_reports])
      total_ability_score = sum(
          [work_report.ability_score if work_report.ability_score is not None else 0 for work_report in work_reports])
      self.ability_score = round(total_ability_score / len(work_reports), 1)
      self.attitude_score = round(total_attitude_score / len(work_reports), 1)
      self.total_score = self.ability_score + self.attitude_score
      self.save()

  @classmethod
  def post(cls, **kwargs):
      schema = EngineerPostSchema(many=False, unknown=EXCLUDE)
      phone = User.query.filter_by(phone=kwargs["phone"]).first()
      if phone:
          raise NewComException("该手机号已被注册，请更换！", 403)
      email = User.query.filter_by(email=kwargs["email"]).first()
      if email:
          raise NewComException("该邮箱已被注册，请更换！", 403)
      data = schema.load(kwargs)
      from main.api.admin import _create_engineer_pre_username
      if not data.get('pre_username'):
          data['pre_username'] = _create_engineer_pre_username()

      data.pop('ability') if 'ability' in data else None
      data.pop('education') if 'education' in data else None
      model = cls(**data)

      model.set_password(Config.DEFAULT_PWD)
      model.role = Roles.engineer
      model.status = EngineerStatus.ready
      model.save()

      education = kwargs.get('education', [])
      for education_item in education:
          education_item['engineer_id'] = model.id
          ed = Education.post(**education_item)
          ed.save()

      ability = kwargs.get('ability', [])
      for _ab in ability:
          _ab['engineer_id'] = model.id
          ab = Ability.post(**_ab)
          ab.save()

      cv_upload_result = data.get('cv_upload_result', None)
      if not cv_upload_result:
          if not Config.DEBUG:
              raise NewComException('简历呢？', 500)
      else:
          model.turn_cv2img(cv_upload_result)

      return model

  @classmethod
  def post_from_cv(cls, **kwargs):

    #   print(888,cls)
    #   print(666,kwargs)
    #   print(777, kwargs.get('cv_name'))
      print(888, kwargs.get('name'))
      print(999,kwargs.get('email'))
      print(999999,kwargs.get('college'))
      offerID = kwargs.get('offerID')
      model = cls()
      writtenInterviewInfo = WrittenInterviewInfo()
      print('cls : ', cls)


      emailOfPost = ''
      if(kwargs.get('email')):
        emailOfPost = kwargs.get('email')
        print("cls in IF : ", cls)
        oldModel = cls.query.filter_by(email=emailOfPost).first()

        if oldModel is not None:
          print('old model is not none')
          print('OldModel: ', oldModel, oldModel.id)
          offerdata = {}
        #   limit here!!!
          duplicatedEngineers = writtenInterviewInfo.query.filter_by(engineer_id=oldModel.id, offer_id=offerID).all()
          print("duplicated engineers : ", len(duplicatedEngineers))
          if (len(duplicatedEngineers) > 0): 
              offerdata['engineer_id'] = None
              offerdata['offer_id'] = None
          else:
            offerdata['engineer_id'] = oldModel.id   
            offerdata['offer_id'] = offerID
            writtenInterviewInfo.engineer_id = oldModel.id
            writtenInterviewInfo.offer_id = offerID
            writtenInterviewInfo.save()
          return offerdata
     
      created_date = get_today()
      from main.api.admin import _create_engineer_pre_username
      model.pre_username = _create_engineer_pre_username()
      if(kwargs.get('name') and kwargs.get('name') != ''):
        model.real_name = kwargs['name']
      if(kwargs.get('gender')):
        model.gender = 1 if kwargs.get('gender') == '男' else 0
      else:
        model.gender = 1
      if(kwargs.get('phone')):
        model.phone = kwargs.get('phone')
      if(kwargs.get('email')):
        model.email = kwargs.get('email')
      if(kwargs.get('birthday')):
        if kwargs.get('birthday') is not None and len(kwargs.get('birthday')) == 7:
          model.birthday = dt.datetime.strptime(kwargs.get('birthday') + '.01', '%Y.%m.%d').date()
        else:
          model.birthday = dt.datetime.strptime(kwargs.get('birthday'), '%Y.%m.%d').date()
      if(kwargs.get('age')):
        model.age = kwargs.get('age')
      model.password = 'pbkdf2:sha256:50000$DelgHvCw$ed70a953d7467907041666ef9f1dd4c8f84937b59715f8060f1707db3e3d6a82'
      model.role = 'engineer'
      model.activate = 1
      model.status = 1
      if(kwargs.get('hometown_address_norm')):
        model.living_address = kwargs.get('hometown_address_norm')
      if(kwargs.get('hukou_address_norm')):
        model.hukou_address = kwargs.get('hukou_address_norm')
      if(kwargs.get('work_company')):
        model.work_company = kwargs.get('work_company')
      if(kwargs.get('cv_name')):
          print(472, "cv_name: ", kwargs.get('cv_name'))
          print(473, "name: ", kwargs.get('name'))
          print(474, "college: ", kwargs.get('college'))
          if ((kwargs.get('name') is not None) and (kwargs.get('college') is not None)):
            print('476 : detailed cv_name')
            model.cv_name = kwargs.get('cv_name') + " " + kwargs.get('name') + " " + kwargs.get('college')
          else:
            print('479 : simple cv_name')
            model.cv_name = kwargs.get('cv_name') 
      model.save()

      if (model.id is not None):
        writtenInterviewInfo.engineer_id = model.id
      if (offerID is not None):
        writtenInterviewInfo.offer_id = offerID
      writtenInterviewInfo.save()

      # education
      if kwargs.get('education_objs'):
        for education in kwargs.get('education_objs'):
          print('481 : education: ',education)
          ed = Education()
          ed.engineer_id = model.id

          print(485,' : start_date : ', education.get('start_date'))

          if education.get('start_date') is not None and len(education.get('start_date')) == 7:
            ed.start_date = dt.datetime.strptime(education.get('start_date') + '.01', '%Y.%m.%d').date()
          elif education.get('start_date') is not None:
            ed.start_date = dt.datetime.strptime(education.get('start_date'), '%Y.%m.%d').date()
          print(491, ' : end_date : ', education.get('end_date'))
          
          if education.get('end_date') is not None and len(education.get('end_date')) == 7:
            ed.start_date = dt.datetime.strptime(education.get('end_date') + '.01', '%Y.%m.%d').date()
          elif education.get('end_date') is not None:
            ed.start_date = dt.datetime.strptime(education.get('end_date'), '%Y.%m.%d').date()
    
          ed.school = education.get('edu_college')
          ed.edu_college_type = education.get('edu_college_type')
          ed.edu_college_rank = education.get('edu_college_rank')
          ed.edu_college_dept = education.get('edu_college_dept')
          ed.edu_major = education.get('edu_major')
          ed.edu_recruit = education.get('edu_recruit')

          ed.edu_gpa = education.get('edu_gpa')

          ed.degree = education.get('edu_degree')
          ed.degree_norm = education.get('edu_degree_norm')

          ed.save()
          print("|||||||||||||||||||||||||||||")

      # job_experience
      if kwargs.get('job_exp_objs'):
        for job_exp in kwargs.get('job_exp_objs'):
          job_exp_item = JobExperience()
          job_exp_item.engineer_id = model.id

          if job_exp.get('start_date') is not None and len(job_exp.get('start_date')) == 7:
            job_exp_item.start_date = dt.datetime.strptime(job_exp.get('start_date') + '.01', '%Y.%m.%d').date()
          elif job_exp.get('start_date') is not None:
            job_exp_item.start_date = dt.datetime.strptime(job_exp.get('start_date'), '%Y.%m.%d').date()

          if job_exp.get('end_date') != '至今':
            if job_exp.get('end_date') is not None and len(job_exp.get('end_date')) == 7:
              job_exp_item.end_date = dt.datetime.strptime(job_exp.get('end_date') + '.01', '%Y.%m.%d').date()
            else:
              job_exp_item.end_date = dt.datetime.strptime(job_exp.get('end_date'), '%Y.%m.%d').date()
          else:
            job_exp_item.end_date = created_date
          
          job_exp_item.company_name = job_exp.get('job_cpy')
          job_exp_item.company_nature = job_exp.get('job_cpy_nature')
          job_exp_item.company_size = job_exp.get('job_cpy_size')
          job_exp_item.company_desc = job_exp.get('job_cpy_desc')
          job_exp_item.industry = job_exp.get('industry')
          job_exp_item.position = job_exp.get('job_position')
          job_exp_item.dept = job_exp.get('job_dept')
          job_exp_item.nature = job_exp.get('job_nature')
          job_exp_item.staff = job_exp.get('job_staff')
          job_exp_item.report_to = job_exp.get('job_report_to')
          job_exp_item.location = job_exp.get('job_location')
          job_exp_item.duaration = job_exp.get('job_duaration')
          job_exp_item.capacity = job_exp.get('job_capacity')
          job_exp_item.content = job_exp.get('job_content')

          job_exp_item.save()
      
      # project_experience
      if kwargs.get('proj_exp_objs'):
        for proj_exp in kwargs.get('proj_exp_objs'):
          proj_exp_item = ProjectExperience()
          proj_exp_item.engineer_id = model.id

          if proj_exp.get('start_date') is not None and len(proj_exp.get('start_date')) == 7:
            proj_exp_item.start_date = dt.datetime.strptime(proj_exp.get('start_date') + '.01', '%Y.%m.%d').date()
          elif proj_exp.get('start_date') is not None:
            proj_exp_item.start_date = dt.datetime.strptime(job_exp.get('start_date'), '%Y.%m.%d').date()

          if proj_exp.get('end_date') != '至今':
            if proj_exp.get('end_date') is not None and len(proj_exp.get('end_date')) == 7:
              proj_exp_item.end_date = dt.datetime.strptime(proj_exp.get('end_date') + '.01', '%Y.%m.%d').date()
            elif proj_exp.get('end_date') is not None:
              proj_exp_item.end_date = dt.datetime.strptime(proj_exp.get('end_date'), '%Y.%m.%d').date()
          elif proj_exp.get('end_date') is not None:
            proj_exp_item.end_date = created_date
          proj_exp_item.name = proj_exp.get('proj_name')
          proj_exp_item.company_name = proj_exp.get('proj_cpy')
          proj_exp_item.position = proj_exp.get('proj_position')
          proj_exp_item.resp = proj_exp.get('proj_resp')
          proj_exp_item.content = proj_exp.get('proj_content')

          proj_exp_item.save()
      
      # language
      if kwargs.get('lang_objs'):
        for lang_obj in kwargs.get('lang_objs'):
          lang = Language()
          lang.engineer_id = model.id
          lang.name = lang_obj.get('language_name')
          lang.level = lang_obj.get('language_level')
          lang.read_write = lang_obj.get('language_read_write')
          lang.listen_speak = lang_obj.get('language_listen_speak')

          lang.save()

      # langcert
      if kwargs.get('cert_objs'):
        for cert_obj in kwargs.get('cert_objs'):
          cert = Langcert()
          cert.engineer_id = model.id
          cert.lang = cert_obj.get('langcert_lang')
          cert.name = cert_obj.get('langcert_name')
          cert.score = cert_obj.get('langcert_score')

          cert.save()

      # ability
      if kwargs.get('skills_objs'):
        for skill_obj in kwargs.get('skills_objs'):
          skill = Ability()
          skill.engineer_id = model.id
          skill.name = skill_obj.get('skills_name')
          skill.level = skill_obj.get('skills_level')
          skill.skills_time = skill_obj.get('skills_time')
          skill.save()

      # career
      career = Career()
      career.engineer_id = model.id
      career.real_name = model.real_name
      career.phone = model.phone
      career.offer_id = offerID
      career.status = 1
      career.start = get_today()
      career.save()

      model.now_career_id = career.id
      model.update()

      offerdata = {}
      offerdata['engineer_id'] = model.id
      offerdata['offer_id'] = offerID

      return offerdata


  def action_to_pm(self, **kwargs):  # 工程师更换PM
      old_pm_id = int(kwargs.get('old_pm_id'))
      new_pm_id = int(kwargs.get('new_pm_id'))
      project_id = self.project_id

      sql = 'update {} set pm_id = {}  where pm_id={} and project_id={}'
      # audit 审批更换
      db.session.execute(sql.format('audit', new_pm_id, old_pm_id, project_id))
      # daily_logs 日报更换
      db.session.execute(sql.format('daily_log', new_pm_id, old_pm_id, project_id))
      # interview  面试更换
      db.session.execute(sql.format('interview', new_pm_id, old_pm_id, project_id))
      # enter_project 入项更换
      db.session.execute(sql.format('enter_project', new_pm_id, old_pm_id, project_id))
      # payment 结算更换
      db.session.execute(sql.format('payment', new_pm_id, old_pm_id, project_id))
      self.pm_id = new_pm_id
      try:
          db.session.add(self)
          db.session.commit()
      except Exception as e:
          db.session.rollback()
          raise NewComException('更换项目经理失败。', 501)

  def action_payment_with_work_report(self, **kwargs):
      payment_id = kwargs.get('id')

      class PS(PaymentSimpleSchema):
          class WD(Schema):
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

              class DailyLogDefaultSchema(Schema):
                  id = fields.Int()
                  date = fields.Date()
                  duration = fields.Float()
                  content = fields.Str()
                  note = fields.Str()
                  origin_type = fields.Str()
                  engineer_company_order_id = fields.Integer()

              class LeaveDefaultSchema(Schema):
                  leave_type = fields.String()
                  start_date = fields.DateTime()
                  end_date = fields.DateTime()
                  duration = fields.Float()
                  reason = fields.String()

              class ExtraWorkDefaultSchema(Schema):
                  reason = fields.String()
                  start_date = fields.DateTime()
                  end_date = fields.DateTime()
                  duration = fields.Float()

              work_days_list = fields.List(fields.Nested(DailyLogDefaultSchema(many=False)))
              leave_days_list = fields.List(fields.Nested(LeaveInfoSchema(many=False)))
              extra_work_days_list = fields.List(fields.Nested(ExtraWorkInfoSchema(many=False)))
              absent_days_list = fields.List(fields.Nested(DailyLogDefaultSchema(many=False)))
              shift_days_list = fields.List(fields.Nested(LeaveInfoSchema(many=False)))
              rest_days_list = fields.List(fields.Nested(DailyLogDefaultSchema(many=False)))

          work_report = fields.Nested(WD(many=False))
          employ_type = fields.Integer()

      pym = Payment.query.filter_by(id=payment_id, engineer_id=self.id).first()
      sc = PS(many=False)
      result = sc.dump(pym)
      return result


class LeaveInfoSchema(Schema):  # 请假/调休详情数据  用于工时界面展示
    id = fields.Int()
    leave_type = fields.String()
    start_date = fields.DateTime()
    end_date = fields.DateTime()
    duration = fields.Float()
    reason = fields.String()


class ExtraWorkInfoSchema(Schema):  # 加班详情数据  用于工时界面展示
    id = fields.Int()
    reason = fields.String()
    start_date = fields.DateTime(required=False)
    end_date = fields.DateTime(required=False)
    duration = fields.Float()


class EngineerEnterStatusSchema(Schema):
    status = fields.Function(lambda x: EnterProjectStatus.int2str(x.status))
    comment = fields.String()

    class EP(Schema):
        real_name = fields.String()

    engineer = fields.Nested(EP(many=False, unknown=EXCLUDE))


class EngineerPaymentWithWorkReport(BaseActionSchema):
    _permission_roles = ['om', 'pm', 'purchase', 'company_om', 'engineer']
    action = 'payment_with_work_report'
    ModelClass = Engineer

    id = fields.Integer()


class EngineerRenewOrderSchema(BaseActionSchema):
    _permission_roles = ['puchase', 'company_om']
    action = 'renew_order'
    ModelClass = Engineer

    # auto_renew = fields.Integer()
    renew_cycle = fields.Integer()
    work_content = fields.String()
    service_type = fields.String()


class EngineerChangePmSchema(BaseActionSchema):
    _permission_roles = ['purchase', 'company_om']
    ModelClass = Engineer
    action = 'to_pm'

    new_pm_id = fields.Integer()
    old_pm_id = fields.Integer()


class EngineerFileImagesSchema(Schema):
    images = fields.Function(lambda x: Engineer.turn_pdf2img(Engineer()))


class Education(Base):
  __tablename__ = 'education'
  engineer_id = db.Column(db.Integer, db.ForeignKey('engineer.id'))
  start_date = db.Column(db.Date(), nullable=False, doc="开始时间")
  end_date = db.Column(db.Date(), nullable=False, doc="结束时间")
  school = db.Column(db.String(32))
  edu_college_type = db.Column(db.String(8), doc="学校类型")
  edu_college_rank = db.Column(db.String(5), doc="学校排名")
  edu_college_dept = db.Column(db.String(255), doc="院系")
  edu_major = db.Column(db.String(32), doc="专业")
  edu_recruit = db.Column(db.String(2), doc="是否统招")
  edu_gpa = db.Column(db.Float, doc="gpa 成绩")
  degree = db.Column(db.String(8), doc="学历")
  degree_norm = db.Column(db.String(255), doc="学历（规范化）")  
  is_highest = db.Column(db.Integer())

  @classmethod
  def post(cls, **kwargs):
    schema = EducationPostSchema(many=False, unknown=EXCLUDE)
    data = schema.load(kwargs)
    m = cls(**data)
    m.save()
    m.update_highest()

    e = Engineer.query.get(m.engineer_id)
    e.s_education = ','.join(['{}-{}-{}'.format(x.school, x.major, x.degree) for x in e.education])[:64]
    e.save()

    return m

  def update_highest(self):
    xueli = {"高中": 1, "大专": 2, "本科": 3, "硕士": 4, "博士": 5}
    es = Education.query.filter_by(engineer_id=self.engineer_id).all()
    h = None
    for e in es:
        e.update(is_highest=0)
        if not h:
            h = e
        else:
            if xueli[h.degree] < xueli[e.degree]:
                h = e
    if h:
        h.is_highest = 1
        h.save()
        e = Engineer.query.filter_by(id=self.engineer_id).first()
        e.highest_education_id = h.id
        e.save()


class EducationPutSchema(BasePutSchema):
    _permission_roles = ['om', 'company_om', 'purchase']

    start_date = fields.Date(required=True)
    end_date = fields.Date(required=True)
    school = fields.String(required=True)
    major = fields.String(required=True)
    degree = fields.String(required=True)

class WrittenInterviewInfo(Base):
    """笔面试信息"""
    __tablename__ = 'written_interview_info'
    engineer_id = db.Column(db.Integer, db.ForeignKey('engineer.id'))
    offer_id = db.Column(db.Integer, db.ForeignKey('offer.id'))
    recommend_time = db.Column(db.Date, doc="推荐时间")
    recommend_person = db.Column(db.String(32), doc="推荐人")
    written_score = db.Column(db.Float, doc="笔试成绩")
    written_total_num = db.Column(db.Integer(), doc="笔试题目数")
    written_num = db.Column(db.Float, doc="笔试答题数")
    single_choice_score = db.Column(db.Float, doc="单选题得分")
    problem_score = db.Column(db.Float, doc="应用题得分")
    design_problem_score = db.Column(db.Float, doc="设计与应用题得分")
    thought_score = db.Column(db.Float, doc="思维题得分")
    written_start = db.Column(db.DateTime, doc="笔试开始时间")
    written_end = db.Column(db.DateTime, doc="笔试结束时间")
    written_time = db.Column(db.Float, doc="笔试题答卷时长")
    written_cut_num = db.Column(db.Float, doc="笔试答卷切换次数")
    written_rank = db.Column(db.Float, doc="笔试成绩排名")
    interview_score = db.Column(db.Float, doc="面试成绩")
    interview_num = db.Column(db.Float, doc="面试题目数")
    interview_skill_score = db.Column(db.Float, doc="面试技术题得分")
    interview_quality_score = db.Column(db.Float, doc="面试素质题得分")
    interview_rank = db.Column(db.Float, doc="面试成绩排名")
    interview_start = db.Column(db.DateTime, doc="面试开始时间")
    interview_end = db.Column(db.DateTime, doc="面试结束时间")
    interview_time = db.Column(db.Float, doc="面试时长")

class WrittenInterviewInfoDefaultSchema(Schema):
    engineer_id = fields.Integer()
    offer_id = fields.Integer()
    recommend_person = fields.String()
    recommend_time = fields.Date()
    written_score = fields.Float()
    written_total_num = fields.Integer()
    written_num = fields.Integer()
    single_choice_score = fields.Float()
    problem_score = fields.Integer()
    design_problem_score = fields.Float()
    thought_score = fields.Float()
    written_start = fields.DateTime()
    written_end = fields.DateTime()
    written_time = fields.Float()
    written_cut_num = fields.Integer()
    written_rank = fields.Integer()
    interview_score = fields.Float()
    interview_num = fields.Integer()
    interview_skill_score = fields.Float()
    interview_quality_score = fields.Float()
    interview_rank = fields.Integer()
    interview_start = fields.DateTime()
    interview_end = fields.DateTime()
    interview_time = fields.Float()

class JobExperience(Base):
    """工作经验"""
    __tablename__ = "job_experience"
    engineer_id = db.Column(db.Integer, db.ForeignKey('engineer.id'))
    start_date = db.Column(db.Date, doc="开始时间")
    end_date = db.Column(db.Date, doc="结束时间")
    company_name = db.Column(db.String(16), doc="公司名称")
    company_nature = db.Column(db.String(8), doc="公司性质")
    company_size = db.Column(db.Integer(), doc="公司规模")
    company_desc = db.Column(db.String(32), doc="公司描述")
    industry = db.Column(db.String(8), doc="行业")
    position = db.Column(db.String(8), doc="职位")
    dept = db.Column(db.String(8), doc="所在部门")
    nature = db.Column(db.String(8), doc="工作性质")
    staff = db.Column(db.Integer(), doc="下属人数")
    report_to = db.Column(db.String(8), doc="汇报对象")
    location = db.Column(db.String(16), doc="工作地点")
    why_leave = db.Column(db.String(32), doc="离职原因")
    duaration = db.Column(db.String(8), doc="持续时间")
    capacity = db.Column(db.String(16), doc="工作能力")
    content = db.Column(db.String(128), doc="工作内容")

class JobExperienceDefaultSchema(Schema):
    engineer_id = fields.Integer()
    start_date = fields.String()
    end_date = fields.String()
    company_name = fields.String()
    company_nature = fields.String()
    company_size = fields.String()
    company_desc = fields.String()
    industry = fields.String()
    position = fields.String()
    dept = fields.String()
    nature = fields.String()
    staff = fields.String()
    report_to = fields.String()
    location = fields.String()
    why_leave = fields.String()
    duaraton = fields.String()
    capacity = fields.String()
    content = fields.String()

class ProjectExperience(Base):
    """项目经验"""
    __tablename__ = "project_experience"
    engineer_id = db.Column(db.Integer, db.ForeignKey('engineer.id'))
    start_date = db.Column(db.Date, doc="开始时间")
    end_date = db.Column(db.Date, doc="结束时间")
    name = db.Column(db.String(16), doc="项目名称")
    company_name = db.Column(db.String(16), doc="公司名称")
    position = db.Column(db.String(8), doc="职位")
    content = db.Column(db.String(128), doc="项目内容")
    resp = db.Column(db.String(128), doc="项目职责")

class ProjectExperienceDefaultSchema(Schema):
    engineer_id = fields.Integer()
    start_date = fields.String()
    end_date = fields.String()
    name = fields.String()
    company_name = fields.String()
    position = fields.String()
    content = fields.String()
    resp = fields.String()

class Language(Base):
    """语言技能"""
    __tablename__ = "language"
    engineer_id = db.Column(db.Integer, db.ForeignKey('engineer.id'))
    name = db.Column(db.String(8), doc="语言名称")
    level = db.Column(db.String(8), doc="熟练程度")
    read_write = db.Column(db.String(8), doc="读写能力")
    listen_speak = db.Column(db.String(8), doc="听说能力")

class LanguageDefaultSchema(Schema):
    engineer_id = fields.Integer()
    name = fields.String()
    level = fields.String()
    read_write = fields.String()
    listen_speak = fields.String()

class Langcert(Base):
    """语言证书列表"""
    __tablename__ = "langcert"
    engineer_id = db.Column(db.Integer, db.ForeignKey('engineer.id'))
    lang = db.Column(db.String(8), doc="语言")
    name = db.Column(db.String(8), doc="证书名称")
    score = db.Column(db.Float, doc="成绩")

class LangcertDefaultSchema(Schema):
    engineer_id = fields.Integer()
    lang = fields.String()
    name = fields.String()
    score = fields.Float()

class Ability(Base):
  engineer_id = db.Column(db.Integer, db.ForeignKey('engineer.id'))
  name = db.Column(db.String(8), doc="技能名称")
  level = db.Column(db.String(8), doc="熟练程度")
  skills_time = db.Column(db.String(8), doc="技能使用时间")

  @classmethod
  def post(cls, **kwargs):
    schema = AbilityPostSchema(many=False, unknown=EXCLUDE)
    data = schema.load(kwargs)
    m = cls(**data)
    m.save()
    e = Engineer.query.get(m.engineer_id)
    e.s_ability = ','.join([x.name for x in e.ability])[:64]
    e.save()
    return m

class AbilityDefaultSchema(Schema):
    engineer_id = fields.Integer()
    name = fields.String()
    level = fields.String()
    skills_time = fields.String()

class AbilityPutSchema(BasePutSchema):
  _permission_roles = ['om', 'company_om', 'purchase']

  name = fields.Str()
  level = fields.Str()


class InterviewStatus(BaseStatus):
    '''
    面试状态
    '''
    cv_new = 1  # 待筛-待查看
    cv_read = 2  # 待筛-已查看
    cv_pass = 3  # 待筛-约面试
    cv_reject = 0  # 反馈-淘汰（简历驳回）

    interview_new = 5  # 待面
    reject_by_engineer = -4  # 工程师拒绝
    interview_pass = 9  # 反馈-已通过（面试成功）
    interview_reject = -8  # 反馈-未通过（面试不通过）
    interview_undetermined = 6  # 反馈-待定（面试完没决定）
    interview_absent = -7  # 反馈-未面试（缺席未面试）

    cancel_entry = -10
    entry_new = 11  # 提交入职
    entry_pass = 13  # 入职审批通过
    entry_reject = -12  # 入职被据

    enter_project_reject = -15  # 入项拒绝
    enter_project_pass = 14  # 入项通过

    om_pass = 17  # 平台通过
    om_reject = -16  # 平台拒绝

    entering_project = 18,  # 正在进行入职材料审批

    status_code = {
        "cv_reject": 0,  # 简历被项目经理拒绝
        "cv_new": 1,  # 新推且项目经理未处理的简历
        "cv_read": 2,  # 新推，项目经理点击，但未处理的简历
        "cv_pass": 3,  # 项目经理通过的简历

        'reject_by_engineer': -4,  # 工程师拒绝面试
        "interview_new": 5,  # 新约面试
        "interview_undetermined": 6,  # 面试时间已过，项目经理未决定
        "interview_absent": -7,  # 工程师缺席面试
        "interview_reject": -8,  # 项目经理判定面试不合格
        "interview_pass": 9,  # 项目经理判定面试通过

        "cancel_entry": -10,  # 工程师拒绝入职（比如不满意级别)
        "entry_new": 11,  # 新发出的入职审批
        "entry_reject": -12,  # 入职被项目经理拒绝
        "entry_pass": 13,  # 入项被项目经理通过

        "enter_project_pass": 14,  # 入项被采购通过
        "enter_project_reject": -15,  # 入项被采购拒绝

        "om_reject": -16,  # 入项被平台运营拒绝
        "om_pass": 17,  # 入项被平台运营通过

        "entering_project": 18,  # 正在进行入职材料审批
    }


class InterviewPositionLevels(Schema):
    class OS(Schema):
        class PLS(Schema):
            id = fields.Integer()
            name = fields.String()
            money = fields.Float()

        position = fields.String()
        position_levels = fields.List(fields.Nested(PLS(many=False, unknown=EXCLUDE)))
        salary_type = fields.Integer()

    offer = fields.Nested(OS(many=False, unknown=EXCLUDE))


class Interview(Base):
    '''
    面试,前端的简历审核等也属于这个模型的责任
    '''
    __tablename__ = 'interview'

    updated = db.Column(db.Date)
    # 项目ID
    project_id = db.Column(db.Integer, db.ForeignKey('project.id'), nullable=False)
    # 公司ID
    company_id = db.Column(db.Integer, db.ForeignKey('company.id'), nullable=False)
    # 工程师ID
    engineer_id = db.Column(db.Integer, db.ForeignKey('engineer.id'), nullable=False)
    # 项目经理ID
    pm_id = db.Column(db.Integer, db.ForeignKey('pm.id'), nullable=False)
    # 需求(工作)ID
    offer_id = db.Column(db.Integer, db.ForeignKey('offer.id'), nullable=False)
    # 如果入职，填写入职时间
    entry_date = db.Column(db.Date)
    entry_before = db.Column(db.Date)

    position_id = db.Column(db.Integer, db.ForeignKey('position.id'), nullable=False)
    final_position_level_id = db.Column(db.Integer)
    # 原定级别
    reject_position_level_id = db.Column(db.Integer)
    result_note = db.Column(db.Text)

    # 由项目经理的可约时间导出成json格式的字符串。
    _pm_free_time = db.Column(db.Text)
    # 最终约定时间
    _appoint_time = db.Column(db.String(128))

    status = db.Column(db.Integer, index=True)
    note = db.Column(db.String(128))

    entry = db.relationship('Entry', backref='interview')

    # todo 会导致重复添加简历失败
    __table_args__ = (  # number name 检查联合唯一
        UniqueConstraint("offer_id", "engineer_id"),
    )

    def __repr__(self):
        return '{}-{}'.format('', '')

    @property
    def final_position_level(self):
        if not self.final_position_level_id:
            return None
        result = list(filter(lambda x: x.id == self.final_position_level_id, self.offer.position.position_levels))
        if len(result) == 0:
            return None
        return result[0]

    def action_status(self, **kwargs):
        if not self.offer.status == OfferStatus.open:
            raise NewComException('需求已关闭，不可操作', 500)
        status = kwargs['status']
        note = kwargs.get('note', None)
        if status == InterviewStatus.cv_pass:
            pm_free_time = kwargs.get('pm_free_time', None)
            if not pm_free_time:
                raise NewComException('请提交可面试时间', 501)
            self._pm_free_time = json.dumps(pm_free_time)
        if status == InterviewStatus.interview_new:
            appoint_time = kwargs['appoint_time']
            self._appoint_time = json.dumps(appoint_time)
        if status == InterviewStatus.interview_pass:
            # 项目经理确认面试通过, 确定一个入项级别
            final_position_level_id = kwargs.get('final_position_level_id', None)
            entry_before = kwargs.get('entry_before', None)
            if not entry_before:
                raise NewComException('请输入入项截止日期', 501)
            if entry_before <= get_today():
                raise NewComException('入职必须在今日之后', 500)
            if not final_position_level_id:
                raise NewComException('请输入入项级别', 501)
            _ep = EnterProject.query.filter(EnterProject.engineer_id == self.engineer_id, EnterProject.ing != 0,
                                            EnterProject.status in [EnterProjectStatus.file_submit,
                                                                    EnterProjectStatus.file_om_reject,
                                                                    EnterProjectStatus.file_om_agree,
                                                                    EnterProjectStatus.file_pm_reject,
                                                                    EnterProjectStatus.file_pm_agree,
                                                                    EnterProjectStatus.file_company_reject,
                                                                    EnterProjectStatus.file_company_agree,
                                                                    EnterProjectStatus.om_reject,
                                                                    EnterProjectStatus.finish]).all()
            if _ep:
                raise NewComException('已存在入项流程', 500)

            ep = EnterProject.query.filter_by(interview_id=self.id).first()
            ey = Entry.query.filter_by(interview_id=self.id).first()
            if ep:  # 说明是运营设定级别不合适，被打回来的审批
                self.reject_position_level_id = final_position_level_id
                self.final_position_level_id = final_position_level_id
                self.entry_before = self.entry_date
                self.entry_date = entry_before
                ep.reject_position_level_id = ep.position_level_id
                ep.position_level_id = final_position_level_id
                ep.save()
                if ey:
                    ey.update(status=AuditStatus.modify, reject_position_level_id=self.reject_position_level_id,
                              position_level_id=final_position_level_id)
            else:
                self.final_position_level_id = final_position_level_id
                self.entry_before = self.entry_date = entry_before
                data = EnterProjectPostSchema(many=False).dump(self)
                data['interview_id'] = self.id
                data['offer_id'] = self.offer_id
                data['salary_type'] = self.offer.salary_type
                data['work_place'] = self.offer.work_place
                data['position_level_id'] = final_position_level_id
                EnterProject.post(**data)
                self.engineer.status = EngineerStatus.entering

        if status == InterviewStatus.cancel_entry:
            ep = EnterProject.query.filter_by(interview_id=self.id).first()
            if ep:
                ep.delete()
        if note:
            self.note = note
        self.status = status
        self.save()

    def action_entry(self, **kwargs):
        if not self.offer.status == OfferStatus.open:
            raise NewComException('需求已关闭，不可操作', 500)
        entry_date = kwargs['date']
        if entry_date <= get_today():
            raise NewComException('入职必须在今日之后', 500)
        if self.offer.entry_amount >= self.offer.amount:
            raise NewComException('入职人数已满', 500)

        note = kwargs.get('note', "")
        position_level_id = kwargs.get('position_level_id')
        if not position_level_id:
            raise NewComException('请确认入项级别', 500)

        # todo 下面逻辑修改为存储过程
        entry = Entry.query.filter_by(interview_id=self.id).first()
        if not entry:
            entry = Entry(interview_id=self.id, offer_id=self.offer_id, date=entry_date,
                          position_level_id=position_level_id, status=AuditStatus.submit,
                          engineer_id=self.engineer_id)
        else:
            entry.update(date=entry_date, position_level_id=position_level_id, status=AuditStatus.submit,
                         engineer_id=self.engineer_id)

        # 入项流程的建立
        ep = EnterProject.query.filter(EnterProject.interview_id == self.id).first()
        ep.status = EnterProjectStatus.engineer_agree
        if not position_level_id == self.final_position_level_id:
            self.reject_position_level_id = self.final_position_level_id
            self.final_position_level_id = position_level_id
            entry.update(reject_position_level_id=self.reject_position_level_id)
            ep.position_level_id = position_level_id
            ep.reject_position_level_id = self.reject_position_level_id
        copy_auth_info(entry, self)
        entry.save()
        ep.start_date = entry_date
        ep.save()

        self.note = note
        self.status = InterviewStatus.entry_new
        self.entry_date = entry_date
        self.save()
        return {'entry_id': entry.id}

    def action_change_entry_info(self):
        self.status = InterviewStatus.interview_new
        self.save()

    @property
    def pm_free_time(self):
        return json.loads(self._pm_free_time) if self._pm_free_time else []

    @property
    def appoint_time(self):
        return json.loads(self._appoint_time) if self._appoint_time else {}


class CareerStatus(BaseStatus):
    entering = 0
    on_duty = 1
    leaving = 2
    finish = 3


class CareerSimpleSchema(Schema):
    id = fields.Integer()
    start = fields.Date()
    end = fields.Date()
    company = fields.String()
    project = fields.String()
    pm = fields.String()

    class PLS(Schema):
        id = fields.Integer()
        name = fields.String()
        money = fields.Float()
        position = fields.String()

    position_level = fields.Nested(PLS(many=False))
    salary_type = fields.Integer()
    tax_free_rate = fields.Float()
    ware_fare = fields.Float()
    break_up_fee_rate = fields.Float()
    use_hr_service = fields.Bool()
    employ_type = fields.Integer()


class CareerManageSchema(Schema):
    engineer_id = fields.Integer()
    phone = fields.String()
    engineer_status = fields.Function(lambda x: CareerStatus.int2str(x.status))
    project = fields.String()
    pm = fields.String()
    ability_score = fields.Float()
    attitude_score = fields.Float()

    class ES(Schema):
        cv_name = fields.String()
        cv_path = fields.List(fields.String())
        id = fields.Integer()
        real_name = fields.String()

    engineer = fields.Nested(ES(many=False))

    class PLS(Schema):
        id = fields.Integer()
        name = fields.String()
        money = fields.Float()
        position = fields.String()

    position_level = fields.Nested(PLS(many=False))

    class COS(Schema):
        id = fields.Integer()
        start_date = fields.Date()
        end_date = fields.Date()
        expect_total_fee = fields.Float()
        finished_fee = fields.Float()
        auto_renew = fields.Integer()
        renew_cycle = fields.Float()
        status = fields.Function(lambda x: x.is_ing())

    orders = fields.List(fields.Nested(COS(many=False)))
    auto_renew = fields.Integer()
    renew_cycle = fields.Integer()
    salary_type = fields.String()
    employ_type = fields.String()
    id = fields.Integer()
    use_hr_service = fields.Bool()
    s_money = fields.Float()


class Career(Base):
    '''
    当发生调项目时，career会变，离职会终结career，加薪不会.
    '''
    __tablename__ = 'career'
    engineer_id = db.Column(db.Integer, db.ForeignKey('engineer.id'))
    real_name = db.Column(db.String(64), index=True)
    phone = db.Column(db.String(11), index=True)
    engineer_status = db.Column(db.Integer, index=True)
    # 能力评分
    ability_score = db.Column(db.Float)
    # 态度评分
    attitude_score = db.Column(db.Float)

    company_id = db.Column(db.Integer, db.ForeignKey('company.id'))
    company = db.relationship('Company', backref='career')
    project_id = db.Column(db.Integer, db.ForeignKey('project.id'))
    project = db.relationship('Project', backref='career')
    pm_id = db.Column(db.Integer, db.ForeignKey('pm.id'))
    pm = db.relationship('Pm', backref='career')
    interview_id = db.Column(db.Integer, db.ForeignKey('interview.id'))
    position_level_id = db.Column(db.Integer, db.ForeignKey('position_level.id'))
    position_id = db.Column(db.Integer, index=True)
    before_career_id = db.Column(db.Integer)
    position_level = db.relationship('PositionLevel', backref='career')
    salary_type = db.Column(db.Integer)
    employ_type = db.Column(db.Integer)  # 模式：0牛咖模式  1员工模式
    tax_free_rate = db.Column(db.Float)
    ware_fare = db.Column(db.Float)  # 社保
    break_up_fee_rate = db.Column(db.Float)
    work_place = db.Column(db.String(192))
    work_content = db.Column(db.String(255))
    auto_renew = db.Column(db.Integer)
    renew_cycle = db.Column(db.Integer)

    offer_id = db.Column(db.Integer, db.ForeignKey('offer.id'))
    start = db.Column(db.Date, nullable=False, doc="开始时间")
    end = db.Column(db.Date, doc="结束时间")
    rank = db.Column(db.Integer)

    status = db.Column(db.Integer, index=True)
    entry_files_checked = db.Column(db.Integer, index=True)

    payment = db.relationship('Payment', backref='career')
    interview = db.relationship('Interview', backref='career')

    s_ability = db.Column(db.String(64), index=True)
    s_education = db.Column(db.String(64), index=True)
    s_use_hr_service = db.Column(db.Integer(), index=True)
    s_money = db.Column(db.Float(), index=True)
    s_need_renew_order = db.Column(db.Integer(), index=True, default=0)

    def search_index(self):
        engineer = Engineer.query.filter_by(id=self.engineer_id).first()
        self.s_ability = ','.join([x.name for x in engineer.ability])[:64]
        self.s_education = ','.join([x.school + "-" + x.degree + '-' + x.major for x in engineer.education])[:64]
        self.s_use_hr_service = not self.use_hr_service
        self.s_money = self.position_level.money

        self.s_need_renew_order = 0
        orders = self.orders
        for order in orders:
            if order.is_ending():
                self.s_need_renew_order = 1
        self.save()

    @classmethod
    def create(cls, interview, position_level_id, level):
        if cls.query.filter_by(engineer_id=interview.engineer_id, project_id=interview.project_id).all():
            return False, '已存在的在职信息。'
        career = Career()
        career.engineer_id = interview.engineer_id
        career.company_id = interview.company_id
        career.project_id = interview.project_id
        career.offer_id = interview.offer_id
        career.position_level_id = position_level_id
        career.status = CareerStatus.entering

        interview.status = InterviewStatus.entry_pass
        engineer = Engineer.query.filter_by(id=interview.engineer_id).first()
        engineer.status = EngineerStatus.on_duty
        engineer.project_id = interview.project_id
        engineer.company_id = interview.company_id
        db.session.add(interview)
        db.session.add(career)
        engineer.now_career_id = career.id
        db.session.add(engineer)
        db.session.commit()
        return True, career

    def action_finish(self):
        audits = Audit.query.filter_by(engineer_id=self.engineer_id, status=AuditStatus.submit).all()
        if audits:
            raise NewComException('尚有未结束的审批未处理', 500)
        daily_logs = DailyLog.query.filter_by(engineer_id=self.engineer_id, status=DailyLogStatus.new).all()
        if daily_logs:
            raise NewComException('尚有未生成工作报告的工作日志', 500)
        self.status = CareerStatus.finish
        self.save()

    @property
    def use_hr_service(self):
        if self.interview_id:
            return 1
        return 0

    def action_order_renew_method(self, **kwargs):
        # todo 检查逻辑
        self.auto_renew = kwargs.get('auto_renew')
        self.renew_cycle = kwargs.get('renew_cycle')
        self.save()

    def pre_renew_order(self):
        pass


class OrderRenewMethodSchema(BaseActionSchema):
    _permission_roles = ['purchase', 'company_om']
    ModelClass = Career
    action = 'order_renew_method'

    auto_renew = fields.Integer(required=True)
    renew_cycle = fields.Integer()


class DailyLogType(object):
    normal_work = 'normal_work'
    extra_work = 'extra_work'
    shift = 'shift'
    leave = 'leave'
    normal_rest = 'normal_rest'
    holiday = 'holiday'

    @classmethod
    def en2cn(cls, en):
        return \
            {'normal_work': '', 'normal_rest': '休息', 'leave': '请假', 'shift': '调休', 'extra_work': '加班',
             'holiday': '节假日'}[en]


class DailyLogStatus(BaseStatus):
    checked = 1
    new = 2


class DailyLog(Base):
    engineer_id = db.Column(db.Integer, db.ForeignKey('engineer.id'))
    company_id = db.Column(db.Integer, db.ForeignKey('company.id'))
    project_id = db.Column(db.Integer, db.ForeignKey('project.id'))
    pm_id = db.Column(db.Integer, db.ForeignKey('pm.id'))
    career_id = db.Column(db.Integer, db.ForeignKey('career.id'))
    engineer_company_order_id = db.Column(db.Integer, db.ForeignKey('engineer_company_order.id'))
    date = db.Column(db.Date, nullable=False)
    content = db.Column(db.String(256))

    duration = db.Column(db.Float, default=0)  # 时长
    origin_type = db.Column(db.String(16))  # 'work' or 'off'

    # 待删除字段
    adjust_type = db.Column(db.String(16))  # 1加班 extra_work,
    adjust_id = db.Column(db.Integer)

    leave_time = db.Column(db.Float, default=0)
    extra_work_time = db.Column(db.Float, default=0)
    shift_time = db.Column(db.Float, default=0)
    absent_time = db.Column(db.Float, default=0)

    status = db.Column(db.Integer, default=DailyLogStatus.new, index=True)

    __table_args__ = (
        db.UniqueConstraint('engineer_id', 'date', name='uix_daily_log_engineer_id_date'),
    )

    @property
    def note(self):
        # 休息， 加班， 调休， 请假
        # off： 休息， work ：啥都不显示， shift：调休， leave:请假
        en_cn = {'off'}
        if self.adjust_type == 'none' or self.adjust_type is None:
            return DailyLogType.en2cn(self.origin_type)
        else:
            return DailyLogType.en2cn(self.adjust_type)

    @property
    def is_workday(self):
        """是否展示填写功能：判断是否是工作日，工作日返回False不展示"""
        return is_work_day(self.date)

    def action_modify(self, content, duration):
        engineer = Engineer.query.filter_by(id=self.engineer_id).first()
        # 正在审核或审核通过，当然是不能修改的
        if self.status in [AuditStatus.checked, AuditStatus.submit]:
            raise NewComException('当月月报审核或审核通过，不可修改！', 500)

        if duration not in range(25):
            raise NewComException('错误的时长', 500)

        # if now_career.end and now_career.end < get_today():
        #     raise NewComException('离职后不可填写日报', 500)

        if self.date < engineer.career[-1].start:
            raise NewComException('还未入职', 500)

        if self.date > get_today():
            raise NewComException('日志不可提前填写', 500)

        # 休息日不允许修改
        if self.origin_type in [DailyLogType.normal_rest, DailyLogType.holiday]:
            raise NewComException('该日没有审批通过的加班审批', 500)
        self.update(content=content, duration=duration)

    @classmethod
    def auto_create(cls, engineer_model, date):
        eco = EngineerCompanyOrder.query.filter(and_(EngineerCompanyOrder.engineer_id == engineer_model.id,
                                                     EngineerCompanyOrder.start_date <= date,
                                                     EngineerCompanyOrder.end_date >= date)).first()
        if not eco:
            raise NewComException('存在订单周期未覆盖的日期', 501)
        if is_work_day(date):
            origin_type = DailyLogType.normal_work
        elif is_holiday(date):
            origin_type = DailyLogType.holiday
        else:
            origin_type = DailyLogType.normal_rest
        dl = DailyLog(engineer_id=engineer_model.id, date=date,
                      career_id=engineer_model.now_career_id,
                      engineer_company_order_id=eco.id, origin_type=origin_type)
        copy_auth_info(dl, engineer_model)
        dl.save()

    @classmethod
    @lru_cache()
    def check_uncreated(cls, engineer_id, today):
        """
        检查是否有应存在但不存在的日志， 如上月已有工时报告，则只检查当月。如不存在，还要检查上月.
        :param engineer_id:
        :param today: 缓存更换的标识符
        :return:
        """
        engineer_model = Engineer.query.get(engineer_id)
        if not engineer_model.now_career_id:
            career = Career.query.filter_by(engineer_id=engineer_id).order_by(db.desc(Career.id)).first()
            if not career:
                raise NewComException('未查询到入职信息', 500)
            return career.end + dt.timedelta(days=1)
        else:
            career = Career.query.get(engineer_model.now_career_id)

        # 先来判断一下从哪一天开始检查
        last_year_month = get_last_year_month()
        if WorkReport.query.filter_by(engineer_id=engineer_id, year_month=last_year_month, status=AuditStatus.checked) \
                .count() == 0:
            check_start, _ = month_first_end_date(last_year_month / 100, last_year_month % 100)
        else:
            check_start, _ = month_first_end_date(today.year, today.month)
        check_start = career.start if career.start > check_start else check_start

        # 查询出检查日期以来的所有日报
        exist_daily_logs = DailyLog.query.filter(DailyLog.engineer_id == engineer_id,
                                                 DailyLog.date >= check_start).all()
        exist_days = [daily_log.date for daily_log in exist_daily_logs]

        today = get_today()
        check_end = career.end if career.end else today
        if check_start <= today:
            for day in days_between(check_start, check_end):
                if str_to_date(day) not in exist_days:
                    cls.auto_create(engineer_model, str_to_date(day))
        return check_start

    @classmethod
    def get_latest_items(cls, engineer_id):
        today = get_today()
        check_start = cls.check_uncreated(engineer_id, today)
        result = cls.get_items_with_pages(engineer_id=engineer_id, gte_date=check_start, sort_date=-1)
        return result


class AuditType(object):
    extra_work = 'extra_work'
    leave = 'leave'
    work_report = 'work_report'
    entry = 'entry'
    resign = 'resign'
    promote = 'promote'


class AuditStatus(BaseStatus):
    submit = 0
    checked = 1
    reject = -1
    modify = -2


class Audit(Base):
    __tablename__ = 'audit'

    engineer_id = db.Column(db.Integer, db.ForeignKey('engineer.id'))
    pm_id = db.Column(db.Integer, db.ForeignKey('pm.id'))
    company_id = db.Column(db.Integer, db.ForeignKey('company.id'))
    project_id = db.Column(db.Integer, db.ForeignKey('project.id'))

    audit_type = db.Column(db.String(16))

    comment = db.Column(db.String(128))
    status = db.Column(db.Integer, default=AuditStatus.submit, index=True)

    __mapper_args__ = {
        'polymorphic_identity': 'normal',
        'polymorphic_on': audit_type
    }


class WorkReportWithSimplePayment(Schema):
    class EngineerSchema(Schema):
        pre_username = fields.String()
        real_name = fields.String()
        project = fields.String()

    class PS(Schema):
        id = fields.Integer()
        company_pay = fields.Float()
        amerce = fields.Float()
        status = fields.Function(lambda x: PaymentStatus.int2str(x.status))

    Payment = fields.List(fields.Nested(PS(many=False)))
    company_pay = fields.Float()
    engineer = fields.Nested(EngineerSchema(many=False))
    status = fields.Function(lambda x: AuditStatus.int2str(x.status))


class WorkReportWithPayment(Schema):
    class EngineerSchema(Schema):
        pre_username = fields.String()
        real_name = fields.String()
        id = fields.Integer()

    year_month = fields.Int()
    work_days = fields.Float()
    leave_days = fields.Float()
    extra_work_days = fields.Float()
    absent_days = fields.Float()
    shift_days = fields.Float()
    attitude_score = fields.Float()
    ability_score = fields.Float()
    out_project_days = fields.Float()
    total_score = fields.Float()
    rest_days = fields.Float()
    engineer = fields.Nested(EngineerSchema(many=False))
    company_pay = fields.Float()
    rank = fields.Int()
    status = fields.Function(lambda x: AuditStatus.int2str(x.status))
    shift_duration = fields.Float()
    work_duration = fields.Float()
    leave_duration = fields.Float()
    extra_work_duration = fields.Float()
    work_extra_duration = fields.Float()
    holiday_extra_duration = fields.Float()
    weekend_extra_duration = fields.Float()

    class PS(Schema):
        id = fields.Integer()
        company_pay = fields.Float()
        amerce = fields.Float()
        status = fields.Function(lambda x: PaymentStatus.int2str(x.status))
        tax = fields.Float()
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
        station_salary = fields.Float()
        extra_salary = fields.Float()

    Payment = fields.List(fields.Nested(PS(many=False)))

    class CS(Schema):
        start = fields.Date()
        interview_id = fields.Integer()
        use_hr_service = fields.Integer()
        salary_type = fields.Integer()
        pm = fields.String()
        project = fields.String()

        class PLS(Schema):
            position = fields.String()
            name = fields.String()
            money = fields.Float()

        position_level = fields.Nested(PLS(many=False, unknown=EXCLUDE))

    career = fields.Nested(CS(many=False, unknown=EXCLUDE))


class WorkReport(Audit):
    __tablename__ = 'work_report'

    id = db.Column(db.Integer, db.ForeignKey('audit.id'), primary_key=True)
    year_month = db.Column(db.Integer)

    work_days = db.Column(db.Float)
    leave_days = db.Column(db.Float)
    extra_work_days = db.Column(db.Float)
    absent_days = db.Column(db.Float)
    shift_days = db.Column(db.Float)
    rest_days = db.Column(db.Float)
    out_project_days = db.Column(db.Float)
    shift_duration = db.Column(db.Float)

    work_duration = db.Column(db.Float)
    leave_duration = db.Column(db.Float)
    extra_work_duration = db.Column(db.Float)

    work_extra_duration = db.Column(db.Float)
    holiday_extra_duration = db.Column(db.Float)
    weekend_extra_duration = db.Column(db.Float)
    extra_station_duration = db.Column(db.Float)

    career_id = db.Column(db.Integer, db.ForeignKey('career.id'))

    # 能力评分
    ability_score = db.Column(db.Float)
    # 态度评分
    attitude_score = db.Column(db.Float)
    # 总分
    total_score = db.Column(db.Float)
    # 排名
    rank = db.Column(db.Integer)
    career = db.relationship('Career', backref="work_report")

    @staticmethod
    def get_month_daily_logs(engineer_id, year_month, career_id):
        start_date, end_date = month_first_end_date(year_month / 100, year_month % 100)
        end_date = dt.datetime(end_date.year, end_date.month, end_date.day, 23, 59, 59)
        daily_logs = DailyLog.query.filter(DailyLog.engineer_id == engineer_id) \
            .filter(DailyLog.career_id == career_id).filter(DailyLog.date.between(start_date, end_date)).all()
        return list(daily_logs)

    @staticmethod
    def get_month_leaves(self):  # 获取工时报告月份中请假审批
        start_date, end_date = month_first_end_date(self.year_month / 100, self.year_month % 100)
        end_date = dt.datetime(end_date.year, end_date.month, end_date.day, 23, 59, 59)
        leaves = Leave.query.filter_by(career_id=self.career_id).filter(
            Leave.start_date.between(start_date, end_date)).all()
        return list(leaves)

    @staticmethod
    def get_month_extraworks(self):  # 获取工时报告月份中加班审批
        start_date, end_date = month_first_end_date(self.year_month / 100, self.year_month % 100)
        end_date = dt.datetime(end_date.year, end_date.month, end_date.day, 23, 59, 59)
        extra_works = ExtraWork.query.filter_by(career_id=self.career_id).filter(
            ExtraWork.start_date.between(start_date, end_date)).all()
        return list(extra_works)

    @property
    def days(self):
        if not hasattr(self, '_days'):
            _days = self.get_month_daily_logs(self.engineer_id, self.year_month, self.career_id)
            setattr(self, '_days', _days)
        return getattr(self, '_days')

    @classmethod
    def filter_list_days(cls, dayslist):  # 过滤审批中得重复时间，输出合格工时，类型为字典{'str(datetime)':'duration'}
        daysdict = dict()
        for i in dayslist:
            start_time = change_datetime_date(i.start_date)
            str_start_time = start_time.strftime('%Y%m%d')
            end_time = change_datetime_date(i.end_date)
            str_end_time = end_time.strftime('%Y%m%d')
            days = days_num_between(i.start_date, i.end_date)
            if days == 1:
                if str_start_time not in daysdict.keys():
                    daysdict[str_start_time] = [[i.start_date.hour, i.end_date.hour]]
                else:
                    daysdict[str_start_time].append([i.start_date.hour, i.end_date.hour])
            else:
                if str_start_time not in daysdict.keys():
                    daysdict[str_start_time] = [[i.start_date.hour, 24]]
                else:
                    daysdict[str_start_time].append([i.start_date.hour, 24])
                if str_end_time not in daysdict.keys():
                    daysdict[str_end_time] = [[0, i.end_date.hour]]
                else:
                    daysdict[str_start_time].append([0, i.end_date.hour])
                while end_time - start_time > dt.timedelta(1):
                    start_time = dt.date(start_time.year, start_time.month, start_time.day + 1)
                    str_start_time = start_time.strftime('%Y%m%d')
                    daysdict[str_start_time] = [[0, 24]]
        return daysdict

    @staticmethod
    def filter_work_days(daily_logs, leaves):  # 过滤日报，请假审批，输出list(dailylog),work_days,duration,daily_logs_durations
        daily_logs = list(
            filter(lambda x: x.duration and x.duration > 0 and x.origin_type == 'normal_work', daily_logs))
        leaves_days = WorkReport.filter_leave_days(leaves)[3]
        daily_logs_durations = dict()
        for i in daily_logs:  # 判定是否存在事后请假，存在则计算真实工作时长。
            daily_logs_durations[i.date] = 8 if i.duration > 8 else i.duration
            if i.date.strftime('%Y%m%d') in leaves_days.keys():
                leave_duration = leaves_days.get(i.date.strftime('%Y%m%d'), 0)
                if leave_duration + i.duration < 8:
                    daily_logs_durations[i.date] = i.duration
                else:
                    daily_logs_durations[i.date] = 8 - leave_duration
        work_days = len(daily_logs)
        durations = sum(daily_logs_durations.values())
        return daily_logs, work_days, durations, daily_logs_durations

    @property
    def work_days_list(self):
        return self.filter_work_days(self.days, self.get_month_leaves(self))[0]

    @staticmethod
    def filter_leave_days(leaves):
        leaves = list(
            filter(lambda x: x.leave_type in ['personal', 'sick'] and x.status == AuditStatus.checked, leaves))
        leaves_days = WorkReport.filter_list_days(leaves)

        for k, v in leaves_days.items():
            duration = 0
            for j in v:
                duration += j[1] - j[0]
            if duration > 8:
                duration = 8
            leaves_days[k] = duration
        leaves_num = len(leaves_days)
        duration = sum(leaves_days.values())

        return leaves, leaves_num, duration, leaves_days

    @property
    def leave_days_list(self):
        return list(filter(lambda x: x.leave_type in ['personal', 'sick'] and x.status == AuditStatus.checked,
                           self.get_month_leaves(self)))

    @staticmethod
    def filter_extra_work_days(extra_works, daily_logs, leaves):
        extra_works = list(filter(lambda x: x.duration > 0 and x.status == AuditStatus.checked, extra_works))
        extra_works_days = WorkReport.filter_list_days(extra_works)
        leave_durations = WorkReport.filter_work_days(daily_logs, leaves)[3]
        extra_station_duration = dict()

        for k, v in extra_works_days.items():
            duration = 0
            tem_extra_duration = 0  # 缓存时长，用于判断工位费【工位费超过8小时按8小时收取】
            for j in v:
                duration += j[1] - j[0]
                tem_extra_duration += j[1] - j[0]
            year, month, day = dt.datetime.strptime(k, '%Y%m%d').timetuple()[:3]
            kt = dt.date(year, month, day)
            if leave_durations.get(kt, 0) + tem_extra_duration > 8:
                tem_extra_duration = 8 - leave_durations.get(kt, 0)
            extra_station_duration[k] = tem_extra_duration
            extra_works_days[k] = duration
        extra_works_num = len(extra_works_days)
        duration = sum(extra_works_days.values())
        extra_station_duration = sum(extra_station_duration.values())
        work_extra_duration = sum([v for k, v in extra_works_days.items() if is_work_day(k)])
        holiday_extra_duration = sum([v for k, v in extra_works_days.items() if is_holiday(k)])
        weekend_extra_duration = duration - work_extra_duration - holiday_extra_duration

        return extra_works, extra_works_num, duration, work_extra_duration, holiday_extra_duration, \
               weekend_extra_duration, extra_station_duration

    @property
    def extra_work_days_list(self):
        return list(
            filter(lambda x: x.duration > 0 and x.status == AuditStatus.checked, self.get_month_extraworks(self)))

    @staticmethod
    def filter_absent_days(daily_logs, leaves):
        leaves = list(
            filter(lambda x: x.leave_type in ['personal', 'sick'] and x.status == AuditStatus.checked, leaves))
        leaves_days = WorkReport.filter_list_days(leaves)
        return list(filter(lambda x:
                           ((x.adjust_type or x.origin_type) == DailyLogType.normal_work) and
                           (not x.duration or x.duration < 1) and (
                                   ''.join(str(x.date).split('-')) not in list(leaves_days.keys()))
                           , daily_logs))

    @property
    def absent_days_list(self):
        return self.filter_absent_days(self.days, self.get_month_leaves(self))

    @staticmethod
    def filter_shift_days(shifts):
        shifts = list(filter(lambda x: x.leave_type == DailyLogType.shift, shifts))
        shifts_days = WorkReport.filter_list_days(shifts)
        for k, v in shifts_days.items():
            duration = 0
            for j in v:
                duration += j[1] - j[0]
                if duration > 8:
                    duration = 8
            shifts_days[k] = duration
        shifts_num = len(shifts_days)
        durations = sum(shifts_days.values())
        return shifts, shifts_num, durations

    @property
    def shift_days_list(self):
        return list(filter(lambda x: x.leave_type == DailyLogType.shift, self.get_month_leaves(self)))

    @staticmethod
    def filter_rest_days(daily_logs):
        return list(
            filter(lambda x: x.duration < 1 and x.origin_type in [DailyLogType.normal_rest, DailyLogType.holiday],
                   daily_logs))

    @property
    def rest_days_list(self):
        return self.filter_rest_days(self.days)

    @staticmethod
    def statistic_of(**kwargs):
        year_month = int(kwargs['year_month'])
        engineer_id = kwargs['engineer_id']
        DailyLog.check_uncreated(engineer_id, get_today())
        involve_engineer = Engineer.query.get(engineer_id)
        if involve_engineer.now_career_id:
            work_report = WorkReport.query.filter_by(career_id=involve_engineer.now_career_id,
                                                     year_month=year_month).first()
        else:
            work_report = WorkReport.query.filter_by(engineer_id=engineer_id, year_month=year_month).first()
        if work_report:
            status = work_report.status
            _id = work_report.id
            career_id = work_report.career_id
        else:
            status = 'un_submit'
            career_id = involve_engineer.now_career_id
            _id = None
        result = dict(year_month=year_month, status=status, id=_id)
        daily_logs = WorkReport.get_month_daily_logs(engineer_id, year_month, career_id)
        start_date, end_date = month_first_end_date(year_month / 100, year_month % 100)
        end_date = dt.datetime(end_date.year, end_date.month, end_date.day, 23, 59, 59)
        leaves = Leave.query.filter_by(career_id=career_id).filter(
            Leave.start_date.between(start_date, end_date)).all()
        extra_works = ExtraWork.query.filter_by(career_id=career_id).filter(
            ExtraWork.start_date.between(start_date, end_date)).all()

        work_result = WorkReport.filter_work_days(daily_logs, leaves)
        result['work_days_list'] = work_result[0]
        result['work_days'] = work_result[1]
        result['work_duration'] = work_result[2]

        leave_result = WorkReport.filter_leave_days(leaves)
        result['leave_days_list'] = leave_result[0]
        result['leave_days'] = leave_result[1]
        result['leave_duration'] = leave_result[2]

        extra_result = WorkReport.filter_extra_work_days(extra_works, daily_logs, leaves)
        result['extra_work_days_list'] = extra_result[0]
        result['extra_work_days'] = extra_result[1]
        result['extra_work_duration'] = extra_result[2]
        result['work_extra_duration'] = extra_result[3]
        result['holiday_extra_duration'] = extra_result[4]
        result['weekend_extra_duration'] = extra_result[5]
        result['extra_station_duration'] = extra_result[6]

        shift_result = WorkReport.filter_shift_days(leaves)
        result['shift_days_list'] = shift_result[0]
        result['shift_days'] = shift_result[1]
        result['shift_duration'] = shift_result[2]

        result['absent_days_list'] = WorkReport.filter_absent_days(daily_logs, leaves)
        result['absent_days'] = len(result['absent_days_list'])

        result['rest_days_list'] = WorkReport.filter_rest_days(daily_logs)
        result['rest_days'] = len(result['rest_days_list'])
        return result

    def cal_out_project_days(self, involve_engineer):
        work_report = self
        unwork_days_before_entry = 0
        unwork_days_after_resign = 0
        one_day = dt.timedelta(days=1)
        month = work_report.year_month % 100
        year = (work_report.year_month - month) // 100
        month_begin, month_end = month_first_end_date(year, month)
        if int_year_month(involve_engineer.now_career.start) == work_report.year_month:
            cursor = month_begin
            while cursor < involve_engineer.now_career.start:
                if is_work_day(cursor):
                    unwork_days_before_entry += 1
                cursor = cursor + one_day
        if (int_year_month(involve_engineer.now_career.end) or 222201) == work_report.year_month:
            cursor = involve_engineer.now_career.end
            while cursor <= month_end:
                if is_work_day(cursor):
                    unwork_days_after_resign += one_day.days
                cursor = cursor + one_day

        return unwork_days_after_resign + unwork_days_before_entry

    @classmethod
    def post(cls, schema, engineer_id, year_month):
        engineer = Engineer.query.get(engineer_id)
        already = cls.query.filter_by(engineer_id=engineer_id, career_id=engineer.now_career_id,
                                      year_month=year_month).first()
        if already:
            return already.action_resubmit()
        if year_month > get_last_year_month(get_today()):
            if not engineer.now_career.end:
                raise NewComException('如果没有申请离职，不可提前提交工作报告', 500)
            if not engineer.now_career.end <= get_today():
                raise NewComException('未到达离职日期，不可提前提交工作报告。', 500)

        statistic = cls.statistic_of(engineer_id=engineer_id, year_month=year_month)
        kwargs = schema.load(statistic)
        wr = cls(**kwargs)
        wr.out_project_days = wr.cal_out_project_days(engineer)
        copy_auth_info(wr, engineer)
        wr.update(engineer_id=engineer_id, career_id=engineer.now_career_id, status=AuditStatus.submit)
        daily_logs = cls.get_month_daily_logs(engineer_id, year_month, engineer.now_career_id)
        for daily_log in daily_logs:
            daily_log.update(status=AuditStatus.submit)
            daily_log.save()

    @staticmethod
    def update_rank(project_id, year_month):
        current_app.logger.error('in update rank')
        db.session.commit()
        work_reports = WorkReport.query.filter_by(project_id=project_id, year_month=year_month,
                                                  status=AuditStatus.checked).all()
        work_reports = sorted(list(work_reports), key=lambda x: x.total_score, reverse=True)
        current_app.logger.error('work_report len: {}'.format(len(work_reports)))
        for index, item in enumerate(work_reports):
            item.rank = index + 1
            item.save()
            db.session.add(item)
        engineers = Engineer.query.filter_by(project_id=project_id, status=EngineerStatus.on_duty).all()
        current_app.logger.error('engineers len: {}'.format(len(engineers)))
        engineers = list(filter(lambda x: isinstance(x.total_score, float), engineers))
        engineers = sorted(list(engineers), key=lambda x: x.total_score, reverse=True)
        for index, item in enumerate(engineers):
            item.rank = index + 1
            item.now_career.rank = item.rank
            db.session.add(item)
        db.session.commit()

    def action_status(self, status=None, comment=None, attitude_score=None, ability_score=None):
        involve_engineer = Engineer.query.get(self.engineer_id)
        if status == AuditStatus.checked:
            Payment.patch(self.id)
            total_score = attitude_score + ability_score
            self.update(status=status, attitude_score=attitude_score, ability_score=ability_score,
                        total_score=total_score)
            involve_engineer.action_update_engineer_score()
            involve_engineer.now_career.update(attitude_score=involve_engineer.attitude_score,
                                               ability_score=involve_engineer.ability_score)
            self.update_rank(involve_engineer.project_id, self.year_month)
        else:
            self.update(status=status, comment=comment)

        daily_logs = self.get_month_daily_logs(self.engineer_id, self.year_month, self.career_id)
        for daily_log in daily_logs:
            daily_log.update(status=status)

    def action_resubmit(self):
        self.update(status=AuditStatus.submit)
        daily_logs = self.get_month_daily_logs(self.engineer_id, self.year_month, self.career_id)
        for daily_log in daily_logs:
            daily_log.update(status=AuditStatus.submit)

    def action_cancel(self, **kwargs):
        if not self.status == AuditStatus.submit:
            raise NewComException('只有等待审核的工时报告可以撤回', 500)
        daily_logs = self.get_month_daily_logs(self.engineer_id, self.year_month, self.career_id)
        for daily_log in daily_logs:
            daily_log.update(status=DailyLogStatus.new)
        self.delete()

    __mapper_args__ = {
        'polymorphic_identity': 'work_report',
    }


class LeaveType(object):
    shift = 'shift'
    sick = 'sick'
    personal = 'personal'


class Leave(Audit):
    __tablename__ = 'leave'

    id = db.Column(db.Integer, db.ForeignKey('audit.id'), primary_key=True)
    career_id = db.Column(db.Integer, db.ForeignKey('career.id'))

    leave_type = db.Column(db.String(16))
    start_date = db.Column(db.DateTime)
    end_date = db.Column(db.DateTime)

    duration = db.Column(db.Float)
    reason = db.Column(db.String(128))

    __mapper_args__ = {
        'polymorphic_identity': 'leave',
    }

    def action_check(self, **kwargs):
        new_status = kwargs.get('status')
        if new_status == AuditStatus.reject:
            comment = kwargs.get('comment')
            self.update(status=AuditStatus.reject, comment=comment)
            return
        if new_status == AuditStatus.checked:
            involved_work_days = workdays_between(self.start_date, self.end_date)
            daily_log_type = DailyLogType.leave
            if self.leave_type == LeaveType.shift:
                daily_log_type = LeaveType.shift

            for day in involved_work_days:
                daily_log = DailyLog.find_or_create(date=day, engineer_id=self.engineer_id)
                daily_log.update(origin_type=DailyLogType.normal_work, adjust_type=daily_log_type,
                                 career_id=self.career_id,
                                 status=DailyLogStatus.new)
                copy_auth_info(daily_log, self)
                daily_log.save()
            self.status = AuditStatus.checked
            self.save()


class ExtraWork(Audit):
    __tablename__ = 'extra_work'
    id = db.Column(db.Integer, db.ForeignKey('audit.id'), primary_key=True)
    career_id = db.Column(db.Integer, db.ForeignKey('career.id'))

    start_date = db.Column(db.DateTime)
    end_date = db.Column(db.DateTime)
    duration = db.Column(db.Float)
    reason = db.Column(db.String(128))

    __mapper_args__ = {
        'polymorphic_identity': 'extra_work',
    }

    def action_check(self, **kwargs):
        new_status = kwargs.get('status')
        if new_status == AuditStatus.reject:
            comment = kwargs.get('comment')
            self.update(status=AuditStatus.reject, comment=comment)
            return
        if new_status == AuditStatus.checked:
            involved_days = days_between(self.start_date, self.end_date)
            for day in involved_days:
                daily_log = DailyLog.find_or_create(date=day, engineer_id=self.engineer_id)
                if is_work_day(day):
                    origin_type = DailyLogType.normal_work
                elif is_holiday(day):
                    origin_type = DailyLogType.holiday
                else:
                    origin_type = DailyLogType.normal_rest
                daily_log.update(origin_type=origin_type, adjust_type=DailyLogType.extra_work, adjust_id=self.id,
                                 career_id=self.career_id, status=DailyLogStatus.new)
                copy_auth_info(daily_log, self)
                daily_log.save()
            self.update(status=AuditStatus.checked)


class Entry(Audit):
    __tablename__ = 'entry'
    id = db.Column(db.Integer, db.ForeignKey('audit.id'), primary_key=True)
    offer_id = db.Column(db.Integer, db.ForeignKey('offer.id'))
    position_level_id = db.Column(db.Integer, db.ForeignKey('position_level.id'), nullable=False)
    reject_position_level_id = db.Column(db.Integer)
    date = db.Column(db.Date, nullable=False)

    interview_id = db.Column(db.Integer, db.ForeignKey('interview.id'), unique=True)

    offer = db.relationship('Offer', backref='entry')
    position_level = db.relationship('PositionLevel', backref='entry')

    __mapper_args__ = {
        'polymorphic_identity': 'entry',
    }

    @property
    def reject_position_level(self):
        rpi = self.reject_position_level_id
        if not rpi:
            rpi = self.position_level_id
        result = list(filter(lambda x: x.id == rpi, self.offer.position_levels))
        if len(result) == 0:
            return None
        return result[0]

    def action_check(self, **kwargs):
        status = kwargs.get('status')
        self.status = status
        interview = Interview.query.filter_by(id=self.interview_id).first()
        engineer = Engineer.query.filter_by(id=self.engineer_id).first()
        comment = kwargs.get('comment')
        if status == AuditStatus.reject:
            self.comment = comment
            interview.update(status=InterviewStatus.entry_reject)
            engineer.update(status=EngineerStatus.ready)
            ep = EnterProject.query.filter(EnterProject.interview_id == self.interview_id).first()
            ep.status = EnterProjectStatus.pm_reject
            ep.ing = 0
            ep.save()

        elif status == AuditStatus.checked:
            if self.offer.entry_amount >= self.offer.amount:
                raise NewComException('入职人数已满', 500)
            interview.update(status=InterviewStatus.entry_pass)
            self.save()
            ep = EnterProject.query.filter(EnterProject.interview_id == self.interview_id).first()
            ep.status = EnterProjectStatus.pm_agree
            ep.comment = comment
            ep.save()


class EntryFileAudit(Audit):
    __tablename__ = 'entry_file_audit'

    id = db.Column(db.Integer, db.ForeignKey('audit.id'), primary_key=True)
    enter_project_id = db.Column(db.Integer, db.ForeignKey('enter_project.id'))
    enter_project = db.relationship('EnterProject', backref='entry_file_audit', cascade='delete')

    __mapper_args__ = {
        'polymorphic_identity': 'entry_file_audit',
    }

    @classmethod
    def post(cls, **kwargs):
        enter_project_id = kwargs.get('enter_project_id')
        efa = cls(enter_project_id=enter_project_id)
        ep = EnterProject.query.get(enter_project_id)
        copy_auth_info(efa, ep)
        efa.status = AuditStatus.submit
        efa.save()

    def action_check(self, **kwargs):
        status = kwargs.get('status')
        self.status = status
        if status == AuditStatus.reject:
            self.enter_project.update(status=EnterProjectStatus.file_pm_reject)
        elif status == AuditStatus.checked:
            self.enter_project.update(status=EnterProjectStatus.file_pm_agree)
        self.update(status=AuditStatus.modify)


class EnterProjectStatus(BaseStatus):
    new = 0  # 平台发送入项申请中
    engineer_reject = -1
    engineer_agree = 2  # 工程师通过入项
    pm_reject = -3  # 项目经理拒绝入项
    pm_agree = 4  # 项目经理通过入项
    purchase_agree = 5  # 采购通过入项
    purchase_reject = -6  # 采购拒绝入项
    file_submit = 7  # 材料提交
    file_om_reject = -8  # om拒绝入项材料
    file_om_agree = 9  # om通过入项材料
    file_pm_reject = -10  # pm拒绝入项材料
    file_pm_agree = 11  # pm通过入项材料
    file_company_reject = -12  # 公司拒绝入项材料
    file_company_agree = 13  # 公司通过入项材料

    om_reject = -14  # om拒绝入项
    finish = 15  # 入项结束


class EnterProjectPostSchema(PostSchema):
    _permission_roles = ['om', 'purchase', 'company_om']
    engineer_id = fields.Integer()
    position_level_id = fields.Integer()
    pm_id = fields.Integer()
    project_id = fields.Integer()
    company_id = fields.Integer()
    interview_id = fields.Integer()
    salary_type = fields.Integer()
    work_place = fields.String()
    start_date = fields.Date()
    offer_id = fields.Integer()


class EnterProjectSchema(Schema):
    class ES(Schema):
        id = fields.Integer()
        real_name = fields.String()
        pre_username = fields.String()  # 工号
        gender = fields.String()
        cv_path = fields.List(fields.String())

    class PLS(Schema):
        id = fields.Integer()
        name = fields.String()
        money = fields.Float()
        position = fields.String()

    class CM(Schema):
        tax_free_rate = fields.Float()
        ware_fare = fields.Float()
        break_up_fee_rate = fields.Float()

    id = fields.Integer()
    engineer = fields.Nested(ES(many=False, unknown=EXCLUDE))
    pm = fields.Nested(ES(many=False, unknown=EXCLUDE))
    company = fields.Nested(CM(many=False, unknown=EXCLUDE))
    project = fields.String()
    salary_type = fields.Integer()
    work_place = fields.String()
    start_date = fields.Date()
    status = fields.Function(lambda x: EnterProjectStatus.int2str(x.status))
    position_level = fields.Nested(PLS(many=False, unknown=EXCLUDE))
    use_hr_service = fields.Bool()
    career_id = fields.Integer()
    expect_daily_income = fields.Float()
    expect_newcom_month_income = fields.Float()
    expect_month_income = fields.Float()
    break_up_fee = fields.Float()

    class IS(Schema):
        note = fields.String()

    interview = fields.Nested(IS(many=False))


class EnterProject(Base):
    engineer_id = db.Column(db.Integer, db.ForeignKey('engineer.id'))
    career_id = db.Column(db.Integer, db.ForeignKey('career.id'), nullable=True)
    career = db.relationship('Career', backref='enter_project')
    engineer = db.relationship('Engineer', backref='enter_project')
    pm_id = db.Column(db.Integer, db.ForeignKey('pm.id'), nullable=False)
    pm = db.relationship('Pm', backref='enter_project')
    company_id = db.Column(db.Integer, db.ForeignKey('company.id'))
    project_id = db.Column(db.Integer, db.ForeignKey('project.id'), nullable=False)
    project = db.relationship('Project', backref='enter_project')
    interview_id = db.Column(db.Integer)
    offer_id = db.Column(db.Integer)
    salary_type = db.Column(db.Integer)
    position_level_id = db.Column(db.Integer, db.ForeignKey('position_level.id'))
    reject_position_level_id = db.Column(db.Integer)
    position_level = db.relationship('PositionLevel', backref='enter_project')
    work_place = db.Column(db.String(192))
    start_date = db.Column(db.Date)
    new_engineer = db.Column(db.Integer)
    comment = db.Column(db.String(256))
    status = db.Column(db.Integer, index=True)
    ing = db.Column(db.Integer, default=1)

    @classmethod
    def post(cls, **kwargs):
        schema = EnterProjectPostSchema(many=False, unknown=EXCLUDE)
        data = schema.load(kwargs)
        if 'interview_id' not in data:
            data['status'] = EnterProjectStatus.pm_agree
        else:
            data['status'] = EnterProjectStatus.new
        m = cls(**data)
        m.save()
        return m

    @classmethod
    def company_statistic(cls, company_id):
        eps = EnterProject.query.filter(EnterProject.company_id == company_id).all()
        entry_agree_count = len(list(filter(lambda x: x.status == EnterProjectStatus.new, eps)))  # 平台发送入项申请中
        engineer_agree_count = len(
            list(filter(lambda x: x.status == EnterProjectStatus.engineer_agree, eps)))  # 项目经理确认入项信息中
        pm_agree_count = len(list(filter(lambda x: x.status == EnterProjectStatus.pm_agree, eps)))  # 确认入项信息中
        purchase_agree_count = len(list(filter(lambda x: x.status in [eval("EnterProjectStatus.{}".format(x)) for x in
                                                                      ['purchase_agree', 'file_om_reject',
                                                                       'file_pm_reject',
                                                                       'file_company_reject ']], eps)))  # 人员提交入项材料中
        file_submit_count = len(list(filter(lambda x: x.status == EnterProjectStatus.file_submit, eps)))  # 平台确认入项材料中
        file_om_count = len(list(filter(lambda x: x.status == EnterProjectStatus.file_om_agree, eps)))  # 项目经理确认入项材料中
        file_pm_count = len(list(filter(lambda x: x.status == EnterProjectStatus.file_pm_agree, eps)))  # 确认入项材料中
        file_company_agree_count = len(
            list(filter(lambda x: x.status == EnterProjectStatus.file_company_agree, eps)))  # 平台确认人员入项中
        result = dict(entry_agree_count=entry_agree_count, engineer_agree_count=engineer_agree_count,
                      pm_agree_count=pm_agree_count, purchase_agree_count=purchase_agree_count,
                      file_submit_count=file_submit_count, file_om_count=file_om_count, file_pm_count=file_pm_count,
                      file_company_agree_count=file_company_agree_count)
        return result

    @property
    def use_hr_service(self):
        return self.interview_id is not None

    @property
    def interview(self):
        if not self.interview_id:
            return {}
        return Interview.query.filter_by(id=self.interview_id).first()

    @property
    def expect_month_income(self):  # 员工模式月结
        if self.salary_type == 0:
            return 0
        cal_kwargs = self.position_level.position_cal_kwargs(1, 1)
        cal_kwargs['use_hr_service'] = self.use_hr_service
        result = self.position_level.expect_cal_payment(**cal_kwargs)
        return result['engineer_get']

    @property
    def expect_newcom_month_income(self):  # 牛咖模式月结
        if self.salary_type == 0:
            return 0
        cal_kwargs = self.position_level.position_cal_kwargs(1, 0)
        cal_kwargs['use_hr_service'] = self.use_hr_service
        result = self.position_level.expect_cal_payment(**cal_kwargs)
        return result['engineer_get']

    @property
    def expect_daily_income(self):  # 牛咖模式日结
        if self.salary_type == 1:
            return 0
        cal_kwargs = self.position_level.position_cal_kwargs(0, 0)
        cal_kwargs['use_hr_service'] = self.use_hr_service
        result = self.position_level.expect_cal_payment(**cal_kwargs)
        return result['engineer_get'] / cal_kwargs['charging_num']

    @property
    def break_up_fee(self):  # 员工离职补贴
        if self.salary_type == 0:
            return 0
        cal_kwargs = self.position_level.position_cal_kwargs(1, 1)
        cal_kwargs['use_hr_service'] = self.use_hr_service
        result = self.position_level.expect_cal_payment(**cal_kwargs)
        return result['break_up_fee']

    def action_reject(self):  # 变更状态为采购未通过
        if not self.status == EnterProjectStatus.pm_agree:
            raise NewComException('错误的入项状态', 501)
        self.status = EnterProjectStatus.purchase_reject
        self.ing = 0
        self.save()
        if self.interview_id:
            iv = Interview.query.filter_by(id=self.interview_id).first()
            iv.status = InterviewStatus.enter_project_reject
            iv.save()

    def action_enter(self, **kwargs):  # 采购通过入项申请信息
        # purchase check
        if not self.status == EnterProjectStatus.pm_agree:
            raise NewComException('错误的入项状态', 501)
        if self.interview_id:
            iv = Interview.query.filter_by(id=self.interview_id).first()
            iv.status = InterviewStatus.enter_project_pass
            iv.save()
            self.offer_id = iv.offer_id

            # todo 将工程师还在进行的面试，修改为工程师拒绝。
            # om 或者purchase 拒绝了入项后，要删除career 和 order （包括入项？）
            ivs = Interview.query.filter_by(engineer_id=self.engineer_id).all()
            for _iv in ivs:
                if _iv.id == iv.id:
                    continue
                if _iv.status > 0 and _iv.status < 14:
                    # 如果面试还在进行， 设置为拒绝
                    _iv.update(status=InterviewStatus.reject_by_engineer)
                    # 相关的入职申请要拒绝
                    _entry = Entry.query.filter(Entry.interview_id == _iv.id).first()
                    if _entry:
                        _entry.update(status=AuditStatus.reject, comment="已入职其他项目")

                    # 相关的入项要拒绝
                    _ep = EnterProject.query.filter(EnterProject.interview_id == _iv.id).first()
                    if _ep:
                        _ep.update(status=EnterProjectStatus.engineer_reject, ing=0)
                    _c = Career.query.filter(Career.interview_id == _iv.id).first()
                    if _c:
                        _ecos = EngineerCompanyOrder.query.filter_by(career_id=_c.id).all()
                        for _eco in _ecos:
                            _eco.delete()
                        _c.delete()
        self.status = EnterProjectStatus.purchase_agree
        self.save()

    def action_file_submit(self):  # 材料提交
        if self.status not in [eval("EnterProjectStatus.{}".format(x)) for x in
                               ['purchase_agree', 'file_om_reject', 'file_pm_reject', 'file_company_reject ']]:
            raise NewComException('错误的入项状态', 501)
        data = dict(request.json)  # 获取前端提交的数据
        ef_upload_result = data.get('ef_upload_result', None)  # 获取入项材料名称
        if not ef_upload_result:
            if not Config.DEBUG:
                raise NewComException('入项材料呢？', 500)
        else:
            eg = Engineer.query.get(self.engineer_id)
            self.status = EnterProjectStatus.file_submit
            self.save()

    def action_om_check_file(self, **kwargs):  # 平台检查入项材料
        yes_or_no = kwargs.get('yes_or_no')
        if yes_or_no == 0:
            comment = kwargs.get('comment', None)
            if comment is None:
                raise NewComException('驳回理由为必填项', 502)
            self.update(status=EnterProjectStatus.file_om_reject, comment=comment)
            return
        else:
            self.update(status=EnterProjectStatus.file_om_agree, comment=None)
            ef = EntryFileAudit.query.filter_by(enter_project_id=self.id).first()
            if ef is None:
                EntryFileAudit.post(enter_project_id=self.id)  # 建立入项材料审批中间表
                ef = EntryFileAudit.query.filter_by(enter_project_id=self.id).first()
            au = Audit.query.filter_by(id=ef.id).first()
            au.update(engineer_id=self.engineer_id, pm_id=self.pm_id, company_id=self.company_id,
                      project_id=self.project_id, status=AuditStatus.submit, audit_type='entry_file_audit')
            return {'entry_file_id': ef.id}

    def action_pm_check_file(self, **kwargs):  # PM检查入项材料
        yes_or_no = kwargs.get('yes_or_no')
        if yes_or_no == 0:
            comment = kwargs.get('comment', None)
            if comment is None:
                raise NewComException('驳回理由为必填项', 502)
            ef = EntryFileAudit.query.filter_by(enter_project_id=self.id).first()
            au = Audit.query.filter_by(id=ef.id).first()
            au.update(status=AuditStatus.reject)
            self.update(status=EnterProjectStatus.file_pm_reject, comment=comment)
            return
        else:
            self.update(status=EnterProjectStatus.file_pm_agree, comment=None)
            ef = EntryFileAudit.query.filter_by(enter_project_id=self.id).first()
            au = Audit.query.filter_by(id=ef.id).first()
            au.update(status=AuditStatus.checked)

    def action_company_check_file(self, **kwargs):  # 甲方端检查入项材料
        yes_or_no = kwargs.get('yes_or_no')
        if yes_or_no == 0:
            comment = kwargs.get('comment', None)
            if comment is None:
                raise NewComException('驳回理由为必填项', 502)
            self.update(status=EnterProjectStatus.file_company_reject, comment=comment)
            return
        elif yes_or_no == 1:
            data = dict(kwargs)
            # todo 判断已有入项的标志不准确。
            if self.career_id:
                career = Career.query.get(self.career_id)
                career.update(engineer_id=self.engineer_id, start=self.start_date, salary_type=self.salary_type,
                              position_level_id=self.position_level_id, status=CareerStatus.entering,
                              work_place=self.work_place, work_content=data.get('work_content', ''),
                              break_up_fee=self.company.break_up_fee_rate,
                              ware_fare=self.company.ware_fare, tax_free_rate=self.company.tax_free_rate,
                              renew_cycle=int(data['renew_cycle']), auto_renew=int(data['auto_renew']))
            else:
                # 创建在职经历
                career = Career(engineer_id=self.engineer_id, start=self.start_date, salary_type=self.salary_type,
                                position_level_id=self.position_level_id, status=CareerStatus.entering,
                                work_place=self.work_place, work_content=data.get('work_content', ''),
                                break_up_fee_rate=self.company.break_up_fee_rate, pm_id=self.pm_id,
                                ware_fare=self.company.ware_fare, tax_free_rate=self.company.tax_free_rate,
                                renew_cycle=int(data['renew_cycle']), auto_renew=int(data['auto_renew']))

            if self.interview_id:
                career.offer_id = self.offer_id
                career.interview_id = self.interview_id
            copy_auth_info(career, self)
            career.save()
            self.engineer.update(now_career_id=career.id)
            self.career_id = career.id

            data['engineer_id'] = self.engineer_id
            data['company_id'] = self.company_id
            data['project_id'] = self.project_id
            data['start_date'] = self.start_date.strftime('%Y-%m-%d')
            data['end_date'] = months_later(self.start_date, int(data['renew_cycle'])).strftime('%Y-%m-%d')
            data['career_id'] = self.career_id
            ep = EngineerCompanyOrder.post(**data)
            self.update(status=EnterProjectStatus.file_company_agree, comment=None)
            return {'engineer_company_order_id': ep.id}

    def action_om_check(self, **kwargs):  # 平台通过入项
        if not self.status == EnterProjectStatus.file_company_agree:
            raise NewComException('错误的入项状态', 501)
        engineer = Engineer.query.get(self.engineer_id)

        # 员工生成入职后的索引
        copy_auth_info(engineer, self)
        engineer.update(status=EngineerStatus.on_duty, now_career_id=self.career_id,
                        position_level_id=self.position_level_id, position_id=self.position_level.position.id)
        engineer.s_money = engineer.now_career.position_level.money
        engineer.save()

        self.career.employ_type = kwargs.get('employ_type')
        if self.career.employ_type == 0:
            self.career.tax_free_rate = self.company.tax_free_rate
        else:
            self.career.ware_fare = self.company.ware_fare
            self.career.break_up_fee_rate = self.company.break_up_fee_rate

        self.career.s_money = self.career.position_level.money
        self.career.real_name = engineer.real_name
        self.career.engineer_status = engineer.status
        # 工时申报审核通过应更新career的分数信息
        keys = ['phone', 'ability_score', 'attitude_score', 'position_id']
        for k in keys:
            v = getattr(engineer, k)
            setattr(self.career, k, v)
        self.career.search_index()
        self.career.status = CareerStatus.on_duty
        self.career.save()

        eps = EnterProject.query.filter(EnterProject.id != self.id,
                                        EnterProject.engineer_id == self.engineer.id).all()
        if eps:
            for ep in eps:
                ep.delete()
        self.status = EnterProjectStatus.finish
        self.ing = 2
        self.save()

        # 如果是通过增员进入的，可以返回了。
        if not self.interview_id:
            return

        iv = Interview.query.filter_by(id=self.interview_id).first()
        iv.status = InterviewStatus.om_pass
        iv.save()

        iv = Interview.query.filter_by(id=self.interview_id).first()
        # 如果需求数量满足，则关闭其他未完成的面试和入职
        if iv.offer.entry_amount >= iv.offer.amount:
            iv.offer.update(status=OfferStatus.closed, shut_down_reason=OfferShutDownReason.finished)
            # 找出这个offer下的所有interviews
            ing_interviews = Interview.query.filter_by(offer_id=self.offer_id).all()
            for ii in ing_interviews:
                if ii.status > 0:
                    if ii.status < 17:
                        # 还在进行的都拒绝
                        ii.update(status=InterviewStatus.reject_by_engineer)
                        _c = Career.query.filter(Career.interview_id == ii.id).first()
                        if _c:
                            _c.delete()
            # 入职审批都拒绝
            ing_entries = Entry.query.filter_by(offer_id=self.offer_id, status=AuditStatus.submit).all()
            for ie in ing_entries:
                ie.update(status=AuditStatus.reject, comment='已招满')
            # 存在得入项流程都删除，若存在采购订单，删除采购订单
            _eps = EnterProject.query.filter(EnterProject.offer_id == self.offer_id,
                                             EnterProject.interview_id != None).all()
            for _ep in _eps:
                if _ep.status < EnterProjectStatus.finish:
                    _order = EngineerCompanyOrder.query.filter_by(project_id=_ep.project_id,
                                                                  career_id=_ep.career_id).first()
                    if _order: _order.delete()
                    _ep.delete()

    def action_om_reject(self):  # 变更状态为om未通过
        if not self.status == EnterProjectStatus.file_company_agree:
            raise NewComException('错误的入项状态', 501)
        self.status = EnterProjectStatus.om_reject
        self.ing = 0
        self.save()
        if self.interview_id:
            iv = Interview.query.filter_by(id=self.interview_id).first()
            iv.status = InterviewStatus.enter_project_reject
            iv.save()
            self.career.delete()
        else:
            eep = EnterProject.query.filter_by(career_id=self.id).first()
            if eep.new_engineer:
                self.career.delete()
                eep.delete()
                self.engineer.delete()
            eep.delete()


class EnterProjectRejectSchema(BaseActionSchema):
    _permission_roles = ['company_om', 'purchase']
    ModelClass = EnterProject
    action = 'reject'


class EnterProjectCheckSchema(BaseActionSchema):
    _permission_roles = ['company_om', 'purchase']
    ModelClass = EnterProject
    action = 'enter'


class EnterProjectSubmitSchema(BaseActionSchema):
    _permission_roles = ['engineer']
    ModelClass = EnterProject
    action = 'file_submit'


class EnterProjectOmFileAuditSchema(BaseActionSchema):
    _permission_roles = ['om']
    ModelClass = EnterProject
    action = 'om_check_file'

    yes_or_no = fields.Bool()
    comment = fields.String(required=False)


class EnterProjectPmFileAuditSchema(BaseActionSchema):
    _permission_roles = ['pm']
    ModelClass = EnterProject
    action = 'pm_check_file'

    yes_or_no = fields.Bool()
    comment = fields.String()


class EnterProjectCompanyFileAuditSchema(BaseActionSchema):
    _permission_roles = ['company_om', 'purchase']
    ModelClass = EnterProject
    action = 'company_check_file'

    yes_or_no = fields.Bool()
    comment = fields.String()

    work_content = fields.String()
    service_type = fields.String()
    auto_renew = fields.Integer()
    renew_cycle = fields.Integer()


class EnterProjectOmCheckSchema(BaseActionSchema):
    _permission_roles = ['om']
    ModelClass = EnterProject
    action = 'om_check'

    employ_type = fields.Integer(required=True)


class EnterProjectOmRejectSchema(BaseActionSchema):
    _permission_roles = ['om']
    ModelClass = EnterProject
    action = 'om_reject'


class EngineerCompanyOrderPostSchema(PostSchema):
    _permission_roles = ['om', 'company_om', 'purchase']

    # 填写的内容
    work_content = fields.String()
    service_type = fields.String()
    auto_renew = fields.Integer()
    renew_cycle = fields.Integer()

    # 通过入职对象获得的信息
    company_id = fields.Integer()
    engineer_id = fields.Integer()
    project_id = fields.Integer()
    career_id = fields.Integer()
    start_date = fields.Date()
    end_date = fields.Date()


class EngineerCompanyOrderSchema(Schema):
    class ES(Schema):
        id = fields.Integer()
        real_name = fields.String()

    class NIS(Schema):
        id = fields.Integer()
        name = fields.String()

    class CS(Schema):
        class PLS(Schema):
            id = fields.Integer()
            name = fields.String()
            position = fields.String()
            money = fields.Float()

        salary_type = fields.Integer()
        work_place = fields.String()
        position_level = fields.Nested(PLS(many=False))
        company = fields.String()
        pm = fields.String()

    id = fields.Integer()
    engineer = fields.Nested(ES(many=False))
    project = fields.Nested(NIS(many=False))
    created = fields.DateTime()
    service_type = fields.String()
    work_content = fields.String()
    career = fields.Nested(CS(many=False))
    start_date = fields.Date()
    end_date = fields.Date()
    renew_cycle = fields.Integer()
    auto_renew = fields.Integer()
    expect_total_fee = fields.Float()
    finished_fee = fields.Float()


class EngineerCompanyOrderStatus(BaseStatus):
    underway = 0
    finsh = 1
    to_start = 2


class EngineerCompanyOrder(Base):
    company_id = db.Column(db.Integer, db.ForeignKey('company.id'))
    engineer_id = db.Column(db.Integer, db.ForeignKey('engineer.id'))
    engineer = db.relationship('Engineer', backref='engineer_company_order')
    project_id = db.Column(db.Integer, db.ForeignKey('project.id'))
    project = db.relationship('Project', backref='engineer_company_order')
    work_content = db.Column(db.String(256))
    start_date = db.Column(db.Date())
    end_date = db.Column(db.Date())
    career_id = db.Column(db.Integer, db.ForeignKey('career.id'))
    career = db.relationship('Career', backref='orders')
    auto_renew = db.Column(db.Integer)
    renew_cycle = db.Column(db.Integer)
    service_type = db.Column(db.String(16))
    next_id = db.Column(db.Integer)
    need_renew = db.Column(db.Integer, default=0)

    expect_total_fee = db.Column(db.Float())
    finished_fee = db.Column(db.Float())
    status = db.Column(db.Integer, default=0)

    daily_logs = db.relationship('DailyLog', backref='order')

    def complete_part(self, p):
        mf, me = month_first_end_date(p.year_month // 100, p.year_month % 100)
        begin = mf if mf > self.start_date else self.start_date
        end = me if me < self.end_date else self.end_date
        if begin > end:
            return
        DL = DailyLog
        ds = DL.query.filter(DL.career_id == self.career_id).filter(and_(DL.date >= begin, DL.date <= end)).all()
        work_days = filter(lambda x: x.origin_type == DailyLogType.normal_work and x.adjust_type is None, ds)
        shift_days = filter(lambda x: x.adjust_type is DailyLogType.shift, ds)
        total_days = p.work_report.work_days + p.work_report.shift_days
        count_days = sum([x.duration for x in work_days]) + len(list(shift_days))
        money = p.company_pay * (count_days / total_days) if total_days != 0 else 0
        if not self.finished_fee:
            self.finished_fee = 0
        self.finished_fee += money
        self.save()

    def is_using(self):
        return self.engineer.now_career_id == self.career_id

    def is_ing(self):
        if not self.is_using():
            return False
        today = get_today()
        if self.start_date <= today and self.end_date >= today:
            self.update(status=EngineerCompanyOrderStatus.underway)
        elif self.start_date > today:
            self.update(status=EngineerCompanyOrderStatus.to_start)
        else:
            self.update(status=EngineerCompanyOrderStatus.finsh)
        return self.status

    def is_ending(self):
        if not self.is_using():
            return False
        today = get_today()
        one_day = dt.timedelta(days=1)
        if self.next_id:
            return False
        if self.is_ing():
            if self.end_date <= one_day * 15 + today:
                return True
        return False

    def cal_expect_total_fee(self):
        salary_type = self.career.salary_type
        if salary_type == 0:
            work_days = 22 * self.renew_cycle
            total = work_days * self.career.position_level.money
        else:
            total = self.renew_cycle * self.career.position_level.money
        self.expect_total_fee = total
        self.save()

    @classmethod
    def post(cls, **kwargs):
        schema = EngineerCompanyOrderPostSchema(many=False, unknown=EXCLUDE)
        data = schema.load(kwargs)
        m = cls(**data)
        m.finished_fee = 0
        m.status = EngineerCompanyOrderStatus.underway
        m.save()
        m.cal_expect_total_fee()
        return m

    def action_daily_logs(self, **kwargs):
        dls = self.daily_logs
        leaves = Leave.query.filter_by(career_id=self.career_id).filter(
            Leave.start_date.between(self.start_date, self.end_date)).all()
        extra_works = ExtraWork.query.filter_by(career_id=self.career_id).filter(
            ExtraWork.start_date.between(self.start_date, self.end_date)).all()
        result = dict(statistics={})
        result['statistics']['work_days'] = WorkReport.filter_work_days(dls, leaves)[1]
        result['statistics']['leave_days'] = WorkReport.filter_leave_days(leaves)[1]
        result['statistics']['rest_days'] = len(WorkReport.filter_rest_days(dls))
        result['statistics']['extra_work_days'] = WorkReport.filter_extra_work_days(extra_works, dls, leaves)[1]
        result['statistics']['absent_days'] = len(WorkReport.filter_absent_days(dls, leaves))
        result['statistics']['shift_days'] = WorkReport.filter_shift_days(leaves)[1]

        class DLS(Schema):
            id = fields.Int()
            date = fields.Date()
            duration = fields.Float()
            content = fields.Str()
            note = fields.Str()
            origin_type = fields.Str()

        sc = DLS(many=True)
        result['daily_logs'] = sc.dump(dls)
        return result


class OrderWithDailyLogs(BaseActionSchema):
    action = 'daily_logs'
    ModelClass = EngineerCompanyOrder
    _permission_roles = ['company_om', 'purchase']


class Resign(Audit):
    __tablename__ = 'resign'
    id = db.Column(db.Integer, db.ForeignKey('audit.id'), primary_key=True)
    date = db.Column(db.Date, nullable=False)
    reason = db.Column(db.String(256), nullable=False)
    career_id = db.Column(db.Integer, db.ForeignKey('career.id'))
    career = db.relationship('Career', backref='resign')

    @property
    def position_level(self):
        return self.career.position_level.position.name + ' ' + self.career.position_level.name

    @classmethod
    def post(cls, **kwargs):
        engineer_id = kwargs.get('engineer_id')
        engineer_model = Engineer.query.get(engineer_id)
        already = cls.query.filter_by(career_id=engineer_model.now_career_id, status=AuditStatus.submit).first()
        if already:
            raise NewComException('尚有未处理的离职信息', 501)
        reason = kwargs.get('reason')
        date = kwargs.get('date')
        date = dt.datetime.strptime(date, "%Y-%m-%d").date()
        if not is_work_day(date):
            raise NewComException('离职应在工作日办理', 501)
        if not date > get_today():
            raise NewComException('离职申请应提前', 500)
        career = Career.query.get(engineer_model.now_career_id)
        career.update(end=date, status=CareerStatus.leaving)
        engineer_model = Engineer.query.filter_by(id=engineer_id).first()
        engineer_model.update(status=EngineerStatus.leaving)
        resign = cls(engineer_id=engineer_id, date=date, career_id=engineer_model.now_career_id, reason=reason)
        copy_auth_info(resign, engineer_model)
        resign.status = AuditStatus.submit
        resign.save()
        return resign.id

    def action_check(self, **kwargs):
        status = kwargs.get('status')
        engineer_model = Engineer.query.get(self.engineer_id)
        if status == AuditStatus.reject:
            self.career.update(end=None, status=CareerStatus.on_duty)
            engineer_model.update(status=EngineerStatus.on_duty)
            comment = kwargs.get('comment')
            self.status = status
            self.comment = comment
        elif status == AuditStatus.checked:
            un_checked_audits = Audit.query.filter_by(engineer_id=self.engineer_id, status=AuditStatus.submit).all()
            if len(un_checked_audits) > 1:
                raise NewComException('尚有未完成的审批', 500)
            DailyLog.check_uncreated(self.engineer_id, self.date)
            if DailyLog.query.filter(DailyLog.engineer_id == self.engineer_id,
                                     DailyLog.career_id == engineer_model.now_career_id,
                                     DailyLog.status == DailyLogStatus.new, DailyLog.date <= self.date).all():
                raise NewComException('离职日期前尚有未完成的日志', 500)

            self.status = status
            order = EngineerCompanyOrder.query.filter_by(career_id=engineer_model.now_career_id).first()
            order.update(status=EngineerCompanyOrderStatus.finsh)
            engineer_model.pm_id = None
            engineer_model.company_id = None
            engineer_model.now_career.update(status=CareerStatus.finish)
            engineer_model.now_career_id = None
            engineer_model.project_id = None
            engineer_model.status = EngineerStatus.ready
            engineer_enter_project = EnterProject.query.filter_by(engineer_id=engineer_model.id).first()
            engineer_enter_project.delete()
            engineer_entry_audit = Audit.query.filter_by(engineer_id=self.id, audit_type='entry_file_audit').first()
            if engineer_entry_audit:
                EntryFileAudit.query.get(engineer_entry_audit.id).delete()
                engineer_entry_audit.delete()  # 删除入项材料审批流程，避免入项材料审批查询不唯一
            engineer_model.save()
        self.save()

    __mapper_args__ = {
        'polymorphic_identity': 'resign',
    }


def copy_auth_info(target, source):
    for key in ['project_id', 'company_id', 'pm_id', 'engineer_id']:
        if hasattr(target, key) and hasattr(source, key):
            setattr(target, key, getattr(source, key))


class PaymentStatus(BaseStatus):
    new = 0
    submit = 1
    checked = 2
    payed = 3


class CalPaymentSchema(Schema):
    salary_type = fields.Integer()
    employ_type = fields.Integer()
    money = fields.Integer()
    on_duty_days = fields.Integer()
    out_duty_days = fields.Integer()
    service_fee_rate = fields.Float()
    tax_rate = fields.Float()
    use_hr_service = fields.Float()
    hr_fee_rate = fields.Float()
    finance_rate = fields.Float()
    tax_free_rate = fields.Float()
    ware_fare = fields.Float()


class PaymentSimpleSchema(Schema):
    class ES(Schema):
        id = fields.Integer()
        real_name = fields.String()
        gender = fields.String()

    class CS(Schema):
        start = fields.Date()
        interview_id = fields.Integer()
        use_hr_service = fields.Integer()
        salary_type = fields.Integer()
        employ_type = fields.Integer()
        pm = fields.String()
        project = fields.String()

    class WRS(Schema):
        work_duration = fields.Integer()
        leave_duration = fields.Float()
        extra_work_duration = fields.Float()
        absent_days = fields.Float()
        shift_duration = fields.Float()
        attitude_score = fields.Float()
        ability_score = fields.Float()
        total_score = fields.Float()
        rest_days = fields.Float()
        rank = fields.Int()
        out_project_days = fields.Float()

    status = fields.Function(lambda x: PaymentStatus.int2str(x.status))

    class PLS(Schema):
        position = fields.String()
        name = fields.String()
        money = fields.Float()

    position_level = fields.Nested(PLS(many=False, unknown=EXCLUDE))

    id = fields.Integer()
    engineer = fields.Nested(ES(many=False))
    career = fields.Nested(CS(many=False))
    work_report = fields.Nested(WRS(many=False))
    year_month = fields.Integer()
    company_pay = fields.Float()
    amerce = fields.Float()
    hr_fee = fields.Float()
    tax = fields.Float()
    tax_rate = fields.Float()
    tax_free_rate = fields.Float()
    service_fee = fields.Float()
    finance_fee = fields.Float()
    finance_rate = fields.Float()
    use_hr_service = fields.Integer()
    created = fields.DateTime()
    service_fee_rate = fields.Float()
    hr_fee_rate = fields.Float()
    billing_cycle = fields.Integer()
    engineer_get = fields.Float()
    engineer_tax = fields.Float()
    break_up_fee_rate = fields.Float()
    break_up_fee = fields.Float()
    ware_fare = fields.Float()
    employ_type = fields.Float()
    station_salary = fields.Float()
    extra_salary = fields.Float()


class Payment(Base):
    engineer_id = db.Column(db.Integer, db.ForeignKey('engineer.id'))
    pm_id = db.Column(db.Integer, db.ForeignKey('pm.id'))
    company_id = db.Column(db.Integer, db.ForeignKey('company.id'))
    project_id = db.Column(db.Integer, db.ForeignKey('project.id'))
    work_report_id = db.Column(db.Integer, db.ForeignKey('work_report.id'))
    career_id = db.Column(db.Integer, db.ForeignKey('career.id'))
    offer_id = db.Column(db.Integer, index=True)

    year_month = db.Column(db.Integer)

    company_pay = db.Column(db.Float('20,2'))
    amerce = db.Column(db.Float)
    hr_fee = db.Column(db.Float('20,2'))
    service_fee_rate = db.Column(db.Float)
    finance_fee = db.Column(db.Float('20,2'))
    tax = db.Column(db.Float('20,2'))
    engineer_income_with_tax = db.Column(db.Float('20,2'))
    engineer_get = db.Column(db.Float('20,2'))
    engineer_tax = db.Column(db.Float('20,2'))
    break_up_fee = db.Column(db.Float('20,2'))
    break_up_fee_rate = db.Column(db.Float)
    out_duty_days = db.Column(db.Integer)

    employ_type = db.Column(db.Integer)
    tax_rate = db.Column(db.Float)
    use_hr_service = db.Column(db.Float)
    finance_rate = db.Column(db.Float)
    tax_free_rate = db.Column(db.Float)
    ware_fare = db.Column(db.Float('20,2'))
    service_fee = db.Column(db.Float('20,2'))
    billing_cycle = db.Column(db.Integer())
    position_level_id = db.Column(db.Integer, db.ForeignKey('position_level.id'))
    position_level = db.relationship('PositionLevel', backref='Payment')
    money = db.Column(db.Float('20,2'))
    hr_fee_rate = db.Column(db.Float('20,2'))
    station_salary = db.Column(db.Float('20,2'))  # 工位费
    extra_salary = db.Column(db.Float('20,2'))  # 加班费

    status = db.Column(db.Integer, index=True)
    monthly_bill_id = db.Column(db.Integer, db.ForeignKey('monthly_bill.id'))
    monthly_bill = db.relationship('WorkReport', backref='payments')
    work_report = db.relationship('WorkReport', backref='Payment')
    pm = db.relationship('Pm', backref='Payment')
    project = db.relationship('Project', backref="Payment")
    company = db.relationship('Company', backref='Payment')

    @classmethod
    def patch(cls, work_report_id):
        exist_payment = cls.query.filter_by(work_report_id=work_report_id).all()
        if exist_payment:
            # exist_payment.update(status=PaymentStatus.new)
            pass
        else:
            cls.post(work_report_id)

    @classmethod
    def cal_payment(cls, salary_type=None, employ_type=None, money=None, work_duration=None, work_extra_duration=None,
                    holiday_extra_duration=None, weekend_extra_duration=None, shift_duration=None,
                    work_day_shift_rate=None, weekend_shift_rate=None, holiday_shift_rate=None, charging_num=None,
                    out_duty_days=None, service_fee_rate=None, tax_rate=None, year_month=None, shift_type=None,
                    use_hr_service=None, hr_fee_rate=None, finance_rate=None, work_station_fee=None, tax_free_rate=None,
                    ware_fare=None, break_up_fee_rate=None, service_type=None, extra_station_duration=None):
        legal_duration = len(month_work_days(year_month)) * 8  # 法定工作日时长
        charging_duration = charging_num * 8  # 计费时长
        extra_total_duration = work_extra_duration * work_day_shift_rate + holiday_extra_duration * holiday_shift_rate \
                               + weekend_extra_duration * weekend_shift_rate  # 加班总时长
        amerce = 0  # 缺勤扣除
        station_salary = 0  # 工位费
        if salary_type == 0:
            # 如果是日结
            duration_salary = money / 8  # 单价按小时
            if shift_type == 0:  # 补偿方式为调休
                on_duty_duration = work_duration + shift_duration
                extra_salary = 0
                labor_salary = on_duty_duration * duration_salary
            else:  # 补偿方式为加班费
                on_duty_duration = work_duration
                if on_duty_duration > legal_duration:  # 实际出勤大于法定时长
                    on_duty_duration = legal_duration
                extra_salary = extra_total_duration * duration_salary
                labor_salary = on_duty_duration * duration_salary + extra_salary
        else:
            # 如果月结
            duration_salary = money / charging_duration
            if shift_type == 0:  # 补偿方式为调休
                on_duty_duration = work_duration + shift_duration
                extra_salary = 0
                labor_salary = duration_salary * on_duty_duration
                if charging_duration < on_duty_duration < legal_duration:
                    amerce = duration_salary * out_duty_days
                    labor_salary = money - amerce
            else:  # 补偿方式为加班费
                on_duty_duration = work_duration
                if on_duty_duration > legal_duration:  # 实际出勤大于法定时长
                    on_duty_duration = legal_duration

                extra_salary = extra_total_duration * duration_salary
                labor_salary = on_duty_duration * duration_salary + extra_salary
                if charging_duration < on_duty_duration < legal_duration:
                    amerce = duration_salary * out_duty_days
                    labor_salary = money - amerce + extra_salary  # 工时费

        if service_type == '远程':
            if shift_type == 0:
                station_salary = (work_station_fee / 8) * (on_duty_duration + shift_duration)  # 工位费
            else:
                station_salary = (work_station_fee / 8) * (on_duty_duration + extra_station_duration)
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

        return dict(company_pay=company_pay, amerce=amerce, hr_fee=hr_fee, service_fee_rate=service_fee_rate,
                    finance_fee=finance_fee, tax=tax, engineer_income_with_tax=engineer_income_with_tax,
                    engineer_get=engineer_get, engineer_tax=engineer_tax, break_up_fee=break_up_fee,
                    break_up_fee_rate=break_up_fee_rate, out_duty_days=out_duty_days, tax_rate=tax_rate,
                    extra_salary=extra_salary, station_salary=station_salary, hr_fee_rate=hr_fee_rate,
                    finance_rate=finance_rate, use_hr_service=use_hr_service, tax_free_rate=tax_free_rate,
                    ware_fare=ware_fare, service_fee=service_fee, tax_fee=tax_fee)

    @classmethod
    def get_cal_kwargs(cls, involve_engineer, involve_work_report):
        cal_kwargs = dict()
        cal_kwargs['service_fee_rate'] = involve_engineer.company.service_fee_rate
        cal_kwargs['tax_rate'] = involve_engineer.company.tax_rate
        cal_kwargs['hr_fee_rate'] = involve_engineer.company.hr_fee_rate
        cal_kwargs['finance_rate'] = involve_engineer.company.finance_rate
        cal_kwargs['use_hr_service'] = involve_engineer.now_career.use_hr_service
        cal_kwargs['salary_type'] = involve_engineer.now_career.salary_type
        cal_kwargs['employ_type'] = involve_engineer.now_career.employ_type
        cal_kwargs['money'] = involve_engineer.now_career.position_level.money
        cal_kwargs['work_duration'] = involve_work_report.work_duration
        cal_kwargs['shift_duration'] = involve_work_report.shift_duration
        cal_kwargs['work_extra_duration'] = involve_work_report.work_extra_duration
        cal_kwargs['holiday_extra_duration'] = involve_work_report.holiday_extra_duration
        cal_kwargs['weekend_extra_duration'] = involve_work_report.weekend_extra_duration
        cal_kwargs['extra_station_duration'] = involve_work_report.extra_station_duration
        cal_kwargs['work_day_shift_rate'] = involve_engineer.company.work_day_shift_rate
        cal_kwargs['weekend_shift_rate'] = involve_engineer.company.weekend_shift_rate
        cal_kwargs['holiday_shift_rate'] = involve_engineer.company.holiday_shift_rate
        cal_kwargs['work_station_fee'] = involve_engineer.company.work_station_fee
        cal_kwargs['tax_free_rate'] = involve_engineer.company.tax_free_rate
        cal_kwargs['year_month'] = involve_work_report.year_month
        cal_kwargs['shift_type'] = involve_engineer.company.shift_type
        cal_kwargs['charging_num'] = involve_engineer.company.charging_num  # 计费天数
        e = EngineerCompanyOrder.query.filter_by(engineer_id=involve_engineer.id).first()
        cal_kwargs['service_type'] = e.service_type
        career_start = involve_engineer.now_career.start
        # 如果是入职第一个月，且晚于15号，不交社保
        if career_start.year * 100 + career_start.month == involve_work_report.year_month and career_start.day >= 15:
            cal_kwargs['ware_fare'] = 0
        else:
            cal_kwargs['ware_fare'] = involve_engineer.company.ware_fare

        cal_kwargs['break_up_fee_rate'] = involve_engineer.company.break_up_fee_rate
        cal_kwargs['out_duty_days'] = involve_work_report.leave_duration + involve_work_report.out_project_days * 8 + \
                                      involve_work_report.absent_days * 8
        return cal_kwargs

    @classmethod
    def post(cls, work_report_id=None):

        involve_work_report = WorkReport.query.get(work_report_id)
        involve_engineer = Engineer.query.get(involve_work_report.engineer_id)

        cal_kwargs = cls.get_cal_kwargs(involve_engineer, involve_work_report)
        result = cls.cal_payment(**cal_kwargs)
        payment = cls(engineer_id=involve_engineer.id)
        copy_auth_info(payment, involve_engineer)
        result['employ_type'] = cal_kwargs['employ_type']
        result['salary_type'] = cal_kwargs['salary_type']
        result['billing_cycle'] = involve_engineer.company.billing_cycle
        result['work_report_id'] = work_report_id
        result['career_id'] = involve_engineer.now_career_id
        result['year_month'] = involve_work_report.year_month
        result['status'] = PaymentStatus.new
        result['position_level_id'] = involve_engineer.now_career.position_level_id
        result['money'] = involve_engineer.now_career.position_level.money
        result['offer_id'] = involve_engineer.now_career.offer_id
        payment.update(**result)
        payment.save()

    @classmethod
    def url_path_name_for_purchase_excel(cls, company_id, year_month):
        year = int(year_month / 100)
        month = year_month % 100
        name = Config.EXCEL_FOR_PURCHASE_NAME_FORMAT.format(company_id, year, month)
        path = os.path.join(Config.EXCEL_PATH, name)
        url = url_for('om.payments_excel_for_purchase', company_id=company_id, year_month=year_month)
        url = 'http://{}{}'.format(Config.DOMAIN, url)
        return url, path, name

    @classmethod
    def url_path_name_for_engineer_excel(cls, company_id, year_month):
        year = int(year_month / 100)
        month = year_month % 100
        name = Config.EXCEL_FOR_ENGINEER_NAME_FORMAT.format(company_id, year, month)
        path = os.path.join(Config.EXCEL_PATH, name)
        url = url_for('om.payments_excel_for_engineer', company_id=company_id, year_month=year_month)
        url = 'http://{}{}'.format(Config.DOMAIN, url)
        return url, path, name

    @classmethod
    def get_purchase_excel(cls, company_id, year_month):
        pass

    @classmethod
    def actions_engineer_excel(cls, models, **kwargs):
        company_id = models[0].company_id
        year_month = models[0].year_month
        for model in models:
            if not model.company_id == company_id or not model.year_month == year_month:
                raise NewComException('只支持生成同一个公司同一个月的账单', 500)
        data = []
        for index, model in enumerate(models):
            item = dict(index=str(index + 1))
            item['name'] = model.engineer.real_name
            item['pm'] = model.pm.real_name
            item['project'] = model.project.name
            item['position'] = model.position_level.position.name
            item['position_level'] = model.career.position_level.name
            item['money'] = model.career.position_level.money
            item['salary_type'] = '按月计费' if model.career.position_level.money else '按日计费'
            item['employ_type'] = '员工模式' if model.career.position_level.money else '牛咖模式'
            item['work_duration'] = model.work_report.work_duration
            item['extra_work_duration'] = model.work_report.extra_work_duration
            item['shift_duration'] = model.work_report.shift_duration
            item['leave_duration'] = model.work_report.leave_duration
            item['absent_days'] = model.work_report.absent_days
            item['out_project_days'] = model.work_report.out_project_days
            item['amerce'] = model.amerce
            item['company_pay'] = model.company_pay
            item['billing_cycle'] = '1个月到账期' if model.billing_cycle == 1 else '3个月到账期'
            item['service_fee_rate'] = model.service_fee_rate
            item['service_fee'] = model.service_fee_rate
            item['tax_rate'] = model.tax_rate
            item['tax'] = model.tax
            item['hr_fee_rate'] = model.hr_fee_rate
            item['hr_fee'] = model.hr_fee
            item['finance_rate'] = model.finance_rate
            item['finance_fee'] = model.finance_fee
            item['ware_fare'] = model.ware_fare
            item['engineer_tax'] = model.engineer_tax
            item['break_up_fee_rate'] = model.break_up_fee_rate
            item['break_up_fee'] = model.break_up_fee
            item['engineer_get'] = model.engineer_get
            data.append(item)

        def _create_excel(path, name):  # 导出薪资结算单excel
            table_headers = [('序号', 'index'), ('姓名', 'name'), ('项目经理', 'pm'), ('项目', 'project'), ('职位', 'position'),
                             ('级别', 'position_level'), ('计费方式', 'salary_type'), ('人员模式', 'employ_type'),
                             ('单价', 'money'), ('出勤', 'work_duration'), ('加班', 'extra_work_duration'),
                             ('倒休', 'shift_duration'), ('请假', 'leave_duration'), ('旷工', 'absent_days'),
                             ('未入项', 'out_project_days'), ('缺勤扣除', 'amerce'), ("服务费", 'company_pay'),
                             ('资金成本', 'billing_cycle'), ('平台服务费率', 'service_fee_rate'), ('平台服务费', 'service_fee'),
                             ('综合税率', 'tax_rate'), ('税金', 'tax'), ('HR服务费率', 'hr_fee_rate'), ('招聘费', 'hr_fee'),
                             ('金融费率', 'finance_rate'), ('金融费', 'finance_fee'), ('离职补偿标准', 'break_up_fee_rate'),
                             ('离职补偿费用', 'break_up_fee'), ('个人所得税', 'engineer_tax'), ("社保", 'ware_fare'),
                             ("技术服务费", 'engineer_get')]
            wbk = xlwt.Workbook()
            sheet = wbk.add_sheet('薪资结算单')
            sheet.write_merge(0, 0, 0, 10, name.split('.')[0])
            for index, header in enumerate(table_headers):
                sheet.write(1, index, header[0])
            for index, item in enumerate(data):
                for header_index, header in enumerate(table_headers):
                    sheet.write(index + 2, header_index, data[index][header[1]])
            wbk.save(path)

        url, path, name = cls.url_path_name_for_engineer_excel(company_id, year_month)

        _create_excel(path, name)
        return url

    @classmethod
    def actions_purchase_excel(cls, models, **kwargs):
        company_id = models[0].company_id
        year_month = models[0].year_month
        for model in models:
            if not model.company_id == company_id or not model.year_month == year_month:
                raise NewComException('只支持生成同一个公司同一个月的账单', 500)
        data = []
        for index, model in enumerate(models):
            item = dict(index=str(index + 1))
            item['position'] = model.career.position_level.position.name
            item['position_level'] = model.career.position_level.name
            item['salary_type'] = '按月计费' if model.career.position_level.money else '按日计费'
            item['name'] = model.engineer.real_name
            item['pm'] = model.pm.real_name
            item['project'] = model.project.name
            item['money'] = model.career.position_level.money
            item['work_duration'] = model.work_report.work_duration
            item['extra_work_duration'] = model.work_report.extra_work_duration
            item['shift_duration'] = model.work_report.shift_duration
            item['leave_duration'] = model.work_report.leave_duration
            item['absent_days'] = model.work_report.absent_days
            item['out_project_days'] = model.work_report.out_project_days
            item['amerce'] = model.amerce
            item['station_salary'] = model.station_salary
            item['company_pay'] = model.company_pay
            item['work_report_status'] = '是' if model.work_report.status == AuditStatus.checked else '否'
            item['send_payment_status'] = '是' if model.status >= PaymentStatus.new else '否'
            item['payment_payed_status'] = '是' if model.status == PaymentStatus.checked else '否'
            data.append(item)

        def _create_excel(path, name):  # 导出结算单
            table_headers = [('序号', 'index'), ('姓名', 'name'), ('职位', 'position'), ('级别', 'position_level'),
                             ('单价', 'money'), ('项目经理', 'pm'), ('所属项目', 'project'), ('出勤', 'work_duration'),
                             ('加班', 'extra_work_duration'), ('倒休', 'shift_duration'), ('请假', 'leave_duration'),
                             ('旷工', 'absent_days'), ('未入项', 'out_project_days'), ('缺勤扣除', 'amerce'),
                             ("服务费", 'company_pay'), ('计费方式', 'salary_type'), ('旷工', 'absent_days'),
                             ('服务费', 'company_pay'), ('工位费', 'station_salary'), ('工时确认', 'work_report_status'),
                             ('发送结算', 'send_payment_status'), ('确认结算', 'payment_payed_status')]
            wbk = xlwt.Workbook()
            sheet = wbk.add_sheet('工时结算单')
            sheet.write_merge(0, 0, 0, 10, name.split('.')[0])
            for index, header in enumerate(table_headers):
                sheet.write(1, index, header[0])
            for index, item in enumerate(data):
                for header_index, header in enumerate(table_headers):
                    sheet.write(index + 2, header_index, data[index][header[1]])
            wbk.save(path)

        url, path, name = cls.url_path_name_for_purchase_excel(company_id, year_month)

        _create_excel(path, name)
        return url

