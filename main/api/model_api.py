from flask import request, jsonify, redirect
from flask_login import current_user
from marshmallow import EXCLUDE

from ..schema.base import *
from ..schema.user import *
from ..schema.pm import *
from ..schema.engineer import *
from ..schema.company import *
from ..schema.om import *
from ..model import *
from ..exception import NewComException, NewComItemNotExist
from ..util.try_catch import api_response
from ..util.work_dates import (
  workday_num_between,
  rest_days_num_between,
  get_datetime_today,
  change_datetime_date,
)
from config import load_config
from .engineer import latest_shown_month, engineer_can_shift_duration, latest_work_report

Config = load_config()


class ModelApi(object):
  exclude_methods = []
  include_methods = ["items", "item", "post", "delete", "put"]

  def __init__(self, app, model_class, default_schema=None):
    self.app = app
    self.model_class = model_class
    self.default_schema = default_schema
    self.single_source_name = None
    self.list_source_name = None
    self.endpoint_prefix = None

  def init_blueprint(
      self,
      single_source_name=None,
      list_source_name=None,
      url_prefix="/",
      endpoint_prefix=None,
  ):
    if not single_source_name:
      single_source_name = self.model_class.__tablename__
    if not list_source_name:
      list_source_name = single_source_name + "s"
    self.single_source_name = single_source_name
    self.list_source_name = list_source_name

    if not endpoint_prefix:
      endpoint_prefix = self.model_class.__name__
    self.endpoint_prefix = endpoint_prefix
    # 注册单条资源路由
    if "get_item" not in self.exclude_methods:
      self.app.add_url_rule(   # important
        url_prefix + "/" + single_source_name,
        endpoint=endpoint_prefix + ".get_item",
        view_func=self.get_item,
        methods=["GET"],
      )

    # 注册资源列表路由
    if "get_items" not in self.exclude_methods:
      self.app.add_url_rule(
        url_prefix + "/" + list_source_name,
        endpoint=endpoint_prefix + ".get_items",
        view_func=self.get_items,
        methods=["GET"],
      )

    # 注册新建路由
    if "post" not in self.exclude_methods:
      self.app.add_url_rule(
        url_prefix + "/" + single_source_name,
        endpoint=endpoint_prefix + ".post",
        view_func=self.post,
        methods=["POST"],
      )

    # 注册删除路由
    if "delete" not in self.exclude_methods:
      self.app.add_url_rule(
        url_prefix + "/" + single_source_name,
        endpoint=endpoint_prefix + ".delete",
        view_func=self.delete,
        methods=["DELETE"],
      )

    # 注册修改路由
    if "put" not in self.exclude_methods:
      self.app.add_url_rule(
        url_prefix + "/" + single_source_name,
        endpoint=endpoint_prefix + ".put",
        view_func=self.put,
        methods=["PUT"],
      )

    # 注册多项修改路由
    if "puts" not in self.exclude_methods and "puts" in self.include_methods:
      self.app.add_url_rule(
        url_prefix + "/" + list_source_name,
        endpoint=endpoint_prefix + ".puts",
        view_func=self.list_put,
        methods=["PUT"],
      )

  def single_auth_kwargs(self, kwargs):
    id, company_id = current_user.id, current_user.__dict__.get("company_id")
    temp_dict = dict(
      om={},
      engineer={"engineer_id": id},
      pm={"pm_id": id},
      purchase={"company_id": company_id},
      company_om={"company_id": company_id},
    )
    kwargs.update(temp_dict[current_user.role])

  def list_auth_kwargs(self, kwargs):
    self.single_auth_kwargs(kwargs)

  def _modify_args(self, kwargs):
    try:
      MS = eval("{}Status".format(self.model_class.__name__))
    except:
      # 如果没有MS， 则不需要执行下面
      return kwargs
    if "status" in kwargs:
      kwargs["status"] = MS.str2int(kwargs["status"])
    if "not_status" in kwargs:
      kwargs["not_status"] = MS.str2int(kwargs["not_status"])
    if "in_status" in kwargs:
      array_str = kwargs["in_status"]
      ss = json.loads(array_str)
      kwargs["in_status"] = json.dumps([MS.str2int(s) for s in ss])
    return kwargs

  def _get_model(self):
    kwargs = request.args.to_dict()
    kwargs.pop("action", None)
    kwargs.pop("schema", None)
    self.single_auth_kwargs(kwargs)
    kwargs = self._modify_args(kwargs)
    result = self.model_class.get_items(**kwargs)
    if len(result) > 1:
      raise NewComException("查询结果不唯一", 403)
    if not result:
      raise NewComException("找不着！", 404)
    return result[0]

  def _get_item(self):
    kwargs = request.args.to_dict()
    schema_type = kwargs.pop("schema", None)

    if not schema_type:
      schema = self.default_schema(many=False)
    else:
      schema = eval(schema_type)(many=False)
    self.single_auth_kwargs(kwargs)
    kwargs = self._modify_args(kwargs)
    result = self.model_class.get_items(**kwargs)
    if len(result) > 1:
      raise NewComException("查询结果不唯一", 403)
    if len(result) == 0:
      raise NewComItemNotExist("对象不存在", 404)
    return schema, result[0]

  @api_response
  def get_item(self):
    schema, result = self._get_item()
    return jsonify(schema.dump(result))

  def _get_items(self):
    kwargs = request.args.to_dict()
    kwargs = self._modify_args(kwargs)
    schema_type = kwargs.pop("schema", None)

    if not schema_type:
      schema = self.default_schema(many=True)
    else:
      schema = eval(schema_type)(many=True)

    self.list_auth_kwargs(kwargs)
    results, page_info = self.model_class.get_items_with_pages(**kwargs)
    return schema, kwargs, results, page_info

  @api_response
  def get_items(self):
    schema, kwargs, results, page_info = self._get_items()
    return jsonify({"data": schema.dump(results), "page_info": page_info.__dict__})

  @api_response
  def list_put(self):
    schema_type = request.args.get("schema", None)
    if not schema_type:
      raise Exception("put 接口必须有schema")
    models = self._get_items()[2]
    schema = eval(schema_type)(many=False, unknown=EXCLUDE)
    if BaseActionsSchema in eval(schema_type).mro():
      result = schema.act(models, request.json)
    else:
      raise NewComException("bad schema", 500)
    return jsonify(result or {})

  @api_response
  def put(self):
    schema_type = request.args.get("schema", None)
    if not schema_type:
      raise Exception("put 接口必须有schema")
    model = self._get_item()[1]
    schema = eval(schema_type)(many=False, unknown=EXCLUDE)
    if BaseActionSchema in eval(schema_type).mro():
      result = schema.act(model, request.json)
    else:
      result = schema.modify_model(model, request.json)
    if result:
      return jsonify(result)
    return jsonify({})

  def post_schema(self):
    schema_type = request.args.get("schema", None)
    if schema_type:
      schema = eval(schema_type)(many=False, unknown=EXCLUDE)
    else:
      schema = self.post_default_schema(many=False, unknown=EXCLUDE)
    return schema

  def post_data_modify(self):
    return dict(request.json)

  def post_model_modify(self, model):
    return model

  def new_model(self):
    schema = self.post_schema()
    data = self.post_data_modify()
    model = schema.load(data)
    self.post_model_modify(model)
    return model

  @api_response
  def post(self):
    """
    在1.0阶段，post的很多参数调整和额外逻辑是在api基类中完成的。
    后期要逐渐升级，有model的类做参数调整和额外逻辑。
    :return:
    """
    if "post" in self.model_class.__dict__:
      model = self.model_class.post(**dict(request.json))
    else:
      model = self.new_model()
      model.save()
    return jsonify({"id": model.id})

  def _before_delete(self, model):
    pass

  @api_response
  def delete(self):
    model = self._get_model()
    self._before_delete(model)
    try:
      model.delete()
    except Exception as e:
      raise NewComException("删除失败，请检查依赖项是否已经删除。", 500)
    return jsonify({})


