from marshmallow import Schema, fields

from main.util.personal_tax import cal as cal_personal_tax

from main.util.work_dates import month_work_days


class CalKwargs(object):
    salary_type: bool = None
    employ_type: bool = None
    money: float = None
    work_duration: float = None
    work_extra_duration: float = None
    holiday_extra_duration: float = None
    weekend_extra_duration: float = None
    shift_duration: float = None
    work_day_shift_rate: float = None
    weekend_shift_rate: float = None
    holiday_shift_rate: float = None
    charging_num: float = None
    out_duty_days: float = None
    service_fee_rate: float = None
    tax_rate: float = None
    year_month: int = None
    shift_type: bool = None
    use_hr_service: bool = None
    hr_fee_rate: float = None
    finance_rate: float = None
    work_station_fee: float = None
    tax_free_rate: float = None
    ware_fare: float = None
    break_up_fee_rate: float = None
    service_type: str = None
    extra_station_duration: float = None


class Numeration(object):
    def __init__(self, cal_kwargs: CalKwargs):
        self.cal_kwargs = cal_kwargs

    @property
    def legal_duration(self):
        return len(month_work_days(self.cal_kwargs.year_month)) * 8

    @property
    def charging_duration(self):
        return self.cal_kwargs.charging_num * 8

    @property
    def extra_total_duration(self):
        return self.cal_kwargs.work_extra_duration * self.cal_kwargs.work_day_shift_rate + self.cal_kwargs.holiday_extra_duration * self.cal_kwargs.holiday_shift_rate \
               + self.cal_kwargs.weekend_extra_duration * self.cal_kwargs.weekend_shift_rate

    @property
    def duration_salary(self):
        return self.cal_kwargs.money / self.charging_duration if self.cal_kwargs.salary_type else self.cal_kwargs.money / 8

    @property
    def on_duty_duration(self):
        if self.cal_kwargs.shift_type:
            return self.legal_duration if self.cal_kwargs.work_duration > self.legal_duration else self.cal_kwargs.work_duration
        else:
            return self.cal_kwargs.work_duration + self.cal_kwargs.shift_duration

    @property
    def extra_salary(self):
        return self.extra_total_duration * self.duration_salary if self.cal_kwargs.shift_type else 0

    @property
    def amerce(self):  # 缺勤扣除
        return self.duration_salary * self.cal_kwargs.out_duty_days if self.cal_kwargs.salary_type else 0

    @property
    def labor_salary(self):  # 工时费
        labor_salary = self.duration_salary * self.on_duty_duration
        if self.cal_kwargs.shift_type:
            labor_salary = labor_salary + self.extra_salary
        if self.cal_kwargs.salary_type:
            if self.charging_duration < self.on_duty_duration < self.legal_duration:
                labor_salary = self.cal_kwargs.money - self.amerce
                if self.cal_kwargs.shift_type:
                    labor_salary = labor_salary + self.extra_salary
        return labor_salary

    @property
    def station_salary(self):  # 工位费
        if self.cal_kwargs.service_type == '远程':
            temp = self.cal_kwargs.work_station_fee / 8
            if self.cal_kwargs.shift_type:
                station_salary = temp * (self.on_duty_duration + self.cal_kwargs.extra_station_duration)
            else:
                station_salary = temp * (self.on_duty_duration + self.cal_kwargs.shift_duration)
            return station_salary if station_salary < 800 else 800
        return 0

    @property
    def company_pay(self):  # 人员服务费
        return self.labor_salary + self.station_salary

    @property
    def service_fee(self):
        return self.cal_kwargs.service_fee_rate * self.labor_salary

    @property
    def tax(self):
        return self.cal_kwargs.tax_rate * self.company_pay

    @property
    def hr_fee(self):
        return self.cal_kwargs.hr_fee_rate * self.labor_salary if self.cal_kwargs.use_hr_service else 0

    @property
    def finance_fee(self):
        return self.cal_kwargs.finance_rate * self.labor_salary

    @property
    def engineer_income_with_tax(self):  # 人员可支配费用
        return self.labor_salary * (
                1 - self.cal_kwargs.service_fee_rate - self.cal_kwargs.tax_rate - self.cal_kwargs.finance_rate) - self.hr_fee

    @property
    def tax_fee(self):
        return self.engineer_income_with_tax * self.cal_kwargs.tax_free_rate

    @property
    def engineer_tax(self):
        return cal_personal_tax(
            self.engineer_income_with_tax - self.cal_kwargs.ware_fare) if self.cal_kwargs.employ_type else 0

    @property
    def break_up_fee(self):
        return (self.engineer_income_with_tax - self.cal_kwargs.ware_fare - self.engineer_tax) * (
                1 - self.cal_kwargs.break_up_fee_rate) if self.cal_kwargs.employ_type else 0

    @property
    def engineer_get(self):
        return (
                       self.engineer_income_with_tax - self.cal_kwargs.ware_fare - self.engineer_tax) * self.cal_kwargs.break_up_fee_rate if self.cal_kwargs.employ_type else 0


class CalPayment(Schema):
    company_pay = fields.Float()
    hr_fee = fields.Float()
    service_fee_rate = fields.Float()
    finance_fee = fields.Float()
    tax = fields.Float()
    engineer_income_with_tax = fields.Float()
    engineer_get = fields.Float()
    engineer_tax = fields.Float()
    break_up_fee_rate = fields.Float()
    break_up_fee = fields.Float()
    out_duty_days = fields.Float()
    tax_rate = fields.Float()
    station_salary = fields.Float()
    hr_fee_rate = fields.Float()
    finance_rate = fields.Float()
    use_hr_service = fields.Float()
    tax_free_rate = fields.Float()
    ware_fare = fields.Float()
    service_fee = fields.Float()
    tax_fee = fields.Float()
