import shutil

from flask_login import current_user
from flask import request, jsonify, current_app

from .model_api import ModelApi
from ..model import *
from ..schema.base import BasePutSchema, BaseActionSchema
from ..schema.company import CompanyPostSchema, CompanyDefaultSchema, CompanyPutSchema
from config import load_config
from ..util.try_catch import api_response
from ..exception import NewComException
from .files import EntryFileTemplate

Config = load_config()


class CompanyModelApi(ModelApi):
    post_default_schema = CompanyPostSchema

    def __init__(self, app_instance):
        super(CompanyModelApi, self).__init__(
            app_instance, Company, default_schema=CompanyDefaultSchema
        )

    # 这里只需添加单条授权，多条授权会自动继承
    def single_auth_kwargs(self, kwargs):
        if not current_user.role == "om":
            kwargs["id"] = current_user.company_id

    def post_data_modify(self):
        data = super().post_data_modify()
        om_name = User.query.filter_by(username=data["om_name"]).first()
        if om_name:
            raise NewComException("该公司账号已被注册，请更换！", 403)
        phone = User.query.filter_by(phone=data["phone"]).first()
        company_phone = Company.query.filter_by(phone=data["phone"]).first()
        if phone or company_phone:
            raise NewComException("该手机号已被注册，请更换！", 403)
        email = User.query.filter_by(email=data["email"]).first()
        if email:
            raise NewComException("该邮箱已被注册，请更换！", 403)
        if request.json.get("contract_upload_result", None):
            return self.deal_contract_name(data)
        return data

    @staticmethod
    def deal_contract_name(data):
        tem_filename = data["contract_upload_result"]
        file_uuid = tem_filename.split(".")[0]
        file_name = ".".join(tem_filename.split(".")[1:])
        data["contract_name"] = file_name
        data["contract_uuid"] = file_uuid
        del data["contract_upload_result"]
        return data

    @staticmethod
    def copy_contract(model):
        contract_dir = os.path.join(Config.ROOT_DIR, Config.FILE_CONTRACT_PATH)
        tem_dir = os.path.join(Config.ROOT_DIR, Config.FILE_TEM_PATH)

        shutil.copy(
            os.path.join(
                tem_dir, "{}.{}".format(model.contract_uuid, model.contract_name)
            ),
            os.path.join(contract_dir, model.contract_uuid),
        )

    @staticmethod
    def patch_company_om(model):
        # 1.0到1.0.1过度期间使用
        # 功能是利用公司的联系人创建甲方管理账户。
        com = CompanyOm.query.filter_by(company_id=model.id).first()
        if not com:
            if not re.match("[a-zA-Z][a-zA-Z0-9_-]{4,16}", model.om_name):
                raise NewComException("账户名不符合要求！", 501)
            com = CompanyOm(
                company_id=model.id,
                username=model.om_name,
                role=Roles.company_om,
                real_name=model.om_name,
                gender=1,
            )
            com.set_password(Config.DEFAULT_PWD)
            com.save()
        else:
            if not re.match("[a-zA-Z][a-zA-Z0-9_-]{4,16}", model.om_name):
                raise NewComException("账户名不符合要求！", 501)
            com.username = model.om_name
            com.real_name = model.om_name
            com.save()

    def post_model_modify(self, model):
        model.activate = 1
        model.save()
        EntryFileTemplate.set_default_for_company(model.id)
        try:
            self.patch_company_om(model)
        except Exception as e:
            model.delete()
            raise e

    @api_response
    def put(self):
        schema_type = request.args.get("schema", None)
        if not schema_type:
            raise Exception("put 接口必须有schema")
        model = self._get_item()[1]
        schema = eval(schema_type)(many=False)
        if BaseActionSchema in eval(schema_type).mro():
            result = schema.act(model, request.json)
            return jsonify(result)
        else:
            data = dict(request.json)
            if data.get("contract_upload_result", None):
                data = self.deal_contract_name(data)
            if model.om_name != data["om_name"]:
                om_name = User.query.filter_by(username=data["om_name"]).first()
                if om_name:
                    raise NewComException("该公司账号已被注册，请更换！", 403)
            schema.modify_model(model, data)
            self.patch_company_om(model)
            return jsonify({})


def _create_pre_username(company_id):
    p_last = User.query.order_by(User.id.desc()).first()
    return "C{}P{}".format(company_id, p_last.id + 1)


def _create_engineer_pre_username():
    p_last = User.query.order_by(User.id.desc()).first()
    return "e{}".format(p_last.id + 1)


@api_response
def create_pre_username():
    company_id = int(request.json["company_id"])
    return _create_pre_username(company_id)


@api_response
def company_month_pay():
    if not Roles.om == current_user.role:
        raise NewComException("错误的权限", 5000)
    company_id = int(request.args.get("company_id"))
    year_month = int(request.args.get("year_month"))
    payments = Payment.query.filter_by(
        company_id=company_id, year_month=year_month
    ).all()
    total = sum(p.company_pay for p in payments)
    return jsonify({"total": round(total, 2)})


@api_response
def send_payments():
    if not Roles.om == current_user.role:
        raise NewComException("错误的权限", 5000)
    company_id = int(request.args.get("company_id"))
    year_month = int(request.args.get("year_month"))
    sql = 'update payment set status="{}" where company_id={} and `year_month`={} and status="{}"'
    try:
        db.session.execute(
            sql.format(PaymentStatus.submit, company_id, year_month, PaymentStatus.new)
        )
        db.session.commit()
        return jsonify({})
    except Exception as e:
        db.session.rollback()
        NewComException("发送结算失败", 501)


def init_api(app, url_prefix):
    CompanyModelApi(app).init_blueprint(
        list_source_name="companies", url_prefix="/api/v1"
    )

    app.add_url_rule(
        os.path.join(url_prefix, "pre_username"),
        endpoint="admin.create_pre_username",
        view_func=create_pre_username,
        methods=["POST"],
    )
    app.add_url_rule(
        os.path.join(url_prefix, "company_month_pay"),
        endpoint="admin.company_month_pay",
        view_func=company_month_pay,
        methods=["GET"],
    )
    app.add_url_rule(
        os.path.join(url_prefix, "om_send_payments"),
        endpoint="admin.send_payments",
        view_func=send_payments,
        methods=["PUT"],
    )
