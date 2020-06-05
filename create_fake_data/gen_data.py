# coding=utf-8
import json
import os
import shutil
import random
from faker import Faker
import traceback
from queue import Queue

from create_fake_data import test_app, AuthUser
from main.model import *
from main.util.work_dates import after_some_work_days, get_today, set_today, month_first_end_date, workday_num_between, \
    str_date, enter_next_work_date, after_some_days, enter_next_date

root_path = '/Users/chaos/Project/Company/newcom'
if not os.path.exists(root_path):
    root_path = '/home/ubuntu/project/nk/newcom'
f = Faker(locale='zh_CN')

default_password = 'nk123456'


def create_company():
    already_company = Company.query.order_by(db.desc(Company.id)).first()
    company_index = already_company.id + 1 if already_company else 1
    name = f.company()
    company_om = f.name()
    email = f.email()
    # phone = '13366556715'  #
    phone = f.phone_number()
    contract_name = '94017386-6fac-11e9-a419-acbc329114cf.r.pdf'
    contract_path = os.path.join(root_path, 'create_fake_data', contract_name)
    site_files = os.path.join(root_path, 'main', 'files', 'tem', contract_name)
    shutil.copyfile(contract_path, site_files)
    om_user = AuthUser('admin', default_password)
    company_data = dict(name=name, contact=company_om, phone=phone, email=email,
                        address='adfa adf',
                        om_name=phone,
                        billing_cycle=1,
                        service_fee_rate=0.1,
                        tax_rate=0.05,
                        hr_fee_rate=0.03,
                        finance_rate=0.01
                        )

    result = om_user.post('/api/v1/company', json=company_data)
    result = json.loads(result)
    return result['id']


def create_pm_purchase_project(com_id):
    u = CompanyOm.query.filter_by(company_id=com_id).first()
    cou = AuthUser(u.username, default_password)

    _om = AuthUser('admin', default_password)
    from main.api.admin import _create_pre_username
    cg = {"pre_username": _create_pre_username(com_id),
          "real_name": f.name(),
          "phone": f.phone_number()}
    cou.post('/api/v1/purchase', json=cg)

    _pm = {"pre_username": _create_pre_username(com_id),
           "real_name": f.name(),
           "phone": f.phone_number()}
    cou.post('/api/v1/pm', json=_pm)

    _pm = {"pre_username": _create_pre_username(com_id),
           "real_name": f.name(),
           "phone": f.phone_number()}
    cou.post('/api/v1/pm', json=_pm)

    _project = {
        "company_id": com_id,
        "name": "项目{}".format(random.randint(0, 1000))
    }
    cou.post('/api/v1/project', json=_project)

    _project = {
        "company_id": com_id,
        "name": "项目{}".format(random.randint(0, 1000))
    }
    cou.post('/api/v1/project', json=_project)


def add_pm2project(com_id):
    u = CompanyOm.query.filter_by(company_id=com_id).first()
    cou = AuthUser(u.username, default_password)
    _pms = Pm.query.filter_by(company_id=com_id).all()
    _projects = Project.query.filter_by(company_id=com_id).all()
    for _project in _projects:
        for _pm in _pms:
            cou.put('/api/v1/project?id={}&schema=ProjectAddPmSchema'.format(_project.id),
                    json={"pm_id": _pm.id})


def create_position_level(com_id):
    u = CompanyOm.query.filter_by(company_id=com_id).first()
    cou = AuthUser(u.username, default_password)
    _position = {"name": "前端", "salary_type": 0,
                 "position_levels": [{"name": "p1", "money": 500},
                                     {"name": "p2", "money": 600}]}
    cou.post('/api/v1/position', json=_position)


def create_offer(cou, data):
    _offer = {
        "name": "需求_{}_{}".format(data['pm_id'], data['project_id']),
        "description": "1211 11as df asdf1 1111",
        "work_place": "asdfadsf",
        "salary_type": 0,
        "amount": 3
    }
    data.update(_offer)
    cou.post('/api/v1/offer', json=data)


def create_offers(com_id):
    u = CompanyOm.query.filter_by(company_id=com_id).first()
    cou = AuthUser(u.username, default_password)

    _projects = Project.query.filter_by(company_id=com_id).all()
    _pms = Pm.query.filter_by(company_id=com_id).all()
    _position = Position.query.filter_by(company_id=com_id).first()
    for _pj in _projects:
        for _pm in _pms:
            data = dict(pm_id=_pm.id, project_id=_pj.id, position_id=_position.id,
                        position_levels=[p.id for p in _position.position_levels])
            create_offer(cou, data)


