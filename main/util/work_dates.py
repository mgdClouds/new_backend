import datetime as dt
import calendar
import os
from config import load_config
from ..exception import NewComException

workdays_2018 = [
    '20180102',
    '20180103',
    '20180104',
    '20180107',
    '20180108',
    '20180109',
    '20180110',
    '20180111',
    '20180114',
    '20180115',
    '20180116',
    '20180117',
    '20180118',
    '20180121',
    '20180122',
    '20180123',
    '20180124',
    '20180125',
    '20180128',
    '20180129',
    '20180130',
    '20180131',
    '20180201',
    '20180211',
    '20180212',
    '20180213',
    '20180214',
    '20180215',
    '20180218',
    '20180219',
    '20180220',
    '20180221',
    '20180222',
    '20180225',
    '20180226',
    '20180227',
    '20180228',
    '20180301',
    '20180304',
    '20180305',
    '20180306',
    '20180307',
    '20180308',
    '20180311',
    '20180312',
    '20180313',
    '20180314',
    '20180315',
    '20180318',
    '20180319',
    '20180320',
    '20180321',
    '20180322',
    '20180325',
    '20180326',
    '20180327',
    '20180328',
    '20180329',
    '20180401',
    '20180402',
    '20180403',
    '20180404',
    '20180408',
    '20180409',
    '20180410',
    '20180411',
    '20180412',
    '20180415',
    '20180416',
    '20180417',
    '20180418',
    '20180419',
    '20180422',
    '20180423',
    '20180424',
    '20180425',
    '20180426',
    '20180429',
    '20180430',
    '20180502',
    '20180503',
    '20180506',
    '20180507',
    '20180508',
    '20180509',
    '20180510',
    '20180513',
    '20180514',
    '20180515',
    '20180516',
    '20180517',
    '20180520',
    '20180521',
    '20180522',
    '20180523',
    '20180524',
    '20180527',
    '20180528',
    '20180529',
    '20180530',
    '20180531',
    '20180603',
    '20180604',
    '20180605',
    '20180606',
    '20180610',
    '20180611',
    '20180612',
    '20180613',
    '20180614',
    '20180617',
    '20180618',
    '20180619',
    '20180620',
    '20180621',
    '20180624',
    '20180625',
    '20180626',
    '20180627',
    '20180628',
    '20180701',
    '20180702',
    '20180703',
    '20180704',
    '20180705',
    '20180708',
    '20180709',
    '20180710',
    '20180711',
    '20180712',
    '20180715',
    '20180716',
    '20180717',
    '20180718',
    '20180719',
    '20180722',
    '20180723',
    '20180724',
    '20180725',
    '20180726',
    '20180729',
    '20180730',
    '20180731',
    '20180801',
    '20180802',
    '20180805',
    '20180806',
    '20180807',
    '20180808',
    '20180809',
    '20180812',
    '20180813',
    '20180814',
    '20180815',
    '20180816',
    '20180819',
    '20180820',
    '20180821',
    '20180822',
    '20180823',
    '20180826',
    '20180827',
    '20180828',
    '20180829',
    '20180830',
    '20180902',
    '20180903',
    '20180904',
    '20180905',
    '20180906',
    '20180909',
    '20180910',
    '20180911',
    '20180912',
    '20180916',
    '20180917',
    '20180918',
    '20180919',
    '20180920',
    '20180923',
    '20180924',
    '20180925',
    '20180926',
    '20180927',
    '20180930',
    '20181008',
    '20181009',
    '20181010',
    '20181011',
    '20181014',
    '20181015',
    '20181016',
    '20181017',
    '20181018',
    '20181021',
    '20181022',
    '20181023',
    '20181024',
    '20181025',
    '20181028',
    '20181029',
    '20181030',
    '20181031',
    '20181101',
    '20181104',
    '20181105',
    '20181106',
    '20181107',
    '20181108',
    '20181111',
    '20181112',
    '20181113',
    '20181114',
    '20181115',
    '20181118',
    '20181119',
    '20181120',
    '20181121',
    '20181122',
    '20181125',
    '20181126',
    '20181127',
    '20181128',
    '20181129',
    '20181202',
    '20181203',
    '20181204',
    '20181205',
    '20181206',
    '20181209',
    '20181210',
    '20181211',
    '20181212',
    '20181213',
    '20181216',
    '20181217',
    '20181218',
    '20181219',
    '20181220',
    '20181223',
    '20181224',
    '20181225',
    '20181226',
    '20181227',
    '20181230',
    '20181231'
]