class UserModelApi(ModelApi):
  include_methods = ["put"]

  def __init__(self, app_instance):
    super(UserModelApi, self).__init__(
      app_instance, User, default_schema=UserDefaultSchema
    )


class PmModelApi(ModelApi):
  post_default_schema = PmPostSchema

  def __init__(self, app_instance):
    super(PmModelApi, self).__init__(
      app_instance, Pm, default_schema=PmDefaultSchema
    )

  def _modify_args(self, kwargs):
    if current_user.role == "pm":
      kwargs["id"] = current_user.id
      kwargs.pop("pm_id", None)
    return kwargs

  @api_response
  def post(self):
    kwargs = dict(request.json)
    project_id = kwargs.get("project_id", 0)
    if project_id:
      kwargs.pop("project_id")
    model = self.model_class.post(**kwargs)
    if project_id:
      p = Project.query.filter_by(id=project_id).first()
      p.action_add_pm(**{"pm_id": model.id})
    return jsonify({"id": model.id})


class CompanyOmModelApi(ModelApi):
  post_default_schema = CompanyOmSchema
  include_methods = ["put"]

  def __init__(self, app_instance):
    super(CompanyOmModelApi, self).__init__(
      app_instance, CompanyOm, default_schema=CompanyOmSchema
    )

  def single_auth_kwargs(self, kwargs):
    super().single_auth_kwargs(kwargs)
    if current_user.role == "company_om":
      kwargs.update({"id": current_user.id})


