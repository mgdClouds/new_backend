# coding=utf-8
import json
import random

from main.model import *
from main.util.work_dates import after_some_work_days, get_today, set_today, month_first_end_date, workday_num_between, \
    str_date, enter_next_work_date, after_some_days, enter_next_date
from create_fake_data import test_app, AuthUser
from create_fake_data.data import company1, engineers


def create_admin():
    admin = Om(username='admin', role='om')
    admin.set_password('11111111')
    admin.fee_rate = 0.1
    admin.tax_rate = 0.1
    admin.save()


def create_company_data():
    admin = AuthUser('admin')

    admin.post('/api/v1/company', json=company1['company_form'])

    company_model = Company.query.filter_by(name=company1['company_form']['name']).first()

    for cg in company1['purchases']:
        cg.update({'company_id': company_model.id})
        admin.post('/api/v1/purchase', json=cg)

    for ipm in company1['pms']:
        ipm.update({'company_id': company_model.id})
        admin.post('/api/v1/pm', json=ipm)

    for position in company1['positions']:
        position.update({'company_id': company_model.id})
        admin.post('/api/v1/position', json=position)
    for position_level in company1['position_levels']:
        position_level.update({'company_id': company_model.id})
        admin.post('/api/v1/position_level', json=position_level)

    # 创建报价单
    position_models = Position.query.filter().all()
    position_level_models = PositionLevel.query.filter().all()
    for p in position_models:
        for pl in position_level_models:
            admin.post('/api/v1/offer_sheet', json={'company_id': company_model.id, 'position_id': p.id, \
                                                    'position_level_id': pl.id, 'money': 10000})

    # 创建项目
    ps = company1['projects']
    for p in ps:
        p['company_id'] = company_model.id
        admin.post('/api/v1/project', json=p)

    os = company1['offers']
    all_project = Project.query.all()
    all_positions = Position.query.all()
    all_position_level = PositionLevel.query.all()
    all_pms = Pm.query.all()

    index = 0
    for one_project in all_project[:2]:
        for one_position in all_positions[:2]:
            one_position_level = all_position_level[index % len(all_position_level)]
            o_data = {}
            o_data['name'] = os['name'](one_position.name + one_position_level.name)
            o_data['amount'] = os['amount'](index)
            o_data['position_id'] = one_position.id
            o_data['company_id'] = company_model.id
            o_data['project_id'] = one_project.id
            o_data['pm_id'] = all_pms[index % len(all_pms)].id
            o_data['position_id'] = one_position.id
            o_data['position_level_id'] = one_position_level.id
            o_data['description'] = '一个需求'
            admin.post('/api/v1/offer', json=o_data)
        index += 1


def create_engineers():
    for i in range(99):
        e = {}
        for key in engineers:
            e[key] = engineers[key](i)
        admin = AuthUser('admin')
        admin.post('/api/v1/engineer', json=e)
        admin.put("/api/v1/engineer?schema=EngineerPutSchema&pre_username={}".format(e['pre_username']),
                  json={"welfare_rate": e["welfare_rate"]})


def push_engineer():
    es = Engineer.query.all()
    os = Offer.query.all()
    es_num = len(es)
    admin = AuthUser('admin')
    for i in range(es_num - 10):
        one_engineer = es[i]
        one_offer = os[i % len(os)]
        interview_data = dict(offer_id=one_offer.id)
        interview_data['engineer_id'] = one_engineer.id
        admin.post('/api/v1/interview', json=interview_data)


