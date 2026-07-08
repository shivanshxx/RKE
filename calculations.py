"""
Payroll calculations as per Indian statutory rules:
- PF  : Employees' Provident Fund (EPF Act 1952)
- ESI : Employees' State Insurance (ESI Act 1948)
- TDS : Tax Deducted at Source (Income Tax Act 1961)
- PT  : Professional Tax — Uttar Pradesh does NOT levy PT (0)
- Shram Sahinta (Labour Laws) minimum wage compliance
"""

# UP Minimum Wage (unskilled) - approximate, update as per UP Govt notification
UP_MIN_WAGE_UNSKILLED = 10000   # per month
UP_MIN_WAGE_SEMI_SKILLED = 11000
UP_MIN_WAGE_SKILLED = 13000

# EPS (pension) wage ceiling per EPFO — applies ONLY to the pension split
# within the employer share. PF itself is computed on FULL Basic+DA
# (no ceiling), per this company's policy of contributing on actual wages.
EPS_WAGE_CEILING = 15000

# ESI gross salary limit
ESI_GROSS_LIMIT = 21000


def compute_pro_rata(amount, total_days, days_worked):
    """Pro-rata salary for partial month"""
    if total_days <= 0:
        return 0.0
    return round((amount / total_days) * days_worked, 2)


def per_day_rate(monthly_amount, total_days):
    """Per-day salary rate = monthly amount / total days in that month."""
    if total_days <= 0:
        return 0.0
    return round(monthly_amount / total_days, 2)


def calendar_days_in_month(year, month):
    """Actual number of calendar days in a given month/year."""
    import calendar
    return calendar.monthrange(year, month)[1]


def calculate_pf(basic_da, pf_applicable=True):
    """
    PF on FULL Basic+DA — no wage ceiling.
    Employee : 12% of Basic+DA
    Employer : 12% of Basic+DA, split as:
        -> EPS (pension) 8.33% of wages CAPPED at 15,000 (statutory hard cap;
           EPFO rejects ECR files that exceed it)
        -> EPF = remainder of the employer 12%
    """
    if not pf_applicable:
        return 0, 0, 0, 0

    emp_pf = round(basic_da * 0.12)
    er_total = round(basic_da * 0.12)
    er_eps = round(min(basic_da, EPS_WAGE_CEILING) * 0.0833)
    er_epf = er_total - er_eps
    return emp_pf, er_total, er_epf, er_eps


def calculate_esi(gross_salary, esi_applicable=True, eligibility_gross=None):
    """
    Applicable only if the rate of wages (eligibility_gross, i.e. the notional
    full-month gross — defaults to gross_salary if not given) is <= ESI_GROSS_LIMIT
    (Rs 21,000). Contribution itself is computed on the actual gross paid.
    Employee : 0.75%
    Employer : 3.25%
    """
    check_gross = eligibility_gross if eligibility_gross is not None else gross_salary
    if not esi_applicable or check_gross > ESI_GROSS_LIMIT:
        return 0, 0

    # ESIC rule: contributions are rounded UP to the next higher rupee,
    # not to the nearest rupee.
    import math
    emp_esi = math.ceil(gross_salary * 0.0075)
    er_esi = math.ceil(gross_salary * 0.0325)
    return emp_esi, er_esi


# Professional Tax slabs by state (monthly), keyed by lowercase state name.
# States not listed (e.g. Uttar Pradesh) do not levy PT.
PT_SLABS = {
    'maharashtra': [(7500, 0), (10000, 175), (float('inf'), 200)],
    'karnataka':   [(15000, 0), (float('inf'), 200)],
    'west bengal': [(10000, 0), (15000, 110), (25000, 130), (40000, 150), (float('inf'), 200)],
    'gujarat':     [(12000, 0), (float('inf'), 200)],
    'madhya pradesh': [(225000 / 12, 0), (float('inf'), 208)],
}


def calculate_pt(gross_salary, state='Uttar Pradesh'):
    """Professional Tax is state-specific and levied on monthly gross salary.
    Uttar Pradesh and several other states do not levy PT."""
    slabs = PT_SLABS.get((state or '').strip().lower())
    if not slabs:
        return 0
    for limit, pt in slabs:
        if gross_salary <= limit:
            return pt
    return 0


# ---- TDS / Income Tax ----