class PurchaseModelApi(ModelApi):
  post_default_schema = PurchasePostSchema

  def __init__(self, app_instance):
    super(PurchaseModelApi, self).__init__(
      app_instance, Purchase, default_schema=PurchaseDefaultSchema
    )

  def post_model_modify(self, model):
    model.set_password(Config.DEFAULT_PWD)
    model.role = Roles.purchase


class EngineerModelApi(ModelApi):
  post_default_schema = EngineerPostSchema

  def __init__(self, app_instance):
    super(EngineerModelApi, self).__init__(
      app_instance, Engineer, default_schema=EngineerDefaultSchema
    )

  def post_data_modify(self):
    data = super().post_data_modify()
    abilities = data.get("abilities", [])
    if not abilities:
      raise NewComException("请添加技能信息", 500)
    from main.api.admin import _create_engineer_pre_username

    if not data.get("pre_username"):
      data["pre_username"] = _create_engineer_pre_username()
    return data

  def post_model_modify(self, model):
    model.set_password(Config.DEFAULT_PWD)
    model.role = Roles.engineer
    model.status = EngineerStatus.ready

  @api_response
  def _post(self):
    model = self.new_model()
    model.save()
    education_items = request.json.get("education", [])
    for education_item in education_items:
      education_item["engineer_id"] = model.id
      education = EducationPostSchema(many=False, unknown=EXCLUDE).load(
        education_item
      )
      education.save()
    cv_upload_result = request.json.get("cv_upload_result", None)
    model.search_index()
    if not cv_upload_result:
      if not Config.DEBUG:
        raise NewComException("简历呢？", 500)
    else:
      model.turn_cv2img(cv_upload_result)

    return jsonify({})


class CvSearchApi(EngineerModelApi):
  def __init__(self, app_instance):
    self.offer_id = None
    super(EngineerModelApi, self).__init__(app_instance, Engineer)

  def init_blueprint(self, url_prefix="/"):
    self.app.add_url_rule(
      url_prefix + "/" + "cvs",
      endpoint="cvs" + ".search",
      view_func=self.search,
      methods=["GET"],
    )

  def _modify_args(self, kwargs):
    super()._modify_args(kwargs)
    self.offer_id = kwargs.pop("offer_id")
    return kwargs

  @api_response
  def search(self):
    _, kwargs, results, page_info = self._get_items()
    pushed_interviews = Interview.query.filter_by(offer_id=self.offer_id)
    pushed_engineers = [pi.engineer_id for pi in pushed_interviews]
    schema = CvSearchSchema(many=True)
    data = schema.dump(results)
    for item in data:
      if item["id"] in pushed_engineers:
        item["pushed"] = True
    return jsonify({"data": data, "page_info": page_info.__dict__})


class ProjectModelApi(ModelApi):
  post_default_schema = ProjectPostSchema

  def __init__(self, app_instance):
    super(ProjectModelApi, self).__init__(
      app_instance, Project, default_schema=ProjectDefaultSchema
    )


