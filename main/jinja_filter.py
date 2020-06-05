#!venv/bin python
# -*- coding:utf-8 -*-
from flask import request, url_for
from datetime import datetime, timedelta
from babel.numbers import format_currency
from money import Money
from random import randint

DT_FORMAT_CN = '%Y年%m月%d日 %H:%M'

WEB_FORMAT = '%Y/%m/%d %H:%M:%S'

NOTICE_FORMAT = '%m-%d'


def cent_to_yuan(cent):
    if cent is None:
        return None
    m = Money(cent / 100, currency='CNY')
    return format_currency(m.amount, m.currency, locale='zh_CN')


def percentage(num):
    return "{0}%".format(num)


def quantity_3_f(quantity):
    if quantity is None:
        return None
    return "%0.3f" % quantity


def yuan(price):
    return u"%s元" % (str(price),)


def day(days):
    return u"%s天" % (str(days),)


def cn_datetime(dt_str):
    dt = datetime.strptime(dt_str[:19], '%Y-%m-%d %H:%M:%S')
    return datetime.strftime(dt, DT_FORMAT_CN)


def notice_datetime(dt_str):
    dt = datetime.strptime(dt_str[:19], '%Y-%m-%d %H:%M:%S')
    return datetime.strftime(dt, NOTICE_FORMAT)


def web_datetime(dt_str):
    dt = datetime.strptime(dt_str[:19], '%Y-%m-%d %H:%M:%S')
    return datetime.strftime(dt, WEB_FORMAT)


def short_time(dt_str):
    dt = datetime.strptime(dt_str[5:19], '%m-%d %H:%M:%S')
    return datetime.strftime(dt, '%m-%d %H:%M:%S')


def process_params(kwargs):
    args = request.args.to_dict()
    args = dict(kwargs, **args)
    args.pop('page', None)
    args.pop('per_page', None)
    return args


def hide_phone(phone):
    if len(phone) == 11:
        return phone[:3] + '******' + phone[9:]
    else:
        return phone


def show_avatar(current_user):
    return current_user.avatar_url if current_user.avatar_url else '/static/img/avatar_{0}.png'.format(randint(1, 9))


def none_to_zero(data):
    return data if data else 0


def listing_time_shot_status(time):
    return time[5:19]


def none_to_null(data):
    if data is None:
        return ''
    else:
        return data


def message_date(date_time):
    return date_time[0:10].replace('-', '/')


def zero_if_none(value):
    if value is None or value is "" or value == "None":
        return 0
    return value


def init_app(app):
    app.jinja_env.filters['cent_to_yuan'] = cent_to_yuan
    app.jinja_env.filters['yuan'] = yuan
    app.jinja_env.filters['day'] = day
    app.jinja_env.filters['cn_datetime'] = cn_datetime
    app.jinja_env.filters['quantity_3_f'] = quantity_3_f
    app.jinja_env.filters['percentage'] = percentage
    app.jinja_env.filters['web_datetime'] = web_datetime
    app.jinja_env.filters['short_time'] = short_time
    app.jinja_env.filters['process_params'] = process_params
    app.jinja_env.filters['hide_phone'] = hide_phone
    app.jinja_env.filters['show_avatar'] = show_avatar
    app.jinja_env.filters['none_to_zero'] = none_to_zero
    app.jinja_env.filters['notice_datetime'] = notice_datetime
    app.jinja_env.filters['listing_time_shot_status'] = listing_time_shot_status
    app.jinja_env.filters['none_to_null'] = none_to_null
    app.jinja_env.filters['message_date'] = message_date
    app.jinja_env.filters['zero_if_none'] = zero_if_none