def check_interviews():
    all_pms = Pm.query.all()
    for one_pm in all_pms:
        auth_pm = AuthUser(one_pm.pre_username)
        appoint_time = auth_pm.get('/api/v1/pm?schema=PmAppointTimeSchema')
        appoint_time = json.loads(appoint_time)
        for d in appoint_time['default_can_appoint_time']:
            d['am'] = True
        auth_pm.put('/api/v1/pm?schema=PmCanAppointTimePutSchema',
                    json={"set_info": appoint_time['default_can_appoint_time'], "set_default": True})
        interviews = Interview.query.filter_by(pm_id=one_pm.id).all()
        for i, one_interview in enumerate(interviews[::-1]):
            if i < 2:
                status = InterviewStatus.cv_new
            elif i < 4:
                status = InterviewStatus.cv_reject
            elif i < 5:
                status = InterviewStatus.cv_read
            else:
                status = InterviewStatus.cv_pass

            if status == InterviewStatus.cv_pass:
                auth_pm.put('/api/v1/interview?id={}&schema=InterviewStatusPutSchema'.format(one_interview.id),
                            json={'status': status, "pm_free_time": appoint_time['default_can_appoint_time']})
            else:
                auth_pm.put('/api/v1/interview?id={}&schema=InterviewStatusPutSchema'.format(one_interview.id),
                            json={'status': status})


def set_interview_appointment():
    all_pms = Pm.query.all()
    auth_admin = AuthUser('admin')
    for one_pm in all_pms:
        interviews = auth_admin.get('/api/v1/interviews?status={}&pm_id={}'.format(InterviewStatus.cv_pass, one_pm.id))
        interviews = json.loads(interviews)['data']
        for i, one_interview in enumerate(interviews[::-1]):
            if i < 6:
                continue
            if i < 7:
                status = InterviewStatus.interview_reject_by_engineer
                auth_admin.put('/api/v1/interview?id={}&schema=InterviewStatusPutSchema'.format(one_interview['id']),
                               json={"status": status})
            else:
                status = InterviewStatus.interview_new
                pm_free_time = one_interview['pm_free_time']
                chooices = []
                for pft in pm_free_time:
                    if (pft['am'] or pft['pmA'] or pft['pmB']) and (not pft['disable']):
                        chooices.append(pft)
                appoint_time = chooices[i % len(chooices)]
                appoint_time.update(am=False, pmA=True, pmB=False)
                auth_admin.put('/api/v1/interview?id={}&schema=InterviewStatusPutSchema'.format(one_interview['id']),
                               json={'status': status, 'appoint_time': appoint_time})


def interview_result():
    all_pms = Pm.query.all()
    for one_pm in all_pms:
        auth_pm = AuthUser(one_pm.pre_username)
        interviews = auth_pm.get('/api/v1/interviews?status={}'.format(InterviewStatus.interview_new))
        interviews = json.loads(interviews)['data']
        for i, one_interview in enumerate(interviews[::-1]):
            if i < 4:
                continue
            if i < 5:
                status = InterviewStatus.interview_undetermined
            elif i < 6:
                status = InterviewStatus.interview_reject
            elif i < 7:
                status = InterviewStatus.interview_absent
            else:
                status = InterviewStatus.interview_pass
            auth_pm.put('/api/v1/interview?id={}&schema=InterviewStatusPutSchema'.format(one_interview['id']),
                        json={"status": status})


def entry():
    auth_admin = AuthUser('admin')
    interviews = auth_admin.get('/api/v1/interviews?status={}'.format(InterviewStatus.interview_pass))
    interviews = json.loads(interviews)['data']
    for i, one_interview in enumerate(interviews[::-1]):
        if i < 4:
            continue
        entry_date = after_some_work_days(1)
        result = auth_admin.put('/api/v1/interview?id={}&schema=InterviewEntryPutSchema'.format(one_interview['id']),
                       json={'date': entry_date.strftime('%Y-%m-%d')})

    all_pms = Pm.query.all()
    for one_pm in all_pms:
        auth_pm = AuthUser(one_pm.pre_username)
        entries = auth_pm.get('/api/v1/entries?status={}'.format(AuditStatus.submit))
        entries = json.loads(entries)['data']
        for i, one_entry in enumerate(entries[::-1]):
            if i < 1:
                continue
            if i < 2:
                status = AuditStatus.reject
                reason = '看不对眼'
                auth_pm.put('/api/v1/entry?id={}&schema=EntryCheckSchema'.format(one_entry['id']),
                            json={'status': status, 'comment': reason})
            else:
                try:
                    auth_pm.put('/api/v1/entry?id={}&schema=EntryCheckSchema'.format(one_entry['id']),
                                json={'status': AuditStatus.checked})
                except Exception as e:
                    print(e)