workdays_2019 = [
    '20190102',
    '20190103',
    '20190104',
    '20190107',
    '20190108',
    '20190109',
    '20190110',
    '20190111',
    '20190114',
    '20190115',
    '20190116',
    '20190117',
    '20190118',
    '20190121',
    '20190122',
    '20190123',
    '20190124',
    '20190125',
    '20190128',
    '20190129',
    '20190130',
    '20190131',
    '20190201',
    '20190211',
    '20190212',
    '20190213',
    '20190214',
    '20190215',
    '20190218',
    '20190219',
    '20190220',
    '20190221',
    '20190222',
    '20190225',
    '20190226',
    '20190227',
    '20190228',
    '20190301',
    '20190304',
    '20190305',
    '20190306',
    '20190307',
    '20190308',
    '20190311',
    '20190312',
    '20190313',
    '20190314',
    '20190315',
    '20190318',
    '20190319',
    '20190320',
    '20190321',
    '20190322',
    '20190325',
    '20190326',
    '20190327',
    '20190328',
    '20190329',
    '20190401',
    '20190402',
    '20190403',
    '20190404',
    '20190408',
    '20190409',
    '20190410',
    '20190411',
    '20190412',
    '20190415',
    '20190416',
    '20190417',
    '20190418',
    '20190419',
    '20190422',
    '20190423',
    '20190424',
    '20190425',
    '20190426',
    '20190428',
    '20190429',
    '20190430',
    '20190505',
    '20190506',
    '20190507',
    '20190508',
    '20190509',
    '20190510',
    '20190513',
    '20190514',
    '20190515',
    '20190516',
    '20190517',
    '20190520',
    '20190521',
    '20190522',
    '20190523',
    '20190524',
    '20190527',
    '20190528',
    '20190529',
    '20190530',
    '20190531',
    '20190603',
    '20190604',
    '20190605',
    '20190606',
    '20190610',
    '20190611',
    '20190612',
    '20190613',
    '20190614',
    '20190617',
    '20190618',
    '20190619',
    '20190620',
    '20190621',
    '20190624',
    '20190625',
    '20190626',
    '20190627',
    '20190628',
    '20190701',
    '20190702',
    '20190703',
    '20190704',
    '20190705',
    '20190708',
    '20190709',
    '20190710',
    '20190711',
    '20190712',
    '20190715',
    '20190716',
    '20190717',
    '20190718',
    '20190719',
    '20190722',
    '20190723',
    '20190724',
    '20190725',
    '20190726',
    '20190729',
    '20190730',
    '20190731',
    '20190801',
    '20190802',
    '20190805',
    '20190806',
    '20190807',
    '20190808',
    '20190809',
    '20190812',
    '20190813',
    '20190814',
    '20190815',
    '20190816',
    '20190819',
    '20190820',
    '20190821',
    '20190822',
    '20190823',
    '20190826',
    '20190827',
    '20190828',
    '20190829',
    '20190830',
    '20190902',
    '20190903',
    '20190904',
    '20190905',
    '20190906',
    '20190909',
    '20190910',
    '20190911',
    '20190912',
    '20190916',
    '20190917',
    '20190918',
    '20190919',
    '20190920',
    '20190923',
    '20190924',
    '20190925',
    '20190926',
    '20190927',
    '20190929',
    '20190930',
    '20191008',
    '20191009',
    '20191010',
    '20191011',
    '20191012',
    '20191014',
    '20191015',
    '20191016',
    '20191017',
    '20191018',
    '20191021',
    '20191022',
    '20191023',
    '20191024',
    '20191025',
    '20191028',
    '20191029',
    '20191030',
    '20191031',
    '20191101',
    '20191104',
    '20191105',
    '20191106',
    '20191107',
    '20191108',
    '20191111',
    '20191112',
    '20191113',
    '20191114',
    '20191115',
    '20191118',
    '20191119',
    '20191120',
    '20191121',
    '20191122',
    '20191125',
    '20191126',
    '20191127',
    '20191128',
    '20191129',
    '20191202',
    '20191203',
    '20191204',
    '20191205',
    '20191206',
    '20191209',
    '20191210',
    '20191211',
    '20191212',
    '20191213',
    '20191216',
    '20191217',
    '20191218',
    '20191219',
    '20191220',
    '20191223',
    '20191224',
    '20191225',
    '20191226',
    '20191227',
    '20191230',
    '20191231'
]