class OfferModelApi(ModelApi):
  post_default_schema = OfferPostSchema

  def __init__(self, app_instance):
    super(OfferModelApi, self).__init__(
      app_instance, Offer, default_schema=OfferDefaultSchema
    )

  @api_response
  def get_item(self):
    kwargs = request.args.to_dict()
    schema_type = kwargs.pop("schema", None)

    if not schema_type:
      schema = self.default_schema(many=False)
    elif schema_type == 'OfferLogsSchema':
      pass
    else:
      schema = eval(schema_type)(many=False)

    self.single_auth_kwargs(kwargs)

    kwargs = self._modify_args(kwargs)

    if schema_type != 'OfferLogsSchema' and schema_type != 'OfferDetailSchema':
      result = self.model_class.get_items(**kwargs)
      if len(result) > 1:
        raise NewComException("查询结果不唯一", 403)
      if len(result) == 0:
        raise NewComItemNotExist("对象不存在", 404)

    if schema_type == 'OfferDetailSchema':   # getting detail information of the offer
      today = dt.date.today()
      result0 = today.strftime('%Y-%m-%d')
      result1 = Offer.get_offer_detail(**kwargs)  # detail information
      result2 = Offer.get_offer_data_list(**kwargs)  # resume data of the offer
      result3 = Offer.get_count_track(**kwargs)  # count track of today
      result4 = Offer.get_chat_information(**kwargs)  # data for chatbox
      result6, result5 = Offer.get_interview_pass_data(**kwargs)  # data for interview monitor box

    if schema_type == 'OfferLogsSchema':
      result = Offer.get_logs(**kwargs)
      return jsonify({'data': result})

    if schema_type == 'OfferDetailSchema':
      return jsonify({ 'today': result0, 'data': result1, \
       'offer_data_list': result2, 'count_tracks': result3, \
       'chat_data': result4, 'it_data': result5, 'it_data_num': result6 })
    else:
      return jsonify({'data': result})

  @api_response
  def put(self):
    kwargs = request.args.to_dict()
    id = kwargs.pop('id', None)
    schema = kwargs.pop('schema', None)
    if schema == 'OfferPostSchema':
      data = request.json
      Offer.updateData(id, data)
    elif schema == 'CloseOffer':
      Offer.closeOffer(id)

    return jsonify({'success': 1})

  @api_response
  def get_items(self):
    kwargs = request.args.to_dict()
    kwargs = self._modify_args(kwargs)

    schema_type = kwargs.pop("schema", None)

    if not schema_type:
      schema = self.default_schema(many=True)
    elif schema_type == 'OfferPersonData':
      pass
    else:
      schema = eval(schema_type)(many=True)

    # self.list_auth_kwargs(kwargs)
    # results, page_info = self.model_class.get_items_with_pages(**kwargs)

    if schema_type == "OfferDefaultSchemaWithStatistics":

      results, page_info = self.model_class.get_items_with_pages(**kwargs)

      # cobra-55555 -20-04-25
      new_data = []
      data = schema.dump(results)
      for item in data:
        new_item = item
        offer_id = item['id']

        written_pass_num, resume_collection_num, interview_pass_num = Offer.get_written_num(offer_id)
        new_item['written_pass_num'] = written_pass_num
        new_item['resume_collection_num'] = resume_collection_num
        new_item['interview_pass_num'] = interview_pass_num
        new_item['updated_datetime'] = new_item['updated'][:10] + ' ' + new_item['updated'][11:-9]
        new_data.append(new_item)

      statistics_schema = OfferStatisticSchema(many=False)
      statistics = statistics_schema.dump(OfferStatistics(results))
      return jsonify(
        {
          "data": new_data,
          "statistics": statistics,
          "page_info": page_info.__dict__,
        }
      )
    elif schema_type == "OfferPersonData":
      items, data = self.model_class.get_offer_person_data(**kwargs)
      statistics_data = self.model_class.get_statistics_modal_data(**kwargs)
      return jsonify(
        {
          "data": data,
          "items": items,
          "statistics": statistics_data,
        }
      )
    else:
      results = self.model_class.get_items(**kwargs)

      return jsonify(
        {"data": schema.dump(results), "page_info": page_info.__dict__}
      )

  """
  def post_data_modify(self):
    # 强制将公司id改为采购的公司id
    data = super().post_data_modify()
    if current_user.role == Roles.purchase:
      current_user_model = User.query.get(current_user.id)
      data['company_id'] = current_user_model.company_id
    return data

  def post_model_modify(self, model):
    # 创建项目经理和项目的多对多关系
    involve_pm = Pm.query.filter_by(id=model.pm_id).first()
    involve_project = Project.query.filter_by(id=model.project_id).first()
    involve_pm.projects.append(involve_project)
    involve_pm.save()
    # todo 添加 model.offer_sheet
    model.status = OfferStatus.open
    model.position_level_id = position_level.id
    return model
  """


