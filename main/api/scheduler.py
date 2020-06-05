import datetime as dt
import os
from traceback import format_exc
import requests

from sqlalchemy import and_
from flask import current_app, jsonify

from ..extention import scheduler, db
from ..model import Engineer, Company
from ..util.work_dates import *
from ..util.try_catch import api_response


def renew_orders():
    one_day = dt.timedelta(days=1)
    today = get_today()

    es = Engineer.query.filter(Engineer.now_career_id > 0).all()
    for e in es:
        if not e.now_career_id:
            continue
        if not e.now_order:
            continue
        if e.now_order.is_ending():
            if not e.now_order.id == e.last_order.id:
                continue
            else:
                if e.now_order.auto_renew == 0:
                    e.auto_renew_order()
                else:
                    e.update(s_need_renew_order=1)
                    e.now_career.update(s_need_renew_order=1)
        else:
            e.update(s_need_renew_order=0)
            e.now_career.update(s_need_renew_order=0)


def daily1():
    requests.get('http://127.0.0.1:5000/api/v1/system/scheduler')


@api_response
def daily1_api():
    lock_path = current_app.config.get('DAILY_LOCK')
    if os.path.exists(lock_path):
        return ''
    else:
        try:
            with open(lock_path, 'w') as f:
                f.write('1')
                renew_orders()
        except Exception as e:
            return str(e)
        finally:
            os.remove(lock_path)

    return 'ok'


def init_api(app, url_prefix):
    app.add_url_rule(os.path.join(url_prefix, 'system/scheduler'),
                     endpoint='system.daily1_api', view_func=daily1_api, methods=['GET'])