holidays_2019 = [
    '20190101',
    '20190204',
    '20190205',
    '20190206',
    '20190405',
    '20190501',
    '20190607',
    '20190913',
    '20191001',
    '20191002',
    '20191003'
]

workdays_2020 = [
    '20200102',
    '20200103',
    '20200106',
    '20200107',
    '20200108',
    '20200109',
    '20200110',
    '20200113',
    '20200114',
    '20200115',
    '20200116',
    '20200117',
    '20200119',
    '20200120',
    '20200121',
    '20200122',
    '20200123',
    '20200131',
    '20200201',
    '20200203',
    '20200204',
    '20200205',
    '20200206',
    '20200207',
    '20200210',
    '20200211',
    '20200212',
    '20200213',
    '20200214',
    '20200217',
    '20200218',
    '20200219',
    '20200220',
    '20200221',
    '20200224',
    '20200225',
    '20200226',
    '20200227',
    '20200228',
    '20200302',
    '20200303',
    '20200304',
    '20200305',
    '20200306',
    '20200309',
    '20200310',
    '20200311',
    '20200312',
    '20200313',
    '20200316',
    '20200317',
    '20200318',
    '20200319',
    '20200320',
    '20200323',
    '20200324',
    '20200325',
    '20200326',
    '20200327',
    '20200330',
    '20200331',
    '20200401',
    '20200402',
    '20200403',
    '20200407',
    '20200408',
    '20200409',
    '20200410',
    '20200413',
    '20200414',
    '20200415',
    '20200416',
    '20200417',
    '20200420',
    '20200421',
    '20200422',
    '20200423',
    '20200424',
    '20200426',
    '20200427',
    '20200428',
    '20200429',
    '20200430',
    '20200506',
    '20200507',
    '20200508',
    '20200509',
    '20200511',
    '20200512',
    '20200513',
    '20200514',
    '20200515',
    '20200518',
    '20200519',
    '20200520',
    '20200521',
    '20200522',
    '20200525',
    '20200526',
    '20200527',
    '20200528',
    '20200529',
    '20200601',
    '20200602',
    '20200603',
    '20200604',
    '20200605',
    '20200608',
    '20200609',
    '20200610',
    '20200611',
    '20200612',
    '20200615',
    '20200616',
    '20200617',
    '20200618',
    '20200619',
    '20200622',
    '20200623',
    '20200624',
    '20200628',
    '20200629',
    '20200630',
    '20200701',
    '20200702',
    '20200703',
    '20200706',
    '20200707',
    '20200708',
    '20200709',
    '20200710',
    '20200713',
    '20200714',
    '20200715',
    '20200716',
    '20200717',
    '20200720',
    '20200721',
    '20200722',
    '20200723',
    '20200724',
    '20200727',
    '20200728',
    '20200729',
    '20200730',
    '20200731',
    '20200803',
    '20200804',
    '20200805',
    '20200806',
    '20200807',
    '20200810',
    '20200811',
    '20200812',
    '20200813',
    '20200814',
    '20200817',
    '20200818',
    '20200819',
    '20200820',
    '20200821',
    '20200824',
    '20200825',
    '20200826',
    '20200827',
    '20200828',
    '20200831',
    '20200901',
    '20200902',
    '20200903',
    '20200904',
    '20200907',
    '20200908',
    '20200909',
    '20200910',
    '20200911',
    '20200914',
    '20200915',
    '20200916',
    '20200917',
    '20200918',
    '20200921',
    '20200922',
    '20200923',
    '20200924',
    '20200925',
    '20200928',
    '20200929',
    '20200930',
    '20201009',
    '20201010',
    '20201012',
    '20201013',
    '20201014',
    '20201015',
    '20201016',
    '20201019',
    '20201020',
    '20201021',
    '20201022',
    '20201023',
    '20201026',
    '20201027',
    '20201028',
    '20201029',
    '20201030',
    '20201102',
    '20201103',
    '20201104',
    '20201105',
    '20201106',
    '20201109',
    '20201110',
    '20201111',
    '20201112',
    '20201113',
    '20201116',
    '20201117',
    '20201118',
    '20201119',
    '20201120',
    '20201123',
    '20201124',
    '20201125',
    '20201126',
    '20201127',
    '20201130',
    '20201201',
    '20201202',
    '20201203',
    '20201204',
    '20201207',
    '20201208',
    '20201209',
    '20201210',
    '20201211',
    '20201214',
    '20201215',
    '20201216',
    '20201217',
    '20201218',
    '20201221',
    '20201222',
    '20201223',
    '20201224',
    '20201225',
    '20201228',
    '20201229',
    '20201230',
    '20201231'
]