class InterviewModelApi(ModelApi):
  post_default_schema = InterviewPostSchema

  def __init__(self, app_instance):
    super(InterviewModelApi, self).__init__(
      app_instance, Interview, default_schema=InterviewDefaultSchema
    )

  def post_model_modify(self, model):
    involve_offer = Offer.query.filter_by(id=model.offer_id).first()
    if not involve_offer.status == OfferStatus.open:
      raise NewComException("需求已经关闭", 500)
    involve_engineer = Engineer.query.get(model.engineer_id)
    if involve_engineer.status not in (
        EngineerStatus.ready,
        EngineerStatus.interview,
        EngineerStatus.entering,
    ):
      raise NewComException("工程师非待选状态", 501)
    model.update_from(
      involve_offer, "project_id", "company_id", "pm_id", "position_id"
    )
    # todo 增加position_levels
    model.status = InterviewStatus.cv_new
    involve_engineer.status = EngineerStatus.interview
    return model

  @api_response
  def get_item(self):
    schema, result = self._get_item()
    if result.status == InterviewStatus.cv_new and result.pm_id == current_user.id:
      result.update(status=InterviewStatus.cv_read)
    return jsonify(schema.dump(result))

  @api_response
  def get_items(self):  # 简历投递近况，近期面试经历
    schema, kwargs, results, page_info = self._get_items()

    if not isinstance(schema, InterviewClassifySchema):
      return jsonify(
        {"data": schema.dump(results), "page_info": page_info.__dict__}
      )
    else:
      data = dict(
        cv_new=[],
        cv_pass=[],
        interview_new=[],
        interview_pass=[],
        entry=[],
        reject=[],
      )
      cv_new = filter(
	  	lambda x: x.status in (InterviewStatus.cv_read, InterviewStatus.cv_new),
        results,
      )
      data["cv_new"] = schema.dump(cv_new)
      cv_pass = filter(lambda x: x.status == InterviewStatus.cv_pass, results)
      data["cv_pass"] = schema.dump(cv_pass)
      interview_new = filter(
        lambda x: x.status
        in [
          InterviewStatus.interview_new,
          InterviewStatus.interview_undetermined,
		],
        results,
      )
      data["interview_new"] = schema.dump(interview_new)
      interview_pass = filter(
        lambda x: x.status
        in (InterviewStatus.interview_pass, InterviewStatus.entry_new),
        results,
      )
      data["interview_pass"] = schema.dump(interview_pass)
      entry = filter(lambda x: x.status == InterviewStatus.om_pass, results)
      data["entry"] = schema.dump(entry)
      reject = filter(lambda x: x.status <= 0, results)
      data["reject"] = schema.dump(reject)
      return jsonify({"data": data})


class PositionModelApi(ModelApi):
  post_default_schema = PositionPostSchema

  def __init__(self, app_instance):
    super(PositionModelApi, self).__init__(
      app_instance, Position, default_schema=PositionDefaultSchema
    )


class PositionLevelModelApi(ModelApi):
  post_default_schema = PositionLevelPostSchema

  def __init__(self, app_instance):
    super(PositionLevelModelApi, self).__init__(
      app_instance, PositionLevel, default_schema=PositionLevelDefaultSchema
    )


class DailyLogModelApi(ModelApi):
  include_methods = ["item", "items", "put"]

  def __init__(self, app_instance):
    super(DailyLogModelApi, self).__init__(
      app_instance, DailyLog, default_schema=DailyLogDefaultSchema
    )

  @api_response
  def get_items(self):
    kwargs = request.args.to_dict()
    if kwargs.get("latest"):
      self.list_auth_kwargs(kwargs)
      results, page_info = DailyLog.get_latest_items(
        engineer_id=kwargs.get("engineer_id")
      )
      schema_type = kwargs.get("schema", None)
      if not schema_type:
        schema = self.default_schema(many=True)
      else:
        schema = eval(schema_type)(many=True)
      return jsonify(
        {"data": schema.dump(results), "page_info": page_info.__dict__}
      )
    else:
      return super().get_items()


class AbilityModeApi(ModelApi):
  def __init__(self, app_instance):
    super(AbilityModeApi, self).__init__(
      app_instance, Ability, default_schema=AbilitySchema
    )

  @api_response
  def put(self):
    result = super().put()
    model = self._get_item()[1]
    e = Engineer.query.get(model.engineer_id)
    e.s_ability = ",".join([x.name for x in e.ability])[:64]
    e.save()
    if e.now_career_id:
      e.now_career.update(s_ability=e.s_ability)
    return result


class EducationModeApi(ModelApi):
  def __init__(self, app_instance):
    super(EducationModeApi, self).__init__(
      app_instance, Education, default_schema=EducationDefaultSchema
    )

  @api_response
  def put(self):
    result = super().put()
    model = self._get_item()[1]
    model.update_highest()
    e = Engineer.query.get(model.engineer_id)
    e.s_education = ",".join(
      [x.school + "-" + x.degree + "-" + x.major for x in e.education]
    )[:64]
    if e.now_career_id:
      e.now_career.update(s_education=e.s_education)
    e.save()
    return result