# Fallback slabs used only if the tax_slabs DB table is empty/unavailable.
_FALLBACK_SLABS = {
    'new': [(0, 400000, 0.00), (400000, 800000, 0.05), (800000, 1200000, 0.10),
            (1200000, 1600000, 0.15), (1600000, 2000000, 0.20),
            (2000000, 2400000, 0.25), (2400000, None, 0.30)],
    'old': [(0, 250000, 0.00), (250000, 500000, 0.05),
            (500000, 1000000, 0.20), (1000000, None, 0.30)],
}


def _get_slabs(regime, fy_start):
    """Slabs come from the database (updatable without a re-release);
    hardcoded values are only a last-resort fallback."""
    try:
        import database as db
        slabs = db.get_tax_slabs(regime, fy_start)
        if slabs:
            return slabs
    except Exception:
        pass
    return _FALLBACK_SLABS[regime]


def _slab_tax(taxable, slabs):
    tax = 0.0
    for lo, hi, rate in slabs:
        if taxable > lo:
            top = min(taxable, hi) if hi else taxable
            tax += (top - lo) * rate
    return tax


def _new_regime_tax(income, fy_start=None):
    """New Tax Regime. Standard deduction Rs 75,000 for salaried.
    Rebate u/s 87A: up to Rs 60,000 for taxable income up to Rs 12,00,000."""
    if fy_start is None:
        fy_start = current_fy_start()
    std_deduction = 75000
    taxable = max(0, income - std_deduction)

    tax = _slab_tax(taxable, _get_slabs('new', fy_start))

    if taxable <= 1200000:
        rebate = min(tax, 60000)
        tax = max(0.0, tax - rebate)

    # Surcharge (applicable on higher incomes)
    if taxable > 5000000:
        tax += tax * 0.10
    elif taxable > 2500000:
        tax += tax * 0.15  # marginal relief may apply but simplified

    # Health & Education Cess 4%
    tax = tax * 1.04
    return tax


def _old_regime_tax(income, deductions_80c=0, hra_exempt=0, lta=0, fy_start=None):
    """Old Tax Regime"""
    if fy_start is None:
        fy_start = current_fy_start()
    std_deduction = 50000
    taxable = max(0, income - std_deduction - deductions_80c - hra_exempt - lta)

    tax = _slab_tax(taxable, _get_slabs('old', fy_start))

    # Rebate u/s 87A: max Rs 12,500 if taxable <= 5,00,000
    if taxable <= 500000:
        rebate = min(tax, 12500)
        tax = max(0.0, tax - rebate)

    tax = tax * 1.04  # 4% cess
    return tax


def current_fy_start():
    """FY start year for today (April-March)."""
    from datetime import date
    today = date.today()
    return today.year if today.month >= 4 else today.year - 1


def calculate_annual_tax(annual_gross, regime='new', deductions_80c=0, hra_exempt=0, lta=0):
    """Return annual income tax"""
    if regime == 'new':
        return _new_regime_tax(annual_gross)
    else:
        return _old_regime_tax(annual_gross, deductions_80c, hra_exempt, lta)


def calculate_monthly_tds(projected_annual_gross, regime='new', deductions_80c=0,
                           hra_exempt=0, lta=0, months_remaining=12, ytd_tds_paid=0):
    """
    Section 192 style monthly TDS:
    Tax is computed on the *projected* annual income (YTD actual + current-month gross
    extrapolated for the rest of the FY). The tax already deducted so far in the FY
    (ytd_tds_paid) is subtracted, and the balance is spread over the remaining months
    (including the current one) — not a flat annual_tax/12.
    """
    if months_remaining <= 0:
        return 0
    annual_tax = calculate_annual_tax(projected_annual_gross, regime, deductions_80c, hra_exempt, lta)
    remaining_tax = max(0.0, annual_tax - ytd_tds_paid)
    return round(remaining_tax / months_remaining)


def months_remaining_in_fy(month):
    """Number of months remaining in the FY (April–March), including the given month."""
    fy_index = month - 4 if month >= 4 else month + 8   # April=0 ... March=11
    return 12 - fy_index