holidays_2020 = [
    '20200101',
    '20200124',
    '20200125',
    '20200126',
    '20200404',
    '20200501',
    '20200625',
    '20201001',
    '20201002',
    '20201003'
]

weekdays_2020 = [
    '20200104',
    '20200105',
    '20200111',
    '20200112',
    '20200118',
    '20200127',
    '20200128',
    '20200129',
    '20200130',
    '20200202',
    '20200208',
    '20200209',
    '20200215',
    '20200216',
    '20200222',
    '20200223',
    '20200229',
    '20200301',
    '20200307',
    '20200308',
    '20200314',
    '20200315',
    '20200321',
    '20200322',
    '20200328',
    '20200329',
    '20200405',
    '20200406',
    '20200411',
    '20200412',
    '20200418',
    '20200419',
    '20200425',
    '20200502',
    '20200503',
    '20200504',
    '20200505',
    '20200510',
    '20200516',
    '20200517',
    '20200523',
    '20200524',
    '20200530',
    '20200531',
    '20200606',
    '20200607',
    '20200613',
    '20200614',
    '20200620',
    '20200621',
    '20200626',
    '20200627',
    '20200704',
    '20200705',
    '20200711',
    '20200712',
    '20200718',
    '20200719',
    '20200725',
    '20200726',
    '20200801',
    '20200802',
    '20200808',
    '20200809',
    '20200815',
    '20200816',
    '20200822',
    '20200823',
    '20200829',
    '20200830',
    '20200905',
    '20200906',
    '20200912',
    '20200913',
    '20200919',
    '20200920',
    '20200926',
    '20200927',
    '20201004',
    '20201005',
    '20201006',
    '20201007',
    '20201008',
    '20201011',
    '20201017',
    '20201018',
    '20201024',
    '20201025',
    '20201031',
    '20201101',
    '20201107',
    '20201108',
    '20201114',
    '20201115',
    '20201121',
    '20201122',
    '20201128',
    '20201129',
    '20201205',
    '20201206',
    '20201212',
    '20201213',
    '20201219',
    '20201220',
    '20201226',
    '20201227'
]

Config = load_config()


def create_year_all_days(year):
    year_first_day = dt.datetime(year=year, month=1, day=1).date()
    cursor = year_first_day
    one_day = dt.timedelta(days=1)
    result = []
    while True:
        if cursor.year == year:
            result.append(cursor)
            cursor += one_day
            continue
        break
    return result