####################
def first_month_audit():
    today = get_today()
    _, month_end_date = month_first_end_date(today.year, today.month)
    es = Engineer.query.filter_by(status=EngineerStatus.on_duty).all()
    pms = Pm.query.all()
    # 请假
    for i, e in enumerate(es):
        e_auth = AuthUser(e.pre_username)
        e_auth.post('/api/v1/leave',
                    json={'leave_type': LeaveType.personal,
                          'start_date': after_some_work_days(i % 5).strftime('%Y-%m-%d'),
                          'end_date': after_some_work_days(i % 5 + 2).strftime('%Y-%m-%d'),
                          'days': 3 - 0.5 * (i % 2),
                          'reason': '爱批不批',
                          })
    for _pm in pms:
        pm_auth = AuthUser(_pm.pre_username)
        # audits = pm_auth.get('')
    # 加班
    # 调休


def first_month_daily_log():
    today = get_today()
    _, month_end_date = month_first_end_date(today.year, today.month)
    es = Engineer.query.filter_by(status=EngineerStatus.on_duty).all()
    while today <= month_end_date:
        for e in es:
            if e.career[-1].start < today:
                continue
            auth_e = AuthUser(e.pre_username)
            auth_e.post('/api/v1/daily_log', json={''})

    pms = Pm.query.all()
    for _pm in pms:
        auth_pm = AuthUser(_pm.pre_username)
        leave_audits = auth_pm.get('/api/v1/leaves?audit_type=leave&status=submit')
        for index, la in enumerate(leave_audits[::-1]):
            if index < 2:
                auth_pm.put('/api/v1/leave?id={}&schema=LeaveCheckPutSchema'.format(la.id))


def _put_daily_log_for(auth_e, date, content="日常工作", duration=1):
    now_daily_log = auth_e.get('/api/v1/daily_log?date={}'.format(date))
    now_daily_log = json.loads(now_daily_log)
    auth_e.put('/api/v1/daily_log?id={}&schema=DailyLogPutSchema'.format(now_daily_log['id']),
               json={"content": content, "duration": duration})


def _get_latest_daily_logs(auth_e):
    now_daily_logs = auth_e.get('/api/v1/daily_logs?latest=True&sort_id=-1')
    return json.loads(now_daily_logs)


def ex_work_content(ex, start_date):
    pm = Pm.query.get(ex.pm_id)
    auth_pm = AuthUser(pm.pre_username)
    # dls = DailyLog.query.filter_by(engineer_id=ex.id).all()
    # for dl in dls:
    #     dl.delete()
    # 第一天的正常日志
    set_today(start_date)
    auth_e = AuthUser(ex.pre_username)
    _get_latest_daily_logs(auth_e)
    _put_daily_log_for(auth_e, get_today())

    # 提个明天的请假：
    next_work_date = after_some_work_days(1)
    next_work_date = str_date(next_work_date)
    response = auth_e.post('/api/v1/leave',
                           json={"leave_type": "person",
                                 "start_date": next_work_date,
                                 "end_date": next_work_date,
                                 "reason": "约会",
                                 "days": 1})
    response = json.loads(response)
    auth_pm.put('/api/v1/leave?id={}&schema=LeaveCheckPutSchema'.format(response['id']),
                json={"status": AuditStatus.checked})

    # 请假了，虚度过去这一天
    enter_next_work_date(1)

    # 正常日志
    enter_next_work_date()
    _get_latest_daily_logs(auth_e)
    _put_daily_log_for(auth_e, get_today())

    # 4天忘了写，打开日志，补了4天
    enter_next_work_date(after=4)
    latest_daily_logs = _get_latest_daily_logs(auth_e)
    un_put_latest_daily_logs = list(
        filter(lambda x: x['duration'] == 0 and not x['content'] and x['origin_type'] == 'normal_work',
               latest_daily_logs['data']))
    assert len(un_put_latest_daily_logs) == 4
    for daily in un_put_latest_daily_logs:
        _put_daily_log_for(auth_e, daily['date'])

    # 正常工作到周末之前
    while is_work_day(after_some_days(1)):
        enter_next_date(1)
        _get_latest_daily_logs(auth_e)
        _put_daily_log_for(auth_e, get_today())

    # 明天应该是周末了，申请1。5天的加班
    next_day = after_some_days(1)
    response = auth_e.post('/api/v1/extra_work',
                           json={"start_date": str_date(next_day),
                                 "end_date": str_date(after_some_days(1, next_day)),
                                 "days": 1.5,
                                 "reason": "赶进度"})
    audit_id = json.loads(response)['id']
    auth_pm.put('/api/v1/extra_work?schema=ExtraWorkCheckPutSchema&id={}'.format(audit_id),
                json={"status": AuditStatus.checked})

    # 加班
    enter_next_date(1)
    _put_daily_log_for(auth_e, get_today(), content='加班1', duration=1)
    enter_next_date(1)
    _put_daily_log_for(auth_e, get_today(), content="加班2", duration=0.5)

    # 加班这么累，调个休
    next_day = after_some_work_days(1)
    can_shift_duration = auth_e.get('/api/v1/can_shift_duration')
    can_shift_duration = int(can_shift_duration)
    auth_e.post('/api/v1/shift', json={'start': next_day, 'end_date': next_day})