def compute_salary(emp, total_days=26, days_worked=26, company_state='Uttar Pradesh',
                    ytd_gross=0.0, ytd_tds=0.0, months_remaining=12):
    """
    Salary is billed on a per-day basis: each component on the employee record
    (basic, hra, da, special_allowance, other_allowance) is the PER-DAY rate
    entered for that employee. The month's salary = per-day rate x days the
    employee actually came (days_worked). `total_days` (calendar days in the
    month) is only used to derive the *full-month notional gross* — needed to
    correctly decide ESI/PT eligibility, which is based on the rate of wages,
    not the reduced amount caused by absence.

    `ytd_gross`/`ytd_tds` are the employee's totals for the current financial year
    *before* this month (used to true-up the monthly TDS per Section 192).
    `months_remaining` includes the current month.
    Returns a dict with all components.
    """
    per_day_basic = emp['basic']
    per_day_hra   = emp['hra']
    per_day_da    = emp['da']
    per_day_spec  = emp['special_allowance']
    per_day_other = emp['other_allowance']
    per_day_gross = per_day_basic + per_day_hra + per_day_da + per_day_spec + per_day_other

    # Actual amount payable for the days the employee came
    basic  = round(per_day_basic * days_worked, 2)
    hra    = round(per_day_hra   * days_worked, 2)
    da     = round(per_day_da    * days_worked, 2)
    spec   = round(per_day_spec  * days_worked, 2)
    other  = round(per_day_other * days_worked, 2)
    gross  = round(basic + hra + da + spec + other, 2)

    # Notional full-month gross (as if present every calendar day) — used only
    # to determine ESI/PT eligibility, per statutory convention.
    full_month_gross = round(per_day_gross * total_days, 2)

    basic_da = basic + da

    emp_pf, er_pf, er_epf, er_eps = calculate_pf(basic_da, bool(emp['pf_applicable']))
    emp_esi, er_esi = calculate_esi(gross, bool(emp['esi_applicable']), eligibility_gross=full_month_gross)
    pt = calculate_pt(full_month_gross, company_state)

    # Project annual income: YTD actual + this month's gross extrapolated for the rest of the FY
    projected_annual_gross = ytd_gross + (gross * months_remaining)
    tds = calculate_monthly_tds(
        projected_annual_gross, emp.get('tax_regime', 'new'),
        months_remaining=months_remaining, ytd_tds_paid=ytd_tds
    ) if emp['tds_applicable'] else 0

    total_deductions = emp_pf + emp_esi + tds + pt
    net = round(gross - total_deductions, 2)

    return {
        'basic': basic,
        'hra': hra,
        'da': da,
        'special_allowance': spec,
        'other_allowance': other,
        'gross_salary': round(gross, 2),
        'per_day_gross': per_day_gross,
        'pf_employee': emp_pf,
        'esi_employee': emp_esi,
        'tds': tds,
        'pt': pt,
        'other_deductions': 0,
        'total_deductions': round(total_deductions, 2),
        'net_salary': net,
        'pf_employer': er_pf,
        'esi_employer': er_esi,
    }


def check_wage_code_50pct(basic, da, gross):
    """Labour Codes (in force since 21 Nov 2025): 'wages' (basic + DA) must be
    at least 50% of total remuneration. Returns (ok, actual_pct)."""
    if gross <= 0:
        return True, 0.0
    pct = (basic + da) / gross * 100
    return pct >= 50.0, round(pct, 1)


def check_minimum_wage(basic_da, skill_category='unskilled'):
    """Returns (ok, min_wage, shortfall)"""
    limits = {
        'unskilled': UP_MIN_WAGE_UNSKILLED,
        'semi_skilled': UP_MIN_WAGE_SEMI_SKILLED,
        'skilled': UP_MIN_WAGE_SKILLED,
    }
    min_w = limits.get(skill_category, UP_MIN_WAGE_UNSKILLED)
    shortfall = max(0, min_w - basic_da)
    return shortfall == 0, min_w, shortfall


def apply_extras(sal, additional_earnings=0, other_deductions=0):
    """Apply one-off earnings (bonus/overtime) and deductions (fine/advance
    recovery) to a computed salary dict, recomputing totals and net."""
    sal['additional_earnings'] = round(additional_earnings or 0, 2)
    sal['other_deductions'] = round(other_deductions or 0, 2)
    sal['total_deductions'] = round(sal['pf_employee'] + sal['esi_employee'] +
                                    sal['tds'] + sal['pt'] + sal['other_deductions'], 2)
    sal['net_salary'] = round(sal['gross_salary'] + sal['additional_earnings'] -
                              sal['total_deductions'], 2)
    return sal


