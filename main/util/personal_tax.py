def cal(income):
    tax_income = income - 5000
    if tax_income <= 0:
        return 0
    if tax_income < 3000:
        return tax_income * 0.03
    if tax_income < 12000:
        return tax_income * 0.1 - 210
    if tax_income < 25000:
        return tax_income * 0.2 - 1410
    if tax_income < 35000:
        return tax_income * 0.25 - 2660
    if tax_income < 55000:
        return tax_income * 0.3 - 4410
    if tax_income < 80000:
        return tax_income * 0.35 - 7160
    return 80000 * 0.45 - 15160