def create_year_month_all_days(year_month):
    month = year_month % 100
    year = int((year_month - month) / 100)
    year_month_first_day = dt.datetime(year=year, month=month, day=1).date()
    cursor = year_month_first_day
    one_day = dt.timedelta(days=1)
    result = []
    while True:
        if cursor.month == month:
            result.append(cursor)
            cursor += one_day
            continue
        break
    return result


days_2018 = [day.strftime('%Y%m%d') for day in create_year_all_days(2018)]
days_2019 = [day.strftime('%Y%m%d') for day in create_year_all_days(2019)]
days_2020 = [day.strftime('%Y%m%d') for day in create_year_all_days(2020)]
rest_days_2018 = sorted(list(set(days_2018) - set(workdays_2018)))
rest_days_2019 = sorted(list(set(days_2019) - set(workdays_2019)))
rest_days_2020 = sorted(list(set(days_2020) - set(workdays_2020)))


class WorkDay(object):
    work_days = []

    @classmethod
    def is_work_day(cls, date):
        if not cls.work_days:
            cls.work_days.extend(workdays_2018)
            cls.work_days.extend(workdays_2019)
            cls.work_days.extend(workdays_2020)
        if isinstance(date, dt.date) or isinstance(date, dt.datetime):
            date = date.strftime('%Y%m%d')
        if isinstance(date, int):
            date = str(date)
        return date in cls.work_days


def is_work_day(date):
    return WorkDay.is_work_day(date)


class Holiday(object):
    holiday_days = []

    @classmethod
    def is_holiday(cls, date):
        if not cls.holiday_days:
            cls.holiday_days.extend(holidays_2019)
            cls.holiday_days.extend(holidays_2020)
        if isinstance(date, dt.date) or isinstance(date, dt.datetime):
            date = date.strftime('%Y%m%d')
        if isinstance(date, int):
            date = str(date)
        return date in cls.holiday_days


def is_holiday(date):
    return Holiday.is_holiday(date)


def get_today():
    if Config.DEBUG:
        with open(os.path.join(Config.ROOT_DIR, 'pretend_today_is'), 'r') as f:
            data = f.read().strip()
            year = int(data[:4])
            month = int(data[4:6])
            day = int(data[6:8])
            fake_today = dt.date(year=year, month=month, day=day)
            return fake_today
    else:
        return dt.date.today()


def get_datetime_today():
    if Config.DEBUG:
        with open(os.path.join(Config.ROOT_DIR, 'pretend_today_is'), 'r') as f:
            data = f.read().strip()
            year = int(data[:4])
            month = int(data[4:6])
            day = int(data[6:8])
            fake_today = dt.datetime(year=year, month=month, day=day, hour=0, minute=0)
            # print(type(fake_today))
            return fake_today
    else:
        return dt.datetime.today()


def set_today(today=None):
    if not today:
        today = '20180808'
    if isinstance(today, dt.date):
        today = today.strftime("%Y%m%d")
    with open(os.path.join(Config.ROOT_DIR, 'pretend_today_is'), 'w') as f:
        f.write(today)


def enter_next_work_date(after=1):
    next_work_day = after_some_work_days(after, get_today())
    set_today(next_work_day)


def enter_next_date(after=1):
    next_day = after_some_days(after)
    set_today(next_day)


def month_first_end_date(year, month):
    year = int(year)
    month = int(month)
    days_of_month = calendar.monthrange(year, month)[1]
    return dt.date(year=year, month=month, day=1), dt.date(year=year, month=month, day=days_of_month)


def int_year_month(date=None):
    if not date:
        return None
    return int(date.strftime('%Y%m'))


def str_date(date):
    return date.strftime('%Y-%m-%d')


def get_last_year_month(today=None):
    """

    :param today:
    :return: int 190001
    """
    if not today:
        today = get_today()
    last_moth_last_day = today.replace(day=1) - dt.timedelta(days=1)
    return last_moth_last_day.year * 100 + last_moth_last_day.month