def create_engineer(om_user):
    engineer_data = {
        "email": f.email(),
        "real_name": "测" + f.name()[1:],
        "phone": f.phone_number(),
        "gender": random.randint(0, 1),
        "job_wanted_status": "positive",
        "education": [
            {"school": "清华", "major": "拖拉机", "degree": "本科", "start_date": "2011-01-01", "end_date": "2014-01-01"}],
        "ability": [{"name": "python", "level": "3年"}, {"name": "java", "level": "2年"}],
        "cv_upload_result": "4f88b228-8dc0-11e9-9632-acbc329114cf.劳动合同.pdf"
    }
    try:
        om_user.post('/api/v1/engineer', json=engineer_data)
    except Exception as e:
        print(e)
        print(traceback.format_exc)


def create_engineers():
    om_user = AuthUser('admin', default_password)
    for i in range(42):
        create_engineer(om_user)


def push_engineer_to_offer(cou, _e, _o):
    try:
        cou.post('/api/v1/interview', json={'offer_id': _o.id, 'engineer_id': _e.id})
    except Exception as e:
        print(e)
        print(traceback.format_exc())


def push_engineers_to_offers(com_id):
    c = Company.query.filter_by(id=com_id).first()
    _om = AuthUser('admin', default_password)
    _offers = Offer.query.filter_by(company_id=com_id).all()
    _es = Engineer.query.filter(Engineer.real_name.like('测%'), Engineer.created > c.created).all()
    _eq = Queue()
    for _e in _es:
        _eq.put(_e)
    for _o in _offers:
        for i in range(8):
            _e = _eq.get()
            push_engineer_to_offer(_om, _e, _o)


def pm_pass_cv(omu, _pmu, _iv, index):
    if index > 20:
        return
    appoint_time = _pmu.get('/api/v1/pm?schema=PmAppointTimeSchema')
    appoint_time = json.loads(appoint_time)
    for d in appoint_time['default_can_appoint_time']:
        d['am'] = True
    # 设置默认面试时间。
    _pmu.put('/api/v1/pm?schema=PmCanAppointTimePutSchema',
             json={"set_info": appoint_time['default_can_appoint_time'], "set_default": True})
    # 简历通过
    _pmu.put('/api/v1/interview?id={}&schema=InterviewStatusPutSchema'.format(_iv.id),
             json={'status': InterviewStatus.cv_pass, "pm_free_time": appoint_time['default_can_appoint_time']})
    if index > 16:
        return
    # 约面试
    apt = appoint_time['default_can_appoint_time'][0]
    omu.put('/api/v1/interview?id={}&schema=InterviewStatusPutSchema'.format(_iv.id),
            json={'status': InterviewStatus.interview_new, 'appoint_time': apt})
    if index > 12:
        return
    # 面试通过
    _of = Offer.query.filter_by(id=_iv.offer_id).first()
    omu.put('/api/v1/interview?id={}&schema=InterviewStatusPutSchema'.format(_iv.id),
            json={"status": InterviewStatus.interview_pass,
                  'final_position_level_id': _of.position_levels[0].id,
                  'result_note': "哈哈"})

    if index > 8:
        return
    _entry = omu.put('/api/v1/interview?id={}&schema=InterviewEntryPutSchema'.format(_iv.id),
                     json={'date': after_some_work_days(1).strftime('%Y-%m-%d')})
    _entry_id = json.loads(_entry)['entry_id']
    _pmu.put('/api/v1/entry?id={}&schema=EntryCheckSchema'.format(_entry_id),
             json={'status': AuditStatus.checked})


def pms_pass_cvs(com_id):
    omu = AuthUser('admin', default_password)
    _ivs = Interview.query.filter_by(company_id=com_id).all()
    for index, _iv in enumerate(_ivs):
        _pm = Pm.query.filter_by(id=_iv.pm_id).first()
        _pmu = AuthUser(_pm.phone, default_password)
        pm_pass_cv(omu, _pmu, _iv, index)


def com_agree_entry(com_id):
    c = Company.query.filter_by(id=com_id).first()
    u = CompanyOm.query.filter_by(company_id=com_id).first()
    cou = AuthUser(u.username, default_password)
    eps = EnterProject.query.filter_by(company_id=com_id, status=EnterProjectStatus.pm_agree).all()
    reject_id = eps[0].id
    cou.put('/api/v1/enter_project?id={}&schema=EnterProjectRejectSchema'.format(reject_id))
    for ep in eps[1:]:
        cou.put('/api/v1/enter_project?id={}&schema=EnterProjectCheckSchema'.format(ep.id),
                json={
                    "work_content": "sdfads",
                    "service_type": "asdfa",
                    "auto_renew": 1,
                    "renew_cycle": 3
                })


def om_check_entry(com_id):
    c = Company.query.filter_by(id=com_id).first()
    _om = AuthUser('admin', default_password)
    eps = EnterProject.query.filter_by(company_id=com_id, status=EnterProjectStatus.purchase_agree).all()
    reject_id = eps[0].id
    _om.put('api/v1/enter_project?id={}&schema=EnterProjectOmRejectSchema'.format(reject_id), json={})
    for ep in eps[1:]:
        _om.put('/api/v1/enter_project?id={}&schema=EnterProjectOmCheckSchema'.format(ep.id),
                json={
                    "employ_type": 0,
                    "tax_free_rate": 0.1
                })