def update_all_un_put_daily_logs(ex):
    auth_e = AuthUser(ex.pre_username)
    latest_daily_logs = _get_latest_daily_logs(auth_e)
    un_put_latest_daily_logs = list(
        filter(lambda x: x['duration'] == 0 and not x['content'] and x['origin_type'] == 'normal_work',
               latest_daily_logs['data']))
    for dl in un_put_latest_daily_logs:
        _put_daily_log_for(auth_e, dl['date'])


def submit_work_report(ex, year_month):
    auth_e = AuthUser(ex.pre_username)
    auth_e.post('/api/v1/work_report', json={"year_month": year_month})


def check_work_report(pmx):
    auth_pm = AuthUser(pmx.pre_username)
    un_checked_work_reports = auth_pm.get('/api/v1/audits?status=submit&sort_id=-1&audit_type=work_report')
    un_checked_work_reports = json.loads(un_checked_work_reports)['data']
    for ucwr in un_checked_work_reports:
        auth_pm.put('/api/v1/work_report?id={}&schema=WorkReportCheckPutSchema'.format(ucwr['id']),
                    json={"status": "checked",
                          "attitude_score": random.randint(3, 5),
                          "ability_score": random.randint(3, 5)})


def generate_month_bill(cg, year_month):
    auth_cg = AuthUser(cg.pre_username)
    auth_admin = AuthUser('admin')
    auth_admin.post('/api/v1/monthly_bill', json={'year_month': year_month, 'company_id': cg.company_id})


def before_entry():
    set_today("20190301")
    create_admin()
    create_company_data()
    create_engineers()
    push_engineer()
    check_interviews()
    set_interview_appointment()
    interview_result()
    entry()


def after_entry():
    # first_month_audit()
    # first_month_daily_log()
    es = Engineer.query.filter_by(status=EngineerStatus.on_duty).all()
    pms = Pm.query.all()
    cg = Purchase.query.filter_by(company_id=1).first()
    today = get_today()
    while not today.month == dt.date.today().month:
        ms, me = month_first_end_date(today.year, today.month)
        set_today(me)
        for ex in es:
            update_all_un_put_daily_logs(ex)
        enter_next_work_date(1)
        for ex in es:
            submit_work_report(ex, ms.year * 100 + ms.month)
        for pmx in pms:
            check_work_report(pmx)
        generate_month_bill(cg, year_month=ms.year * 100 + ms.month)
        today = get_today()


def run():
    before_entry()
    after_entry()


if __name__ == '__main__':
    run()