class WorkReportModelApi(ModelApi):
  def __init__(self, app_instance):
    super(WorkReportModelApi, self).__init__(
      app_instance, WorkReport, default_schema=WorkReportDefaultSchema
    )

  @api_response
  def get_item(self):
    kwargs = request.args.to_dict()
    kwargs = self._modify_args(kwargs)
    self.single_auth_kwargs(kwargs)
    schema_type = kwargs.pop("schema", "WorkReportDetailSchema")
    if kwargs.get("latest", False):
      return latest_work_report()
    if not schema_type:
      schema = self.default_schema(many=False, unknown=EXCLUDE)
    else:
      schema = eval(schema_type)(many=False, unknown=EXCLUDE)

    result = self.model_class.get_items(**kwargs)
    if len(result) == 0:
      return latest_work_report()
    if len(result) > 1:
      raise NewComException("查询结果不唯一", 403)
    return jsonify(schema.dump(result[0]))

  @api_response
  def post(self):
    WorkReport.post(
      WorkReportPostSchema(many=False, unknown=EXCLUDE),
      current_user.id,
      request.json.get("year_month"),
    )
    return jsonify({})


class AuditModelApi(ModelApi):
  def __init__(self, app_instance):
    super(AuditModelApi, self).__init__(
      app_instance, Audit, default_schema=AuditDetailSchema
    )

  @api_response
  def get_items(self):
    kwargs = request.args.to_dict()
    self.list_auth_kwargs(kwargs)
    kwargs = self._modify_args(kwargs)
    if current_user.role == "engineer":
      kwargs["in_audit_type"] = '("leave", "extra_work", "work_report")'
    items, page_info = self.model_class.get_items_with_pages(**kwargs)
    results = []
    schema_types = {
      "leave": LeaveDefaultSchema,
      "extra_work": ExtraWorkDefaultSchema,
      "work_report": WorkReportDefaultSchema,
      "entry": EntryDefaultSchema,
      "resign": ResignDefaultSchema,
      "entry_file_audit": EntryFileAuditSchema,
    }
    for item in items:
      schema_type = schema_types[item.audit_type]
      json_item = schema_type(many=False).dump(item, many=False)
      results.append(json_item)

    return jsonify({"data": results, "page_info": page_info.__dict__})

  @api_response
  def get_item(self):
    kwargs = request.args.to_dict()
    kwargs = self._modify_args(kwargs)

    self.single_auth_kwargs(kwargs)
    result = self.model_class.get_items(**kwargs)
    if len(result) > 1:
      raise NewComException("查询结果不唯一", 403)
    if len(result) == 0:
      raise NewComException("查无此信息", 404)
    result = result[0]
    schema_types = {
      "leave": LeaveDefaultSchema,
      "extra_work": ExtraWorkDefaultSchema,
      "work_report": WorkReportDefaultSchema,
      "entry": EntryDefaultSchema,
      "entry_file_audit": EntryFileAuditSchema,
    }

    schema = schema_types[result.audit_type](many=False)
    return jsonify(schema.dump(result))


class EntryModelApi(ModelApi):
  def __init__(self, app_instance):
    super(EntryModelApi, self).__init__(
      app_instance, Entry, default_schema=EntryDefaultSchema
    )


class EnterProjectModelApi(ModelApi):
  def __init__(self, app_instance):
    super(EnterProjectModelApi, self).__init__(
      app_instance, EnterProject, default_schema=EnterProjectSchema
    )

  def _modify_args(self, kwargs):
    super()._modify_args(kwargs)
    kwargs["ing"] = 1
    return kwargs


class EngineerCompanyOrderModelApi(ModelApi):
  def __init__(self, app_instance):
    super(EngineerCompanyOrderModelApi, self).__init__(
      app_instance,
      EngineerCompanyOrder,
      default_schema=EngineerCompanyOrderSchema,
    )


