from main.util.work_dates import month_work_days
from main.util.personal_tax import cal as cal_personal_tax


def cal_payment(salary_type=None, employ_type=None, money=None, work_duration=None, work_extra_duration=None,
                holiday_extra_duration=None, weekend_extra_duration=None, shift_duration=None,
                work_day_shift_rate=None, weekend_shift_rate=None, holiday_shift_rate=None, charging_num=None,
                out_duty_days=None, service_fee_rate=None, tax_rate=None, year_month=None, shift_type=None,
                use_hr_service=None, hr_fee_rate=None, finance_rate=None, work_station_fee=None, tax_free_rate=None,
                ware_fare=None, break_up_fee=None, service_type=None, extra_station_duration=None):
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
    print(station_salary)
    service_fee = service_fee_rate * labor_salary
    tax = tax_rate * company_pay
    if use_hr_service:
        hr_fee = hr_fee_rate * labor_salary
    else:
        hr_fee = 0
    finance_fee = finance_rate * labor_salary
    engineer_income_with_tax = labor_salary * (
            1 - service_fee_rate - tax_rate - hr_fee_rate - finance_rate)  # 人员可支配费用

    tax_fee = engineer_income_with_tax * tax_free_rate

    if employ_type == 0:
        engineer_get = engineer_income_with_tax * (1 - tax_free_rate)
        engineer_tax = 0
        break_up_fee = 0
    else:
        engineer_tax = cal_personal_tax(engineer_income_with_tax - ware_fare)
        _engineer_get = engineer_income_with_tax - ware_fare - engineer_tax
        engineer_get = _engineer_get * break_up_fee
        break_up_fee = _engineer_get * (1 - break_up_fee)  # 离职补偿费

    return dict(company_pay=company_pay, amerce=amerce, hr_fee=hr_fee, service_fee_rate=service_fee_rate,
                finance_fee=finance_fee, tax=tax, engineer_income_with_tax=engineer_income_with_tax,
                engineer_get=engineer_get, engineer_tax=engineer_tax, break_up_fee=break_up_fee,
                out_duty_days=out_duty_days, tax_rate=tax_rate, extra_salary=extra_salary,
                station_salary=station_salary, hr_fee_rate=hr_fee_rate, finance_rate=finance_rate,
                use_hr_service=use_hr_service, tax_free_rate=tax_free_rate, ware_fare=ware_fare,
                service_fee=service_fee, tax_fee=tax_fee)

if __name__ == '__main__':
    res = cal_payment(salary_type=1, employ_type=0, money=20000, work_duration=38, work_extra_duration=0,
                holiday_extra_duration=0, weekend_extra_duration=8, shift_duration=0,
                work_day_shift_rate=1, weekend_shift_rate=2, holiday_shift_rate=3, charging_num=20,
                out_duty_days=10, service_fee_rate=0.1, tax_rate=0.067, year_month=201909, shift_type=1,
                use_hr_service=1, hr_fee_rate=0.05, finance_rate=0.09, work_station_fee=20, tax_free_rate=0.1,
                ware_fare=2200, break_up_fee=12/13, service_type='远程', extra_station_duration=8)
    print(res)