def calculate_gratuity(doj_str, last_day_str, per_day_basic_da):
    """
    Payment of Gratuity Act 1972: eligible after 5 years of continuous service.
    Gratuity = (15/26) x last drawn monthly wage (Basic+DA) x completed years.
    A final partial year over 6 months rounds up to a full year.
    Returns (eligible, years_counted, amount).
    """
    from datetime import datetime as _dt
    try:
        doj = _dt.strptime(doj_str.strip(), '%Y-%m-%d')
    except (ValueError, AttributeError):
        try:
            doj = _dt.strptime(doj_str.strip(), '%d-%m-%Y')
        except (ValueError, AttributeError):
            return False, 0, 0.0
    try:
        end = _dt.strptime(last_day_str.strip(), '%Y-%m-%d')
    except (ValueError, AttributeError):
        try:
            end = _dt.strptime(last_day_str.strip(), '%d-%m-%Y')
        except (ValueError, AttributeError):
            return False, 0, 0.0

    days = (end - doj).days
    if days < 5 * 365:
        return False, 0, 0.0

    full_years = days // 365
    rem_days = days - full_years * 365
    years = int(full_years + (1 if rem_days > 182 else 0))

    monthly_wage = per_day_basic_da * 26  # standard monthly wage basis
    amount = round((15 / 26) * monthly_wage * years, 2)
    return True, years, amount


def compliance_deadlines(today=None):
    """Statutory deadlines for last month's payroll. Returns a list of
    (name, due_date, status) where status is 'overdue' | 'due_soon' | 'upcoming'."""
    from datetime import date
    today = today or date.today()

    # Deadlines fall in the current month, for the previous wage month
    prev_month = today.month - 1 or 12
    prev_year = today.year if today.month > 1 else today.year - 1
    label = f"{MONTH_NAMES[prev_month]} {prev_year}"

    items = [
        (f"TDS deposit — salary of {label}", date(today.year, today.month, 7)),
        (f"PF (EPF) payment + ECR — {label}", date(today.year, today.month, 15)),
        (f"ESI contribution — {label}", date(today.year, today.month, 15)),
    ]

    out = []
    for name, due in items:
        if today > due:
            status = 'overdue'
        elif (due - today).days <= 5:
            status = 'due_soon'
        else:
            status = 'upcoming'
        out.append((name, due, status))
    return out


MONTH_NAMES = {
    1: 'January', 2: 'February', 3: 'March', 4: 'April',
    5: 'May', 6: 'June', 7: 'July', 8: 'August',
    9: 'September', 10: 'October', 11: 'November', 12: 'December'
}

NUM_TO_WORDS_MAP = [
    '', 'One', 'Two', 'Three', 'Four', 'Five', 'Six', 'Seven', 'Eight', 'Nine',
    'Ten', 'Eleven', 'Twelve', 'Thirteen', 'Fourteen', 'Fifteen', 'Sixteen',
    'Seventeen', 'Eighteen', 'Nineteen'
]
TENS = ['', '', 'Twenty', 'Thirty', 'Forty', 'Fifty',
        'Sixty', 'Seventy', 'Eighty', 'Ninety']


def _words_lt1000(n):
    if n == 0:
        return ''
    elif n < 20:
        return NUM_TO_WORDS_MAP[n]
    elif n < 100:
        return TENS[n // 10] + ((' ' + NUM_TO_WORDS_MAP[n % 10]) if n % 10 else '')
    else:
        rest = _words_lt1000(n % 100)
        return NUM_TO_WORDS_MAP[n // 100] + ' Hundred' + ((' and ' + rest) if rest else '')


def amount_to_words(amount):
    """Convert numeric amount to Indian English words"""
    amount = int(round(amount))
    if amount == 0:
        return 'Zero Rupees Only'

    crore   = amount // 10000000;  amount %= 10000000
    lakh    = amount // 100000;    amount %= 100000
    thousand = amount // 1000;     amount %= 1000
    rest    = amount

    parts = []
    if crore:   parts.append(_words_lt1000(crore) + ' Crore')
    if lakh:    parts.append(_words_lt1000(lakh) + ' Lakh')
    if thousand: parts.append(_words_lt1000(thousand) + ' Thousand')
    if rest:    parts.append(_words_lt1000(rest))

    return ' '.join(parts) + ' Rupees Only'