def get_next_year_month(date: dt.date = get_today()):
    """
    :param date:datetime.date
    :return: int 202001
    """
    next_month_days = calendar.monthrange(date.year, date.month)[1]
    next_month_final_day = date + dt.timedelta(days=next_month_days)
    return next_month_final_day.year * 100 + next_month_final_day.month


def week_first_end_date(today=None):
    if not today:
        today = get_today()
    one_day = dt.timedelta(days=1)
    this_week_start = today - one_day * today.weekday()
    this_week_end = today + (6 - today.weekday()) * one_day
    return this_week_start, this_week_end


def this_and_next_weeks(today=None):
    if not today:
        today = get_today()
    this_week_start, this_week_end = week_first_end_date(today)
    one_day = dt.timedelta(days=1)
    next_week_start = this_week_end + one_day
    next_week_start, next_week_end = week_first_end_date(next_week_start)
    days = [this_week_start]
    while days[-1] < next_week_end:
        days.append(days[-1] + one_day)
    return days


def after_some_days(num, today=None):
    if not today:
        today = get_today()
    if num > 365 or num < 0:
        raise Exception('有病！')
    today_str = today.strftime('%Y%m%d')
    year = today_str[:4]
    days_year = eval('days_{}'.format(year))
    index = days_year.index(today_str)
    if index + num + 1 > len(days_year):
        days_next_year = eval('workday_{}'.format(int(year) + 1))
        days_year = days_year + days_next_year
    return dt.datetime.strptime(days_year[index + num], '%Y%m%d').date()


def after_some_work_days(num, today=None):
    # 如果传入的today是非工作日，则把today换成下一个交易日
    if not today:
        today = get_today()
    if num > 365 or num < 0:
        raise Exception('有病！')
    today_str = today.strftime('%Y%m%d')
    year = today_str[:4]
    workdays_year = eval('workdays_{}'.format(year))
    try:
        index = workdays_year.index(today_str)
    except ValueError:
        for d in workdays_year:
            if d < today_str:
                continue
            else:
                if num == 0:
                    return dt.datetime.strptime(d, '%Y%m%d').date()
                today_str = d
                index = workdays_year.index(today_str)
                break
    if index + num + 1 > len(workdays_year):
        workdays_next_year = eval('workdays_{}'.format(int(year) + 1))
        workdays_year = workdays_year + workdays_next_year
    return dt.datetime.strptime(workdays_year[index + num], '%Y%m%d').date()


def month_work_days_until_today(today=None):
    if not today:
        today = get_today()
    month_first, _ = month_first_end_date(today.year, today.month)
    workdays_this_year = eval('workdays_{}'.format(today.year))
    start_index = workdays_this_year.index(month_first.strftime('%Y%m%d'))
    end_index = workdays_this_year.index(today.strftime('%Y%m%d'))
    str_result = workdays_this_year[start_index:end_index + 1]
    return [dt.datetime.strptime(date_str, '%Y%m%d').date() for date_str in str_result]


def month_work_days(year_month):
    year_month_all_days = create_year_month_all_days(year_month)
    result = []
    workdays_this_year = eval('workdays_{}'.format(int(year_month / 100)))
    for d in year_month_all_days:
        if d.strftime("%Y%m%d") in workdays_this_year:
            result.append(d)
    return result


def month_days_until_today(today=None):
    if not today:
        today = get_today()
    month_first, _ = month_first_end_date(today.year, today.month)
    result = []
    one_day = dt.timedelta(days=1)
    while today >= month_first:
        result.append(today)
        today = today - one_day
    result.reverse()
    return result


def workdays_between(start, end):
    # 只可传入工作日做start， end
    start_year = start.year
    end_year = end.year
    start_year_work_days = eval('workdays_{}'.format(start_year))
    end_year_work_days = eval('workdays_{}'.format(end_year))
    if start.strftime('%Y%m%d') not in start_year_work_days or end.strftime('%Y%m%d') not in end_year_work_days:
        raise NewComException('请输入工作日', 500)
    if end_year - start_year == 0:
        workdays = start_year_work_days
    elif end_year - start_year == 1:
        workdays = start_year_work_days + end_year_work_days
    else:
        raise NewComException('超出处理期限', 500)
    end_index, start_index = workdays.index(end.strftime('%Y%m%d')), workdays.index(start.strftime('%Y%m%d'))
    days = workdays[start_index: end_index + 1]
    return days


