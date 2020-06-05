from . import test_app, AuthUser
from main.model import *


def test_token():
    admin = User.query.filter_by(role='admin').first()
    response = test_app.post('/api/v1/auth/token', json={'username': admin.username, 'password': '111111'})
    assert response.status_code == 200


def test_auth_user():
    admin_user = AuthUser('admin')
    purchase_object = Purchase.query.filter().first()
    purchase_user = AuthUser(purchase_object.pre_username)
    pm_object = Pm.query.filter().first()
    pm_user = AuthUser(pm_object.pre_username)
    engineer_object = Engineer.query.filter().first()
    engineer_user = AuthUser(engineer_object.pre_username)

    admin_get_companies = admin_user.get_json('/companies')
    assert len(admin_get_companies['data']) > 1
    purchase_get_companies = purchase_user.get_json('/companies')
    purchase_get_company = purchase_user.get_json('company')
    assert purchase_get_company['id'] == purchase_object.company_id
    assert len(purchase_get_companies['data']) == 1
    assert purchase_get_companies['data'][0]['id'] == purchase_object.company_id
    pm_get_companies = pm_user.get_json('/companies')
    assert len(pm_get_companies['data']) == 1
    assert pm_get_companies['data'][0]['id'] == pm_object.company_id

    admin_get_all_projects = admin_user.get_json('/projects')
    purchase_get_all_projects = purchase_user.get_json('/projects')
    assert len(admin_get_all_projects['data']) > len(purchase_get_all_projects['data'])
    for project in purchase_get_all_projects['data']:
        assert project['company_id'] == purchase_object.company_id
