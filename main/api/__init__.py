import datetime as dt

import jwt
from flask import current_app

from main.api.model_api import *
from main.api.admin import CompanyModelApi


class LongLastUser(object):
    def __init__(self, u):
        self.id = u.id
        self.role = u.role
        self.created = u.created
        self.phone = u.phone
        self.username = u.username
        self.email = u.email
        self.gender = u.gender
        self.head_img = u.head_img
        self.pre_username = u.pre_username
        if hasattr(u, 'company_id'):
            self.company_id = u.company_id


@login_manager.request_loader
def load_user_from_request(request):
    token = request.headers.get('Authorization')
    if token:
        token = token.split(' ')[-1]
        try:
            payload = jwt.decode(token, Config.SECRET_KEY, algorithms=[Config.JWT_ALGORITHM, ])
        except jwt.ExpiredSignatureError:
            raise NewComException('token已过期！', 401)
        except jwt.InvalidTokenError:
            raise NewComException('错误的token！', 401)
        user_id = payload['uid']
        user_model = User.query.get(int(user_id))
        if user_model:
            if not user_model.activate:
                raise NewComException('账户处在禁用状态', 401)
            current_app.logger.info('{} {}-{}-{} {} {}'.format(
                dt.datetime.now().strftime("%H:%M:%S"),
                user_model.role,
                user_model.username or user_model.pre_username,
                user_model.id,
                request.method,
                request.full_path))
            return LongLastUser(user_model)
    raise NewComException('权限不对', 401)


def init_model_api(app):
    UserModelApi(app).init_blueprint(url_prefix='/api/v1')
    PmModelApi(app).init_blueprint(url_prefix='/api/v1')
    PurchaseModelApi(app).init_blueprint(url_prefix='/api/v1')
    EngineerModelApi(app).init_blueprint(url_prefix='/api/v1')
    ProjectModelApi(app).init_blueprint(url_prefix='/api/v1')
    OfferModelApi(app).init_blueprint(url_prefix='/api/v1')
    InterviewModelApi(app).init_blueprint(url_prefix='/api/v1')
    PositionModelApi(app).init_blueprint(url_prefix='/api/v1')
    PositionLevelModelApi(app).init_blueprint(url_prefix='/api/v1')
    AuditModelApi(app).init_blueprint(url_prefix='/api/v1')
    EntryModelApi(app).init_blueprint(url_prefix='/api/v1', list_source_name='entries')
    LeaveModeApi(app).init_blueprint(url_prefix='/api/v1')
    ExtraWorkModelApi(app).init_blueprint(url_prefix='/api/v1')
    DailyLogModelApi(app).init_blueprint(url_prefix='/api/v1')
    WorkReportModelApi(app).init_blueprint(url_prefix='/api/v1')
    CareerModeApi(app).init_blueprint(url_prefix='/api/v1')
    ResignModeApi(app).init_blueprint(url_prefix='/api/v1')
    MonthlyBillModeApi(app).init_blueprint(url_prefix='/api/v1')
    PaymentModeApi(app).init_blueprint(url_prefix='/api/v1')
    SelfApi(app).init_blueprint(url_prefix='/api/v1')
    SelfPassword(app).init_blueprint(url_prefix='/api/v1')
    CvSearchApi(app).init_blueprint(url_prefix='/api/v1')
    EducationModeApi(app).init_blueprint(url_prefix='/api/v1')
    AbilityModeApi(app).init_blueprint(url_prefix='/api/v1')
    EnterProjectModelApi(app).init_blueprint(url_prefix='/api/v1')
    EngineerCompanyOrderModelApi(app).init_blueprint(url_prefix='/api/v1')
    CompanyOmModelApi(app).init_blueprint(url_prefix='/api/v1')


def init_api(app):
    init_model_api(app)

    from .upload import init_upload_url
    init_upload_url(app, '/api/v1/')

    from .admin import init_api
    init_api(app, '/api/v1/')

    from .auth import init_api
    init_api(app, '/api/v1')

    from .engineer import init_api
    init_api(app, '/api/v1/')

    from .purchase import init_api
    init_api(app, '/api/v1/')

    from .scheduler import init_api
    init_api(app, '/api/v1/')

    from .files import init_api
    init_api(app, '/api/v1')