def engineer_do_work(pmu, eu, begin):
    real_month = dt.date.today().month
    cursor = begin.month + 1
    for i in range(real_month - begin.month):
        set_today(dt.date(year=begin.year, month=cursor, day=1))
        eu.get('/api/v1/daily_logs?latest=True')
        dls = DailyLog.query.filter_by(engineer_id=eu.id, origin_type='normal_work').all()
        for dl in dls:
            # 填写日志
            eu.put('/api/v1/daily_log?id={}&schema=DailyLogPutSchema'.format(dl.id),
                   json={"content": "干活", "duration": 1})
        # 提交工时报告
        eu.post('/api/v1/work_report', json={
            "year_month": begin.year * 100 + cursor - 1
        })
        wr = WorkReport.query.filter_by(engineer_id=eu.id, year_month=begin.year * 100 + cursor - 1).first()
        pmu.put('/api/v1/work_report?id={}&schema=WorkReportCheckPutSchema'.format(wr.id), json={
            "status": "checked", "attitude_score": 5, "ability_score": 5
        })
        cursor = cursor + 1
    set_today(begin)


def delete_daily_work(pmu, eu):
    pass


def engineers_do_work(com_id):
    set_today('20190522')
    begin = get_today()
    pms = Pm.query.filter_by(company_id=com_id).all()
    for _pm in pms:
        pmu = AuthUser(_pm.pre_username, default_password)
        es = Engineer.query.filter_by(company_id=com_id, status='on_duty', pm_id=_pm.id).all()
        for e in es:
            eu = AuthUser(e.pre_username, default_password)
            engineer_do_work(pmu, eu, begin)


def create_data():
    set_today('20190522')
    com_index = create_company()
    create_pm_purchase_project(com_index)
    add_pm2project(com_index)
    create_position_level(com_index)
    create_offers(com_index)
    create_engineers()
    push_engineers_to_offers(com_index)
    pms_pass_cvs(com_index)
    com_agree_entry(com_index)
    om_check_entry(com_index)
    engineers_do_work(com_index)


def delete_audit(com_id):
    sql_tem = "delete `delete_table` from `audit` left join `delete_table` on audit.id=`delete_table`.id where company_id={}"
    db.session.execute(sql_tem.format(com_id).replace('delete_table', "entry"))
    db.session.execute(sql_tem.format(com_id).replace('delete_table', "work_report"))
    db.session.execute(sql_tem.format(com_id).replace('delete_table', "extra_work"))
    db.session.execute(sql_tem.format(com_id).replace('delete_table', "leave"))
    sql_tem = "delete from audit where company_id={}".format(com_id)
    db.session.execute(sql_tem)
    db.session.commit()


def delete_data(com_id):
    c = Company.query.filter_by(id=com_id).first()

    sql_tem = 'delete from {} where company_id={}'
    db.session.execute(sql_tem.format('daily_log', c.id))
    db.session.execute(sql_tem.format('payment', c.id))
    delete_audit(com_id)
    db.session.execute(sql_tem.format('monthly_bill', c.id))
    db.session.execute(sql_tem.format('engineer_company_order', c.id))
    db.session.execute(sql_tem.format('enter_project', c.id))

    db.session.execute(sql_tem.format('career', c.id))
    db.session.commit()

    _eps = EnterProject.query.filter(EnterProject.company_id == com_id).all()
    for _ep in _eps:
        _ep.delete()
    _es = Engineer.query.filter(Engineer.real_name.like("测%"), Engineer.created >= c.created).all()
    for _e in _es:
        _entries = Entry.query.filter_by(engineer_id=_e.id).all()
        for _en in _entries:
            _en.delete()
        _ivs = Interview.query.filter_by(engineer_id=_e.id).all()
        for _iv in _ivs:
            _iv.delete()
        _e.delete()
        for a in Ability.query.filter_by(engineer_id=_e.id).all():
            a.delete()
        for e in Education.query.filter_by(engineer_id=_e.id).all():
            e.delete()

    _offers = Offer.query.filter_by(company_id=com_id).all()
    for _o in _offers:
        _o.delete()

    _positions = Position.query.filter_by(company_id=com_id).all()
    for _p in _positions:
        for _pl in _p.position_levels:
            _pl.delete()
        _p.delete()

    _pms = Pm.query.filter_by(company_id=com_id).all()
    for _pm in _pms:
        _pm.delete()
    _pus = Purchase.query.filter_by(company_id=com_id).all()

    for _pu in _pus:
        _pu.delete()
    CompanyOm.query.filter_by(company_id=com_id).first().delete()

    _projects = Project.query.filter_by(company_id=com_id).all()
    for _project in _projects:
        _project.delete()

    c.delete()


if __name__ == '__main__':
    want_to_create, delete_id = True, 23
    if want_to_create:
        create_data()
    else:
        delete_data(delete_id)