def rest_days_between(start, end):
    start_year = start.year
    end_year = end.year
    start_year_rest_days = eval('rest_days_{}'.format(start_year))
    end_year_rest_days = eval('rest_days_{}'.format(end_year))
    if start.strftime('%Y%m%d') not in start_year_rest_days or end.strftime('%Y%m%d') not in end_year_rest_days:
        raise NewComException('请输入休息日', 500)
    if end_year - start_year == 0:
        rest_days = start_year_rest_days
    elif end_year - start_year == 1:
        rest_days = start_year_rest_days + end_year_rest_days
    else:
        raise NewComException('超出处理期限', 500)
    end_index, start_index = rest_days.index(end.strftime('%Y%m%d')), rest_days.index(start.strftime('%Y%m%d'))
    days = rest_days[start_index: end_index + 1]
    return days


def days_between(start, end):
    # 只可传入任意时间做start， end
    start_year = start.year
    end_year = end.year
    start_year_days = eval('days_{}'.format(start_year))
    end_year_days = eval('days_{}'.format(end_year))
    if end_year - start_year == 0:
        days = start_year_days
    elif end_year - start_year == 1:
        days = start_year_days + end_year_days
    else:
        raise NewComException('超出处理期限', 500)
    end_index, start_index = days.index(end.strftime('%Y%m%d')), days.index(start.strftime('%Y%m%d'))
    days = days[start_index: end_index + 1]
    return days


def workday_num_between(start, end):
    days = workdays_between(start, end)
    return len(days)


def rest_days_num_between(start, end):
    days = rest_days_between(start, end)
    return len(days)


def days_num_between(start, end):
    days = days_between(start, end)
    return len(days)


def months_later(start, month_count):
    year, start_month, start_day = start.year, start.month, start.day
    total_month = start_month + month_count
    if total_month <= 12:
        end_day = calendar.monthrange(start.year, total_month)[1]
        day = start_day if end_day >= start_day else end_day
        return dt.date(year, total_month, day)
    else:
        num = total_month // 12
        month = total_month % 12
        if month == 0:
            num -= 1
            month = 12
        year += num
        end_day = calendar.monthrange(start.year, month)[1]
        day = start_day if end_day >= start_day else end_day
        return dt.date(year, month, day)


def change_datetime_date(bgtime):
    year = bgtime.year
    month = bgtime.month
    day = bgtime.day
    return dt.date(year=year, month=month, day=day)


def work_time(btime, start=None, end=None):
    year = btime.year
    month = btime.month
    day = btime.day
    if start:
        return dt.datetime(year=year, month=month, day=day, hour=0, minute=0)
    if end:
        return dt.datetime(year=year, month=month, day=day, hour=23, minute=59)


def time_difference(start, end):
    start_year = start.year
    end_year = end.year
    start_year_days = eval('workdays_{}'.format(start_year)) + eval('rest_days_{}'.format(start_year))
    end_year_days = eval('workdays_{}'.format(end_year)) + eval('rest_days_{}'.format(end_year))
    if end_year - start_year == 0:
        days = start_year_days
    elif end_year - start_year == 1:
        days = start_year_days + end_year_days
    else:
        raise NewComException('超出处理期限', 500)
    end_index, start_index = days.index(end.strftime('%Y%m%d')), days.index(start.strftime('%Y%m%d'))
    days = days[start_index: end_index + 1]
    return len(days)


def str_to_date(date: str):
    """
    params: date:"%Y%m%d"格式的字符串 eg:"20191226"
    return: datetime.date类型 eg:datetime.date(2019,12,26)
    """
    date = dt.datetime.strptime(date, "%Y%m%d")
    return dt.date(date.year, date.month, date.day)