class LeaveModeApi(ModelApi):
  post_default_schema = LeavePostSchema

  def __init__(self, app_instance):
    super(LeaveModeApi, self).__init__(
      app_instance, Leave, default_schema=LeaveDefaultSchema
    )

  def post_model_modify(self, model):
    current_engineer = Engineer.query.get(current_user.id)
    start_month = int_year_month(model.start_date)
    work_report = WorkReport.query.filter_by(
      career_id=current_engineer.now_career_id, year_month=start_month
    ).first()
    if work_report:
      raise NewComException("当月工时已提交，不可申请请假", 500)
    if not current_engineer.in_career_check():
      raise NewComException("该工程师未在入职日期内", 500)
    if model.leave_type == LeaveType.shift:
      if current_engineer.company.shift_type == 1:
        raise NewComException("加班模式不允许调休", 500)
      if (
          model.duration
          > engineer_can_shift_duration(current_engineer.id, get_today())[0]
      ):
        raise NewComException("调休尚未积攒如此多的时长", 500)
    if (
	dt.date(model.start_date.year, model.start_date.month, model.start_date.day)
        < current_engineer.now_career.start
    ):
      raise NewComException("未入职时间段不允许请假/调休", 500)
    copy_auth_info(model, current_engineer)
    model.engineer_id = current_engineer.id
    model.career_id = current_engineer.now_career_id
    days = workday_num_between(model.start_date, model.end_date)
    start_date = dt.datetime(
      model.start_date.year, model.start_date.month, model.start_date.day, 0, 0
    )
    end_date = dt.datetime(
      model.start_date.year, model.start_date.month, model.start_date.day, 23, 59
    )
    leaves = (
      Leave.query.filter_by(career_id=current_engineer.now_career_id)
      .filter(Leave.start_date.between(start_date, end_date))
      .all()
    )
    leaves = list(
      filter(lambda x: x.status in [AuditStatus.checked, AuditStatus.submit], leaves
      )
    )
    # 审批前，审批通过后，筛选申请时间是否符合要求
    for i in leaves:
      if i.start_date >= model.start_date and i.end_date >= model.end_date:
        raise NewComException("已存在输入时间段", 500)
      if i.start_date > model.start_date and i.end_date < model.end_date:
        db.session.delete(i)
      elif max(i.start_date, model.start_date) <= min(
          i.end_date, model.end_date
      ):  # 判断时间段是否重叠
        raise NewComException("存在重叠时间段", 500)
    # 如果请假时长超过8小时，且已提交日报，则修改日报类型origin_type为leave
    if days == 1:
      year_month_day = dt.date(
        model.start_date.year, model.start_date.month, model.start_date.day
      )
      dailylog = DailyLog.query.filter_by(date=year_month_day).first()
      if dailylog and model.duration >= 8:
        dailylog.update(origin_type=DailyLogType.leave)
    else:
      for i in range(model.start_date.day, model.end_date.day + 1):
        year_month_day = dt.date(
          model.start_date.year, model.start_date.month, model.start_date.day
        )
        dailylog = DailyLog.query.filter_by(date=year_month_day).first()
        if dailylog and model.duration >= 8:
          dailylog.update(origin_type=DailyLogType.leave)

  def _before_delete(self, model):
    if not model.status == AuditStatus.submit:
      raise NewComException("只有审核状态可以撤回", 500)


class ExtraWorkModelApi(ModelApi):
  post_default_schema = ExtraWorkPostSchema

  def __init__(self, app_instance):
    super(ExtraWorkModelApi, self).__init__(
      app_instance, ExtraWork, default_schema=ExtraWorkDefaultSchema
    )

  def post_model_modify(self, model):
    current_engineer = Engineer.query.get(current_user.id)
    start_month = int_year_month(model.start_date)
    work_report = WorkReport.query.filter_by(
      career_id=current_engineer.now_career_id, year_month=start_month
    ).first()
    if work_report:
      raise NewComException("当月工时已提交，不可申请加班", 500)
    if not current_engineer.in_career_check():
      raise NewComException("该工程师未在入职日期内", 500)
    if (dt.date(model.start_date.year, model.start_date.month, model.start_date.day)
        < current_engineer.now_career.start
    ):
      raise NewComException("未入职时间段不允许加班", 500)
    copy_auth_info(model, current_engineer)
    model.engineer_id = current_engineer.id
    model.career_id = current_engineer.now_career_id
    start_date = dt.datetime(
      model.start_date.year, model.start_date.month, model.start_date.day, 0, 0
    )
    end_date = dt.datetime(
      model.start_date.year, model.start_date.month, model.start_date.day, 23, 59
    )
    extra_works = (
      ExtraWork.query.filter_by(career_id=current_engineer.now_career_id)
      .filter(ExtraWork.start_date.between(start_date, end_date))
      .all()
    )
    extra_works = list(
      filter(
	  lambda x: x.status in [AuditStatus.checked, AuditStatus.submit],
      extra_works,
      )
    )
    for i in extra_works:
      if i.start_date <= model.start_date and i.end_date >= model.end_date:
        raise NewComException("已存在输入时间段", 500)
      if i.start_date > model.start_date and i.end_date < model.end_date:
        db.session.delete(i)
      elif max(i.start_date, model.start_date) <= min(
          i.end_date, model.end_date
      ):  # 判断时间段是否重叠
        raise NewComException("存在重叠时间段", 500)


def _before_delete(self, model):
  if not model.status == AuditStatus.submit:
    raise NewComException("只有审核状态可以撤回", 500)


class CareerModeApi(ModelApi):
  include_methods = ["items", "item"]

  def __init__(self, app_instance):
    super(CareerModeApi, self).__init__(
      app_instance, Career, default_schema=CareerDefaultSchema
    )

  def _modify_args(self, kwargs):
    try:
      MS = eval("{}Status".format(self.model_class.__name__))
    except:
      # 如果没有MS， 则不需要执行下面
      return kwargs
    if "status" in kwargs:
      kwargs["status"] = MS.str2int(kwargs["status"])
    if "lt_status" in kwargs:
      kwargs["lt_status"] = MS.str2int(kwargs["lt_status"])
    if "not_status" in kwargs:
      kwargs["not_status"] = MS.str2int(kwargs["not_status"])
    else:
      kwargs["not_status"] = MS.str2int("entering")
    return kwargs


class ResignModeApi(ModelApi):
  post_default_schema = ResignPostSchema
  include_methods = ["items", "item", "post", "put"]

  def __init__(self, app_instance):
    super(ResignModeApi, self).__init__(
      app_instance, Resign, default_schema=ResignDefaultSchema
    )

  @api_response
  def post(self):
    schema = self.post_schema()
    data = self.post_data_modify()
    kwargs = schema.dump(schema.load(data))
    Resign.post(**kwargs)
    return jsonify({})


class PaymentModeApi(ModelApi):
  include_methods = ["items", "item", "puts"]

  def __init__(self, app_instance):
    super(PaymentModeApi, self).__init__(
      app_instance, Payment, default_schema=PaymentDefaultSchema
    )


class MonthlyBillModeApi(ModelApi):
  include_methods = ["items", "item", "post"]
  post_default_schema = MonthlyBillPostSchema

  def __init__(self, app_instance):
    super(MonthlyBillModeApi, self).__init__(
      app_instance, MonthlyBill, default_schema=MonthlyBillDefaultSchema
    )

  """
  @api_response
  def post(self):
    schema = self.post_schema()
    data = self.post_data_modify()
    kwargs = schema.dump(data)
    MonthlyBill.post(**kwargs)
    return jsonify({})
  """

  @api_response
  def get_item(self):
    try:
      schema, result = self._get_item()
      return jsonify(schema.dump(result))
    except NewComException as e:
      if e.status_code == 404:
        return jsonify({}), 200


class SelfApi(ModelApi):
  include_methods = ["put", "item"]

  def __init__(self, app_instance):
    super(SelfApi, self).__init__(app_instance, User)

  def init_blueprint(self, url_prefix="/"):
    super().init_blueprint(
      single_source_name="self",
      list_source_name=False,
      url_prefix=url_prefix,
      endpoint_prefix="self",
    )

  @api_response
  def get_item(self):
    schema_type = request.args.get("schema", None)
    if schema_type:
      schema = eval(schema_type)(many=False)
    else:
      schemas = {
        "engineer": EngineerDetailSchema,
        "pm": PmDetailSchema,
        "purchase": PurchaseDetailSchema,
        "om": UserDefaultSchema,
        "company_om": CompanyOmSchema,
      }
      schema = schemas[current_user.role](many=False)
    return jsonify(schema.dump(User.query.get(int(current_user.id))))

  def single_auth_kwargs(self, kwargs):
    kwargs["id"] = current_user.id  # todo 莫名其妙的慢，需要找原因
    return kwargs


class SelfPassword(ModelApi):
  include_methods = ["put"]

  def __init__(self, app_instance):
    self.app = app_instance

  def init_blueprint(self, url_prefix):
    self.app.add_url_rule(
      url_prefix + "/self/password",
      endpoint="engineer.password",
      view_func=self.change_password,
      methods=["PUT"],
    )

  @api_response
  def change_password(self):
    kwargs = request.json
    kwargs = PasswordSchema(many=False).load(kwargs)
    user = User.query.get(current_user.id)
    if user.verify_password(kwargs.get("old_password")):
      user.set_password(kwargs.get("new_password"))
      user.save()
    else:
      raise NewComException("错误的原密码", 5000)
    return jsonify({})


class ToBeUpdateCompanyModelApi(ModelApi):
  include_methods = ["item", "post"]

  def __init__(self, app_instance):
    super(ToBeUpdateCompanyModelApi, self).__init__(
      app_instance, ToBeUpdateCompany, default_schema=ToBeUpdateCompanyDefaultSchema
    )
