"""
PDF Report Generation:
  - Salary Slip
  - Form 16 (Part A + Part B)
Uses ReportLab library.
"""
import os
import sys
from datetime import datetime
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.units import mm, cm
from reportlab.platypus import (SimpleDocTemplate, Table, TableStyle, Paragraph,
                                 Spacer, HRFlowable, KeepTogether)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from reportlab.platypus import PageBreak

import calculations as calc

if getattr(sys, 'frozen', False):
    _BASE_DIR = os.path.dirname(os.path.abspath(sys.executable))
else:
    _BASE_DIR = os.path.dirname(os.path.abspath(__file__))

OUTPUT_DIR = os.path.join(_BASE_DIR, "output")
os.makedirs(OUTPUT_DIR, exist_ok=True)

# ---- Colour palette ----
DARK_BLUE  = colors.HexColor("#1B3A6B")
MID_BLUE   = colors.HexColor("#2E6DA4")
LIGHT_BLUE = colors.HexColor("#D6E4F0")
ACCENT     = colors.HexColor("#F0A500")
LIGHT_GRAY = colors.HexColor("#F5F5F5")
WHITE      = colors.white
BLACK      = colors.black
GREEN      = colors.HexColor("#1E7E34")


def _styles():
    ss = getSampleStyleSheet()
    custom = {}
    custom['CompanyName'] = ParagraphStyle('CompanyName', fontSize=16, fontName='Helvetica-Bold',
                                            textColor=DARK_BLUE, alignment=TA_CENTER, spaceAfter=2)
    custom['CompanyAddr'] = ParagraphStyle('CompanyAddr', fontSize=9, fontName='Helvetica',
                                            textColor=DARK_BLUE, alignment=TA_CENTER, spaceAfter=1)
    custom['SlipTitle']   = ParagraphStyle('SlipTitle', fontSize=12, fontName='Helvetica-Bold',
                                            textColor=WHITE, alignment=TA_CENTER)
    custom['Normal']      = ParagraphStyle('Normal', fontSize=9, fontName='Helvetica')
    custom['Bold']        = ParagraphStyle('Bold', fontSize=9, fontName='Helvetica-Bold')
    custom['Small']       = ParagraphStyle('Small', fontSize=8, fontName='Helvetica')
    custom['Header2']     = ParagraphStyle('Header2', fontSize=10, fontName='Helvetica-Bold',
                                            textColor=DARK_BLUE)
    custom['Center']      = ParagraphStyle('Center', fontSize=9, fontName='Helvetica', alignment=TA_CENTER)
    custom['Right']       = ParagraphStyle('Right', fontSize=9, fontName='Helvetica', alignment=TA_RIGHT)
    return custom


def _para(text, style):
    return Paragraph(str(text), style)


# ================================================================
#  SALARY SLIP
# ================================================================

def generate_salary_slip(company, employee, salary, output_path=None):
    """
    Generate a professional salary slip PDF.
    Returns path to the generated file.
    """
    month_name = calc.MONTH_NAMES[salary['month']]
    year = salary['year']
    if not salary.get('per_day_gross'):
        salary['per_day_gross'] = calc.per_day_rate(salary['gross_salary'], salary.get('total_days') or 1)

    if output_path is None:
        fname = f"SalarySlip_{employee['emp_code']}_{year}_{salary['month']:02d}.pdf"
        output_path = os.path.join(OUTPUT_DIR, fname)

    doc = SimpleDocTemplate(output_path, pagesize=A4,
                            leftMargin=15*mm, rightMargin=15*mm,
                            topMargin=15*mm, bottomMargin=15*mm)

    s = _styles()
    story = []

    # ---- Header ----
    header_data = [[
        _para(company.get('name', 'Ram Krishna Enterprises'), s['CompanyName'])
    ]]
    addr = f"{company.get('address', '')} | {company.get('city', 'Prayagraj')}, {company.get('state', 'Uttar Pradesh')} - {company.get('pincode', '')}"
    if company.get('phone'):
        addr += f" | Ph: {company['phone']}"

    header_tbl = Table([[_para(company.get('name', 'Ram Krishna Enterprises'), s['CompanyName'])],
                        [_para(addr, s['CompanyAddr'])]], colWidths=[180*mm])
    header_tbl.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), LIGHT_BLUE),
        ('BOX', (0,0), (-1,-1), 1, DARK_BLUE),
        ('TOPPADDING', (0,0), (-1,-1), 6),
        ('BOTTOMPADDING', (0,0), (-1,-1), 4),
    ]))
    story.append(header_tbl)
    story.append(Spacer(1, 3*mm))

    # ---- Slip title bar ----
    title_tbl = Table([[_para(f'SALARY SLIP — {month_name.upper()} {year}', s['SlipTitle'])]],
                      colWidths=[180*mm])
    title_tbl.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), DARK_BLUE),
        ('TOPPADDING', (0,0), (-1,-1), 5),
        ('BOTTOMPADDING', (0,0), (-1,-1), 5),
    ]))
    story.append(title_tbl)
    story.append(Spacer(1, 4*mm))

    # ---- Employee details ----
    reg_data = [
        [_para('Employee Code', s['Bold']),  _para(employee.get('emp_code',''), s['Normal']),
         _para('Designation', s['Bold']),    _para(employee.get('designation',''), s['Normal'])],
        [_para('Employee Name', s['Bold']),  _para(employee.get('name',''), s['Normal']),
         _para('Department', s['Bold']),     _para(employee.get('department',''), s['Normal'])],
        [_para('Date of Joining', s['Bold']),_para(employee.get('doj',''), s['Normal']),
         _para('PAN', s['Bold']),            _para(employee.get('pan',''), s['Normal'])],
        [_para('PF Number', s['Bold']),      _para(employee.get('pf_number',''), s['Normal']),
         _para('UAN', s['Bold']),            _para(employee.get('uan',''), s['Normal'])],
        [_para('ESI Number', s['Bold']),     _para(employee.get('esi_number',''), s['Normal']),
         _para('Bank Account', s['Bold']),   _para(employee.get('bank_account',''), s['Normal'])],
        [_para('Days in Month', s['Bold']),  _para(str(salary['total_days']), s['Normal']),
         _para('Days Worked', s['Bold']),    _para(str(salary['days_worked']), s['Normal'])],
        [_para('Per Day Rate', s['Bold']),
         _para(f"Rs. {salary.get('per_day_gross', 0):,.2f}", s['Normal']),
         _para('', s['Normal']), _para('', s['Normal'])],
    ]
    reg_tbl = Table(reg_data, colWidths=[38*mm, 52*mm, 38*mm, 52*mm])
    reg_tbl.setStyle(TableStyle([
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor("#CCCCCC")),
        ('BACKGROUND', (0,0), (0,-1), LIGHT_BLUE),
        ('BACKGROUND', (2,0), (2,-1), LIGHT_BLUE),
        ('ROWBACKGROUNDS', (0,0), (-1,-1), [WHITE, LIGHT_GRAY]),
        ('FONTNAME', (0,0), (-1,-1), 'Helvetica'),
        ('FONTSIZE', (0,0), (-1,-1), 9),
        ('TOPPADDING', (0,0), (-1,-1), 4),
        ('BOTTOMPADDING', (0,0), (-1,-1), 4),
        ('LEFTPADDING', (0,0), (-1,-1), 5),
    ]))
    story.append(reg_tbl)
    story.append(Spacer(1, 4*mm))

    # ---- Earnings & Deductions side by side ----
    earn_head = [_para('EARNINGS', s['SlipTitle']), '', _para('DEDUCTIONS', s['SlipTitle'])]

    rows = [
        [_para('Component', s['Bold']), _para('Amount (₹)', s['Bold']),
         '', _para('Component', s['Bold']), _para('Amount (₹)', s['Bold'])],
    ]

    earn_items = [
        ('Basic Salary',       salary['basic']),
        ('HRA',                salary['hra']),
        ('Dearness Allowance', salary['da']),
        ('Special Allowance',  salary['special_allowance']),
        ('Other Allowance',    salary['other_allowance']),
    ]
    ded_items = [
        ('PF (Employee 12%)',  salary['pf_employee']),
        ('ESI (Employee 0.75%)', salary['esi_employee']),
        ('TDS (Income Tax)',   salary['tds']),
        ('Prof. Tax (PT)',     salary['pt']),
        ('Other Deductions',  salary['other_deductions']),
    ]

    max_rows = max(len(earn_items), len(ded_items))
    for i in range(max_rows):
        ec, ea = earn_items[i] if i < len(earn_items) else ('', '')
        dc, da_ = ded_items[i] if i < len(ded_items) else ('', '')
        ea_str = f'{ea:,.2f}' if ea != '' else ''
        da_str = f'{da_:,.2f}' if da_ != '' else ''
        rows.append([_para(ec, s['Normal']), _para(ea_str, s['Right']),
                     '', _para(dc, s['Normal']), _para(da_str, s['Right'])])

    # Totals row
    rows.append([_para('Gross Salary', s['Bold']),
                 _para(f"{salary['gross_salary']:,.2f}", s['Right']),
                 '',
                 _para('Total Deductions', s['Bold']),
                 _para(f"{salary['total_deductions']:,.2f}", s['Right'])])

    ed_tbl = Table(rows, colWidths=[55*mm, 30*mm, 5*mm, 55*mm, 30*mm])
    style_ed = [
        ('GRID', (0,0), (1,-1), 0.5, colors.HexColor("#CCCCCC")),
        ('GRID', (3,0), (4,-1), 0.5, colors.HexColor("#CCCCCC")),
        ('LINEAFTER', (1,0), (1,-1), 0, WHITE),
        ('BACKGROUND', (0,0), (1,0), MID_BLUE),
        ('BACKGROUND', (3,0), (4,0), MID_BLUE),
        ('TEXTCOLOR', (0,0), (1,0), WHITE),
        ('TEXTCOLOR', (3,0), (4,0), WHITE),
        ('ROWBACKGROUNDS', (0,1), (1,-1), [WHITE, LIGHT_GRAY]),
        ('ROWBACKGROUNDS', (3,1), (4,-1), [WHITE, LIGHT_GRAY]),
        ('BACKGROUND', (0,-1), (1,-1), LIGHT_BLUE),
        ('BACKGROUND', (3,-1), (4,-1), LIGHT_BLUE),
        ('FONTNAME', (0,-1), (1,-1), 'Helvetica-Bold'),
        ('FONTNAME', (3,-1), (4,-1), 'Helvetica-Bold'),
        ('TOPPADDING', (0,0), (-1,-1), 4),
        ('BOTTOMPADDING', (0,0), (-1,-1), 4),
        ('LEFTPADDING', (0,0), (-1,-1), 5),
    ]
    ed_tbl.setStyle(TableStyle(style_ed))
    story.append(ed_tbl)
    story.append(Spacer(1, 3*mm))

    # ---- Net Salary Bar ----
    net_words = calc.amount_to_words(salary['net_salary'])
    net_data = [[
        _para('NET SALARY (Take Home)', s['SlipTitle']),
        _para(f"₹ {salary['net_salary']:,.2f}", ParagraphStyle('NetAmt', fontSize=13,
               fontName='Helvetica-Bold', textColor=WHITE, alignment=TA_RIGHT))
    ]]
    net_tbl = Table(net_data, colWidths=[120*mm, 60*mm])
    net_tbl.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), GREEN),
        ('TOPPADDING', (0,0), (-1,-1), 7),
        ('BOTTOMPADDING', (0,0), (-1,-1), 7),
        ('LEFTPADDING', (0,0), (-1,-1), 8),
        ('RIGHTPADDING', (0,0), (-1,-1), 8),
    ]))
    story.append(net_tbl)

    words_tbl = Table([[_para(f'Amount in words: {net_words}', s['Small'])]],
                      colWidths=[180*mm])
    words_tbl.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), LIGHT_GRAY),
        ('TOPPADDING', (0,0), (-1,-1), 3),
        ('BOTTOMPADDING', (0,0), (-1,-1), 3),
        ('LEFTPADDING', (0,0), (-1,-1), 5),
    ]))
    story.append(words_tbl)
    story.append(Spacer(1, 4*mm))

    # ---- Employer contributions ----
    emp_contrib = [
        [_para('Employer PF Contribution', s['Bold']),
         _para(f"₹ {salary['pf_employer']:,.2f}", s['Normal']),
         _para('Employer ESI Contribution', s['Bold']),
         _para(f"₹ {salary['esi_employer']:,.2f}", s['Normal'])],
        [_para('Payment Mode', s['Bold']),
         _para(salary.get('payment_mode', 'Bank Transfer'), s['Normal']),
         _para('Bank', s['Bold']),
         _para(employee.get('bank_name', ''), s['Normal'])],
    ]
    ec_tbl = Table(emp_contrib, colWidths=[45*mm, 45*mm, 45*mm, 45*mm])
    ec_tbl.setStyle(TableStyle([
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor("#CCCCCC")),
        ('BACKGROUND', (0,0), (0,-1), LIGHT_BLUE),
        ('BACKGROUND', (2,0), (2,-1), LIGHT_BLUE),
        ('FONTNAME', (0,0), (-1,-1), 'Helvetica'),
        ('FONTSIZE', (0,0), (-1,-1), 9),
        ('TOPPADDING', (0,0), (-1,-1), 4),
        ('BOTTOMPADDING', (0,0), (-1,-1), 4),
        ('LEFTPADDING', (0,0), (-1,-1), 5),
    ]))
    story.append(ec_tbl)
    story.append(Spacer(1, 8*mm))

    # ---- Signature ----
    sig_data = [[
        _para('Employee Signature', s['Center']),
        '',
        _para('Authorised Signatory', s['Center'])
    ]]
    sig_tbl = Table(sig_data, colWidths=[60*mm, 60*mm, 60*mm])
    sig_tbl.setStyle(TableStyle([
        ('LINEABOVE', (0,0), (0,0), 1, DARK_BLUE),
        ('LINEABOVE', (2,0), (2,0), 1, DARK_BLUE),
        ('ALIGN', (0,0), (-1,-1), 'CENTER'),
        ('TOPPADDING', (0,0), (-1,-1), 20),
    ]))
    story.append(sig_tbl)

    # ---- Footer ----
    story.append(Spacer(1, 4*mm))
    footer_tbl = Table([[_para('This is a computer generated salary slip. No signature required.',
                               ParagraphStyle('footer', fontSize=7, fontName='Helvetica-Oblique',
                                              textColor=colors.gray, alignment=TA_CENTER))]],
                       colWidths=[180*mm])
    footer_tbl.setStyle(TableStyle([
        ('LINEABOVE', (0,0), (-1,-1), 0.5, colors.gray),
        ('TOPPADDING', (0,0), (-1,-1), 3),
    ]))
    story.append(footer_tbl)

    doc.build(story)
    return output_path


# ================================================================
#  FORM 16
# ================================================================

def generate_form16(company, employee, annual_records, financial_year, output_path=None):
    """
    Generate Form 16 (Part A + Part B) for a financial year.
    annual_records: list of monthly salary_record dicts (April to March).
    """
    if output_path is None:
        fy_str = financial_year.replace('/', '-')
        fname = f"Form16_{employee['emp_code']}_{fy_str}.pdf"
        output_path = os.path.join(OUTPUT_DIR, fname)

    doc = SimpleDocTemplate(output_path, pagesize=A4,
                            leftMargin=15*mm, rightMargin=15*mm,
                            topMargin=15*mm, bottomMargin=15*mm)

    s = _styles()
    story = []

    # ---- PART A ----
    _f16_part_a(story, s, company, employee, annual_records, financial_year)
    story.append(PageBreak())

    # ---- PART B ----
    _f16_part_b(story, s, company, employee, annual_records, financial_year)

    doc.build(story)
    return output_path


def _section_header(text, style):
    tbl = Table([[Paragraph(text, style)]], colWidths=[180*mm])
    tbl.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), DARK_BLUE),
        ('TOPPADDING', (0,0), (-1,-1), 5),
        ('BOTTOMPADDING', (0,0), (-1,-1), 5),
        ('LEFTPADDING', (0,0), (-1,-1), 8),
    ]))
    return tbl


def _data_row(label, value, s, bg=WHITE):
    return [Paragraph(label, s['Normal']), Paragraph(str(value), s['Normal'])]


def _f16_part_a(story, s, company, employee, annual_records, financial_year):
    title_style = ParagraphStyle('t16', fontSize=13, fontName='Helvetica-Bold',
                                  textColor=WHITE, alignment=TA_CENTER)

    story.append(_section_header('FORM 16 — PART A', title_style))
    story.append(Spacer(1, 3*mm))

    sub_title = ParagraphStyle('st', fontSize=10, fontName='Helvetica-Bold',
                                textColor=DARK_BLUE, alignment=TA_CENTER)
    story.append(Paragraph('Certificate under Section 203 of the Income Tax Act, 1961', sub_title))
    story.append(Paragraph('for Tax Deducted at Source on Salary', sub_title))
    story.append(Spacer(1, 4*mm))

    # Assessment year
    fy_parts = financial_year.split('-')
    ay = f"AY {int(fy_parts[0])+1}-{str(int(fy_parts[0])+2)[-2:]}"

    info = [
        ['Name of Employer', company.get('name', 'Ram Krishna Enterprises'),
         'Assessment Year', ay],
        ['Address of Employer', f"{company.get('address','')}, {company.get('city','Prayagraj')}",
         'Financial Year', financial_year],
        ['TAN of Employer', company.get('tan', 'N/A'),
         'PAN of Employer', company.get('pan', 'N/A')],
        ['Name of Employee', employee.get('name', ''),
         'PAN of Employee', employee.get('pan', 'N/A')],
        ['Address of Employee', f"{company.get('city','Prayagraj')}, {company.get('state','Uttar Pradesh')}",
         'Period of Employment', f"01/04/{fy_parts[0]} to 31/03/{fy_parts[1]}"],
    ]

    info_tbl = Table(info, colWidths=[45*mm, 50*mm, 42*mm, 43*mm])
    info_tbl.setStyle(TableStyle([
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor("#CCCCCC")),
        ('BACKGROUND', (0,0), (0,-1), LIGHT_BLUE),
        ('BACKGROUND', (2,0), (2,-1), LIGHT_BLUE),
        ('ROWBACKGROUNDS', (0,0), (-1,-1), [WHITE, LIGHT_GRAY]),
        ('FONTNAME', (0,0), (0,-1), 'Helvetica-Bold'),
        ('FONTNAME', (2,0), (2,-1), 'Helvetica-Bold'),
        ('FONTSIZE', (0,0), (-1,-1), 9),
        ('TOPPADDING', (0,0), (-1,-1), 4),
        ('BOTTOMPADDING', (0,0), (-1,-1), 4),
        ('LEFTPADDING', (0,0), (-1,-1), 5),
    ]))
    story.append(info_tbl)
    story.append(Spacer(1, 5*mm))

    # Monthly TDS table
    story.append(Paragraph('Monthly Tax Deducted at Source', ParagraphStyle('mhdr', fontSize=10,
                             fontName='Helvetica-Bold', textColor=DARK_BLUE)))
    story.append(Spacer(1, 2*mm))

    from calculations import MONTH_NAMES
    tds_rows = [
        [Paragraph(h, ParagraphStyle('th', fontSize=9, fontName='Helvetica-Bold', textColor=WHITE))
         for h in ['Month', 'Gross Salary (₹)', 'TDS Deducted (₹)', 'Remarks']]
    ]

    total_gross = 0
    total_tds = 0
    for rec in annual_records:
        mn = MONTH_NAMES.get(rec['month'], str(rec['month']))
        g = rec.get('gross_salary', 0)
        t = rec.get('tds', 0)
        total_gross += g
        total_tds += t
        tds_rows.append([
            Paragraph(f"{mn} {rec['year']}", s['Normal']),
            Paragraph(f"{g:,.2f}", s['Right']),
            Paragraph(f"{t:,.2f}", s['Right']),
            Paragraph(rec.get('remarks', ''), s['Normal'])
        ])

    tds_rows.append([
        Paragraph('TOTAL', ParagraphStyle('tot', fontSize=9, fontName='Helvetica-Bold')),
        Paragraph(f"{total_gross:,.2f}", ParagraphStyle('totr', fontSize=9, fontName='Helvetica-Bold', alignment=TA_RIGHT)),
        Paragraph(f"{total_tds:,.2f}", ParagraphStyle('totr2', fontSize=9, fontName='Helvetica-Bold', alignment=TA_RIGHT)),
        Paragraph('', s['Normal'])
    ])

    tds_tbl = Table(tds_rows, colWidths=[50*mm, 45*mm, 45*mm, 40*mm])
    tds_tbl.setStyle(TableStyle([
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor("#CCCCCC")),
        ('BACKGROUND', (0,0), (-1,0), MID_BLUE),
        ('ROWBACKGROUNDS', (0,1), (-1,-2), [WHITE, LIGHT_GRAY]),
        ('BACKGROUND', (0,-1), (-1,-1), LIGHT_BLUE),
        ('FONTNAME', (0,-1), (-1,-1), 'Helvetica-Bold'),
        ('TOPPADDING', (0,0), (-1,-1), 4),
        ('BOTTOMPADDING', (0,0), (-1,-1), 4),
        ('LEFTPADDING', (0,0), (-1,-1), 5),
    ]))
    story.append(tds_tbl)
    story.append(Spacer(1, 8*mm))

    # Verification
    story.append(Paragraph(
        f"I hereby certify that a sum of ₹ <b>{total_tds:,.2f}</b> has been deducted at source and "
        f"deposited to the credit of the Central Government as per the provisions of the Income Tax Act, 1961.",
        s['Normal']))
    story.append(Spacer(1, 12*mm))

    sig_data = [[
        Paragraph('Signature of Person Responsible for Deduction of Tax', s['Center']),
        Paragraph('Date:', s['Normal'])
    ]]
    sig_tbl = Table(sig_data, colWidths=[130*mm, 50*mm])
    sig_tbl.setStyle(TableStyle([
        ('LINEABOVE', (0,0), (0,0), 1, DARK_BLUE),
        ('TOPPADDING', (0,0), (-1,-1), 20),
    ]))
    story.append(sig_tbl)
    story.append(Paragraph(f"Full Name: {company.get('name', '')}", s['Normal']))
    story.append(Paragraph(f"Designation: Authorised Signatory", s['Normal']))


def _f16_part_b(story, s, company, employee, annual_records, financial_year):
    title_style = ParagraphStyle('t16b', fontSize=13, fontName='Helvetica-Bold',
                                  textColor=WHITE, alignment=TA_CENTER)

    story.append(_section_header('FORM 16 — PART B', title_style))
    story.append(Spacer(1, 3*mm))

    sub_title = ParagraphStyle('st2', fontSize=10, fontName='Helvetica-Bold',
                                textColor=DARK_BLUE, alignment=TA_CENTER)
    story.append(Paragraph('Statement showing particulars of Salary, Perquisites and other Income',
                            sub_title))
    story.append(Spacer(1, 4*mm))

    # Aggregate annual figures
    total = {k: sum(r.get(k, 0) for r in annual_records)
             for k in ['basic', 'hra', 'da', 'special_allowance', 'other_allowance',
                       'gross_salary', 'pf_employee', 'esi_employee', 'tds',
                       'pt', 'other_deductions', 'net_salary']}

    regime = employee.get('tax_regime', 'new')
    annual_gross = total['gross_salary']

    # Standard deduction
    std_deduction = 75000 if regime == 'new' else 50000
    taxable_income = max(0, annual_gross - std_deduction)

    from calculations import _new_regime_tax, _old_regime_tax
    gross_tax = _new_regime_tax(annual_gross) if regime == 'new' else _old_regime_tax(annual_gross)
    cess = gross_tax * 0.04 / 1.04   # approx extract
    net_tax = gross_tax

    # ---- Salary Details ----
    story.append(Paragraph('A. Details of Salary Paid', ParagraphStyle('sec', fontSize=10,
                             fontName='Helvetica-Bold', textColor=DARK_BLUE)))
    story.append(Spacer(1, 2*mm))

    sal_rows = [
        [Paragraph('Component', ParagraphStyle('th', fontSize=9, fontName='Helvetica-Bold', textColor=WHITE)),
         Paragraph('Annual Amount (₹)', ParagraphStyle('th2', fontSize=9, fontName='Helvetica-Bold',
                                                         textColor=WHITE, alignment=TA_RIGHT))],
        [Paragraph('1. Basic Salary', s['Normal']), Paragraph(f"{total['basic']:,.2f}", s['Right'])],
        [Paragraph('2. House Rent Allowance (HRA)', s['Normal']), Paragraph(f"{total['hra']:,.2f}", s['Right'])],
        [Paragraph('3. Dearness Allowance (DA)', s['Normal']), Paragraph(f"{total['da']:,.2f}", s['Right'])],
        [Paragraph('4. Special Allowance', s['Normal']), Paragraph(f"{total['special_allowance']:,.2f}", s['Right'])],
        [Paragraph('5. Other Allowance', s['Normal']), Paragraph(f"{total['other_allowance']:,.2f}", s['Right'])],
        [Paragraph('Gross Salary (Total)', ParagraphStyle('bold', fontSize=9, fontName='Helvetica-Bold')),
         Paragraph(f"{total['gross_salary']:,.2f}", ParagraphStyle('br', fontSize=9, fontName='Helvetica-Bold', alignment=TA_RIGHT))],
    ]

    sal_tbl = Table(sal_rows, colWidths=[130*mm, 50*mm])
    sal_tbl.setStyle(TableStyle([
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor("#CCCCCC")),
        ('BACKGROUND', (0,0), (-1,0), MID_BLUE),
        ('ROWBACKGROUNDS', (0,1), (-1,-2), [WHITE, LIGHT_GRAY]),
        ('BACKGROUND', (0,-1), (-1,-1), LIGHT_BLUE),
        ('TOPPADDING', (0,0), (-1,-1), 4),
        ('BOTTOMPADDING', (0,0), (-1,-1), 4),
        ('LEFTPADDING', (0,0), (-1,-1), 5),
    ]))
    story.append(sal_tbl)
    story.append(Spacer(1, 4*mm))

    # ---- Tax Computation ----
    story.append(Paragraph('B. Computation of Income Tax', ParagraphStyle('sec2', fontSize=10,
                             fontName='Helvetica-Bold', textColor=DARK_BLUE)))
    story.append(Spacer(1, 2*mm))

    regime_label = 'New Tax Regime (Section 115BAC)' if regime == 'new' else 'Old Tax Regime'
    tax_rows = [
        [Paragraph('Particulars', ParagraphStyle('th3', fontSize=9, fontName='Helvetica-Bold', textColor=WHITE)),
         Paragraph('Amount (₹)', ParagraphStyle('th4', fontSize=9, fontName='Helvetica-Bold',
                                                  textColor=WHITE, alignment=TA_RIGHT))],
        [Paragraph('Gross Salary', s['Normal']),       Paragraph(f"{annual_gross:,.2f}", s['Right'])],
        [Paragraph(f'Less: Standard Deduction ({regime_label})', s['Normal']),
         Paragraph(f"({std_deduction:,.2f})", s['Right'])],
        [Paragraph('Net Taxable Salary', ParagraphStyle('b', fontSize=9, fontName='Helvetica-Bold')),
         Paragraph(f"{taxable_income:,.2f}", ParagraphStyle('br2', fontSize=9, fontName='Helvetica-Bold', alignment=TA_RIGHT))],
        [Paragraph('Less: Deductions u/s 80C, 80D etc. (if old regime)', s['Normal']),
         Paragraph('0.00' if regime == 'new' else '—', s['Right'])],
        [Paragraph('Tax on Total Income (as per applicable slabs)', s['Normal']),
         Paragraph(f"{gross_tax:,.2f}", s['Right'])],
        [Paragraph('Add: Health & Education Cess @ 4%', s['Normal']),
         Paragraph(f"{gross_tax * 0.04 / 1.04:,.2f}", s['Right'])],
        [Paragraph('Total Tax Liability', ParagraphStyle('b2', fontSize=9, fontName='Helvetica-Bold')),
         Paragraph(f"{gross_tax:,.2f}", ParagraphStyle('br3', fontSize=9, fontName='Helvetica-Bold', alignment=TA_RIGHT))],
        [Paragraph('Tax Deducted at Source (TDS) u/s 192', s['Normal']),
         Paragraph(f"{total['tds']:,.2f}", s['Right'])],
        [Paragraph('Balance Tax Payable / (Refundable)', ParagraphStyle('b3', fontSize=9, fontName='Helvetica-Bold')),
         Paragraph(f"{max(0, gross_tax - total['tds']):,.2f}", ParagraphStyle('br4', fontSize=9, fontName='Helvetica-Bold', alignment=TA_RIGHT))],
    ]

    tax_tbl = Table(tax_rows, colWidths=[130*mm, 50*mm])
    tax_tbl.setStyle(TableStyle([
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor("#CCCCCC")),
        ('BACKGROUND', (0,0), (-1,0), MID_BLUE),
        ('ROWBACKGROUNDS', (0,1), (-1,-1), [WHITE, LIGHT_GRAY]),
        ('BACKGROUND', (0,-1), (-1,-1), LIGHT_BLUE),
        ('TOPPADDING', (0,0), (-1,-1), 4),
        ('BOTTOMPADDING', (0,0), (-1,-1), 4),
        ('LEFTPADDING', (0,0), (-1,-1), 5),
    ]))
    story.append(tax_tbl)
    story.append(Spacer(1, 4*mm))

    # ---- Deductions Summary ----
    story.append(Paragraph('C. Annual Deductions Summary', ParagraphStyle('sec3', fontSize=10,
                             fontName='Helvetica-Bold', textColor=DARK_BLUE)))
    story.append(Spacer(1, 2*mm))

    ded_rows = [
        [Paragraph('Deduction', ParagraphStyle('th5', fontSize=9, fontName='Helvetica-Bold', textColor=WHITE)),
         Paragraph('Annual Amount (₹)', ParagraphStyle('th6', fontSize=9, fontName='Helvetica-Bold',
                                                          textColor=WHITE, alignment=TA_RIGHT))],
        [Paragraph('PF - Employee Contribution (12% of Basic+DA)', s['Normal']),
         Paragraph(f"{total['pf_employee']:,.2f}", s['Right'])],
        [Paragraph('ESI - Employee Contribution (0.75% of Gross)', s['Normal']),
         Paragraph(f"{total['esi_employee']:,.2f}", s['Right'])],
        [Paragraph('TDS (Income Tax deducted u/s 192)', s['Normal']),
         Paragraph(f"{total['tds']:,.2f}", s['Right'])],
        [Paragraph('Professional Tax (PT)', s['Normal']),
         Paragraph(f"{total['pt']:,.2f}", s['Right'])],
        [Paragraph('Total Deductions', ParagraphStyle('b4', fontSize=9, fontName='Helvetica-Bold')),
         Paragraph(f"{total['pf_employee']+total['esi_employee']+total['tds']+total['pt']:,.2f}",
                   ParagraphStyle('br5', fontSize=9, fontName='Helvetica-Bold', alignment=TA_RIGHT))],
    ]

    ded_tbl = Table(ded_rows, colWidths=[130*mm, 50*mm])
    ded_tbl.setStyle(TableStyle([
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor("#CCCCCC")),
        ('BACKGROUND', (0,0), (-1,0), MID_BLUE),
        ('ROWBACKGROUNDS', (0,1), (-1,-2), [WHITE, LIGHT_GRAY]),
        ('BACKGROUND', (0,-1), (-1,-1), LIGHT_BLUE),
        ('TOPPADDING', (0,0), (-1,-1), 4),
        ('BOTTOMPADDING', (0,0), (-1,-1), 4),
        ('LEFTPADDING', (0,0), (-1,-1), 5),
    ]))
    story.append(ded_tbl)
    story.append(Spacer(1, 8*mm))

    # ---- Declaration ----
    story.append(Paragraph(
        "I, the undersigned, solemnly declare that to the best of my knowledge and belief, "
        "the information given in this certificate is correct and complete.",
        s['Normal']))
    story.append(Spacer(1, 12*mm))

    sig2 = Table([[
        Paragraph('', s['Normal']),
        Paragraph('Signature & Seal of Employer', s['Center'])
    ]], colWidths=[110*mm, 70*mm])
    sig2.setStyle(TableStyle([
        ('LINEABOVE', (1,0), (1,0), 1, DARK_BLUE),
        ('TOPPADDING', (0,0), (-1,-1), 20),
    ]))
    story.append(sig2)
    story.append(Paragraph(f"Name: {company.get('name', '')}", s['Normal']))
    story.append(Paragraph(f"Place: {company.get('city', 'Prayagraj')}", s['Normal']))
    story.append(Paragraph(f"Date: {datetime.now().strftime('%d/%m/%Y')}", s['Normal']))


# ================================================================
#  MONTHLY PAYROLL SUMMARY  (all employees for a month)
# ================================================================

def generate_payroll_summary(company, month_records, year, month, output_path=None):
    from calculations import MONTH_NAMES
    month_name = MONTH_NAMES[month]

    if output_path is None:
        fname = f"PayrollSummary_{year}_{month:02d}.pdf"
        output_path = os.path.join(OUTPUT_DIR, fname)

    doc = SimpleDocTemplate(output_path, pagesize=A4,
                            leftMargin=10*mm, rightMargin=10*mm,
                            topMargin=15*mm, bottomMargin=15*mm)

    s = _styles()
    story = []

    story.append(_section_header(
        f"{company.get('name','Ram Krishna Enterprises')} — Payroll Summary {month_name} {year}",
        ParagraphStyle('sh', fontSize=11, fontName='Helvetica-Bold', textColor=WHITE, alignment=TA_CENTER)
    ))
    story.append(Spacer(1, 4*mm))

    headers = ['Code', 'Name', 'Gross', 'PF(E)', 'ESI(E)', 'TDS', 'Total Ded.', 'Net Pay']
    h_style = ParagraphStyle('th', fontSize=8, fontName='Helvetica-Bold', textColor=WHITE, alignment=TA_CENTER)
    rows = [[Paragraph(h, h_style) for h in headers]]

    t_gross = t_pf = t_esi = t_tds = t_ded = t_net = 0
    for r in month_records:
        t_gross += r.get('gross_salary', 0)
        t_pf    += r.get('pf_employee', 0)
        t_esi   += r.get('esi_employee', 0)
        t_tds   += r.get('tds', 0)
        t_ded   += r.get('total_deductions', 0)
        t_net   += r.get('net_salary', 0)

        rows.append([
            Paragraph(r.get('emp_code', ''), s['Small']),
            Paragraph(r.get('name', ''), s['Small']),
            Paragraph(f"{r.get('gross_salary',0):,.0f}", ParagraphStyle('sr', fontSize=8, fontName='Helvetica', alignment=TA_RIGHT)),
            Paragraph(f"{r.get('pf_employee',0):,.0f}", ParagraphStyle('sr2', fontSize=8, fontName='Helvetica', alignment=TA_RIGHT)),
            Paragraph(f"{r.get('esi_employee',0):,.0f}", ParagraphStyle('sr3', fontSize=8, fontName='Helvetica', alignment=TA_RIGHT)),
            Paragraph(f"{r.get('tds',0):,.0f}", ParagraphStyle('sr4', fontSize=8, fontName='Helvetica', alignment=TA_RIGHT)),
            Paragraph(f"{r.get('total_deductions',0):,.0f}", ParagraphStyle('sr5', fontSize=8, fontName='Helvetica', alignment=TA_RIGHT)),
            Paragraph(f"{r.get('net_salary',0):,.0f}", ParagraphStyle('sr6', fontSize=8, fontName='Helvetica-Bold', alignment=TA_RIGHT)),
        ])

    b_style = ParagraphStyle('tot', fontSize=8, fontName='Helvetica-Bold')
    br_style = ParagraphStyle('totr', fontSize=8, fontName='Helvetica-Bold', alignment=TA_RIGHT)
    rows.append([
        Paragraph('TOTAL', b_style), Paragraph('', b_style),
        Paragraph(f"{t_gross:,.0f}", br_style), Paragraph(f"{t_pf:,.0f}", br_style),
        Paragraph(f"{t_esi:,.0f}", br_style),   Paragraph(f"{t_tds:,.0f}", br_style),
        Paragraph(f"{t_ded:,.0f}", br_style),   Paragraph(f"{t_net:,.0f}", br_style),
    ])

    col_w = [18*mm, 40*mm, 22*mm, 18*mm, 18*mm, 18*mm, 22*mm, 22*mm]
    tbl = Table(rows, colWidths=col_w, repeatRows=1)
    tbl.setStyle(TableStyle([
        ('GRID', (0,0), (-1,-1), 0.3, colors.HexColor("#CCCCCC")),
        ('BACKGROUND', (0,0), (-1,0), MID_BLUE),
        ('ROWBACKGROUNDS', (0,1), (-1,-2), [WHITE, LIGHT_GRAY]),
        ('BACKGROUND', (0,-1), (-1,-1), LIGHT_BLUE),
        ('FONTNAME', (0,-1), (-1,-1), 'Helvetica-Bold'),
        ('TOPPADDING', (0,0), (-1,-1), 3),
        ('BOTTOMPADDING', (0,0), (-1,-1), 3),
        ('LEFTPADDING', (0,0), (-1,-1), 4),
    ]))
    story.append(tbl)

    doc.build(story)
    return output_path


# ================================================================
#  PF ECR TEXT FILE (EPFO revamped ECR, || delimited, 11 fields)
# ================================================================

def generate_pf_ecr(month_records, employees_by_id, year, month, output_path=None):
    """
    EPFO ECR 2.0 text file for upload on the unified portal.
    Fields: UAN||MEMBER NAME||GROSS WAGES||EPF WAGES||EPS WAGES||EDLI WAGES||
            EPF CONTRI REMITTED||EPS CONTRI REMITTED||EPF EPS DIFF REMITTED||
            NCP DAYS||REFUND OF ADVANCES
    Employees without a UAN are skipped (returned in the second element).
    """
    if output_path is None:
        fname = f"PF_ECR_{year}_{month:02d}.txt"
        output_path = os.path.join(OUTPUT_DIR, fname)

    lines = []
    skipped = []
    for r in month_records:
        emp = employees_by_id.get(r['emp_id'], {})
        uan = str(emp.get('uan', '') or '').strip()
        if not uan or not int(emp.get('pf_applicable', 0)):
            if not uan:
                skipped.append(emp.get('name', f"emp_id {r['emp_id']}"))
            continue

        gross = round(r.get('gross_salary', 0))
        basic_da = round(r.get('basic', 0) + r.get('da', 0))
        epf_wages = basic_da
        eps_wages = min(basic_da, 15000)
        edli_wages = min(basic_da, 15000)
        epf_contri = round(min(basic_da, 15000) * 0.12)
        eps_contri = round(eps_wages * 0.0833)
        diff = epf_contri - eps_contri
        ncp_days = max(0, round((r.get('total_days', 0) or 0) - (r.get('days_worked', 0) or 0)))

        name = str(emp.get('name', '')).upper().strip()
        lines.append(f"{uan}||{name}||{gross}||{epf_wages}||{eps_wages}||{edli_wages}||"
                     f"{epf_contri}||{eps_contri}||{diff}||{ncp_days}||0")

    with open(output_path, 'w', newline='') as f:
        f.write('\n'.join(lines) + '\n')

    return output_path, skipped


# ================================================================
#  ANNUAL PAYROLL REGISTER (one employee, full FY, month-by-month)
# ================================================================

def generate_annual_register(company, employee, annual_records, financial_year, output_path=None):
    from calculations import MONTH_NAMES

    if output_path is None:
        fname = f"AnnualRegister_{employee['emp_code']}_{financial_year}.pdf"
        output_path = os.path.join(OUTPUT_DIR, fname)

    doc = SimpleDocTemplate(output_path, pagesize=A4,
                            leftMargin=10*mm, rightMargin=10*mm,
                            topMargin=15*mm, bottomMargin=15*mm)

    s = _styles()
    story = []

    story.append(_section_header(
        f"{company.get('name','Ram Krishna Enterprises')} — Annual Payroll Register {financial_year}",
        ParagraphStyle('sh', fontSize=11, fontName='Helvetica-Bold', textColor=WHITE, alignment=TA_CENTER)
    ))
    story.append(Spacer(1, 2*mm))
    story.append(_para(f"Employee: {employee.get('name','')} ({employee.get('emp_code','')}) — "
                        f"{employee.get('designation','')}", s['Bold']))
    story.append(Spacer(1, 3*mm))

    headers = ['Month', 'Days', 'Gross', 'PF(E)', 'ESI(E)', 'TDS', 'Total Ded.', 'Net Pay']
    h_style = ParagraphStyle('th2', fontSize=8, fontName='Helvetica-Bold', textColor=WHITE, alignment=TA_CENTER)
    rows = [[Paragraph(h, h_style) for h in headers]]

    r_style = ParagraphStyle('rr2', fontSize=8, fontName='Helvetica', alignment=TA_RIGHT)
    t_gross = t_pf = t_esi = t_tds = t_ded = t_net = 0
    for r in annual_records:
        t_gross += r.get('gross_salary', 0)
        t_pf    += r.get('pf_employee', 0)
        t_esi   += r.get('esi_employee', 0)
        t_tds   += r.get('tds', 0)
        t_ded   += r.get('total_deductions', 0)
        t_net   += r.get('net_salary', 0)

        rows.append([
            Paragraph(MONTH_NAMES[r['month']], s['Small']),
            Paragraph(str(r.get('days_worked', '')), r_style),
            Paragraph(f"{r.get('gross_salary',0):,.0f}", r_style),
            Paragraph(f"{r.get('pf_employee',0):,.0f}", r_style),
            Paragraph(f"{r.get('esi_employee',0):,.0f}", r_style),
            Paragraph(f"{r.get('tds',0):,.0f}", r_style),
            Paragraph(f"{r.get('total_deductions',0):,.0f}", r_style),
            Paragraph(f"{r.get('net_salary',0):,.0f}", ParagraphStyle('rb2', fontSize=8, fontName='Helvetica-Bold', alignment=TA_RIGHT)),
        ])

    b_style = ParagraphStyle('tot2', fontSize=8, fontName='Helvetica-Bold')
    br_style = ParagraphStyle('totr2', fontSize=8, fontName='Helvetica-Bold', alignment=TA_RIGHT)
    rows.append([
        Paragraph('TOTAL', b_style), Paragraph('', b_style),
        Paragraph(f"{t_gross:,.0f}", br_style), Paragraph(f"{t_pf:,.0f}", br_style),
        Paragraph(f"{t_esi:,.0f}", br_style), Paragraph(f"{t_tds:,.0f}", br_style),
        Paragraph(f"{t_ded:,.0f}", br_style), Paragraph(f"{t_net:,.0f}", br_style),
    ])

    col_w = [22*mm, 16*mm, 24*mm, 20*mm, 20*mm, 20*mm, 24*mm, 24*mm]
    tbl = Table(rows, colWidths=col_w, repeatRows=1)
    tbl.setStyle(TableStyle([
        ('GRID', (0,0), (-1,-1), 0.3, colors.HexColor("#CCCCCC")),
        ('BACKGROUND', (0,0), (-1,0), MID_BLUE),
        ('ROWBACKGROUNDS', (0,1), (-1,-2), [WHITE, LIGHT_GRAY]),
        ('BACKGROUND', (0,-1), (-1,-1), LIGHT_BLUE),
        ('FONTNAME', (0,-1), (-1,-1), 'Helvetica-Bold'),
        ('TOPPADDING', (0,0), (-1,-1), 3),
        ('BOTTOMPADDING', (0,0), (-1,-1), 3),
        ('LEFTPADDING', (0,0), (-1,-1), 4),
    ]))
    story.append(tbl)

    doc.build(story)
    return output_path


# ================================================================
#  PF / ESI CONTRIBUTION REPORT (all employees, one month)
# ================================================================

def generate_pf_esi_report(company, month_records, year, month, output_path=None):
    from calculations import MONTH_NAMES
    month_name = MONTH_NAMES[month]

    if output_path is None:
        fname = f"PF_ESI_Report_{year}_{month:02d}.pdf"
        output_path = os.path.join(OUTPUT_DIR, fname)

    doc = SimpleDocTemplate(output_path, pagesize=A4,
                            leftMargin=10*mm, rightMargin=10*mm,
                            topMargin=15*mm, bottomMargin=15*mm)

    s = _styles()
    story = []

    story.append(_section_header(
        f"{company.get('name','Ram Krishna Enterprises')} — PF / ESI Contribution Report {month_name} {year}",
        ParagraphStyle('sh3', fontSize=11, fontName='Helvetica-Bold', textColor=WHITE, alignment=TA_CENTER)
    ))
    story.append(Spacer(1, 4*mm))

    headers = ['Code', 'Name', 'Gross', 'PF(Emp)', 'PF(Empr)', 'ESI(Emp)', 'ESI(Empr)']
    h_style = ParagraphStyle('th3', fontSize=8, fontName='Helvetica-Bold', textColor=WHITE, alignment=TA_CENTER)
    rows = [[Paragraph(h, h_style) for h in headers]]

    r_style = ParagraphStyle('rr3', fontSize=8, fontName='Helvetica', alignment=TA_RIGHT)
    t_gross = t_pf_e = t_pf_er = t_esi_e = t_esi_er = 0
    for r in month_records:
        t_gross += r.get('gross_salary', 0)
        t_pf_e  += r.get('pf_employee', 0)
        t_pf_er += r.get('pf_employer', 0)
        t_esi_e  += r.get('esi_employee', 0)
        t_esi_er += r.get('esi_employer', 0)

        rows.append([
            Paragraph(r.get('emp_code', ''), s['Small']),
            Paragraph(r.get('name', ''), s['Small']),
            Paragraph(f"{r.get('gross_salary',0):,.0f}", r_style),
            Paragraph(f"{r.get('pf_employee',0):,.0f}", r_style),
            Paragraph(f"{r.get('pf_employer',0):,.0f}", r_style),
            Paragraph(f"{r.get('esi_employee',0):,.0f}", r_style),
            Paragraph(f"{r.get('esi_employer',0):,.0f}", r_style),
        ])

    b_style = ParagraphStyle('tot3', fontSize=8, fontName='Helvetica-Bold')
    br_style = ParagraphStyle('totr3', fontSize=8, fontName='Helvetica-Bold', alignment=TA_RIGHT)
    rows.append([
        Paragraph('TOTAL', b_style), Paragraph('', b_style),
        Paragraph(f"{t_gross:,.0f}", br_style),
        Paragraph(f"{t_pf_e:,.0f}", br_style), Paragraph(f"{t_pf_er:,.0f}", br_style),
        Paragraph(f"{t_esi_e:,.0f}", br_style), Paragraph(f"{t_esi_er:,.0f}", br_style),
    ])

    col_w = [22*mm, 45*mm, 26*mm, 26*mm, 26*mm, 26*mm, 26*mm]
    tbl = Table(rows, colWidths=col_w, repeatRows=1)
    tbl.setStyle(TableStyle([
        ('GRID', (0,0), (-1,-1), 0.3, colors.HexColor("#CCCCCC")),
        ('BACKGROUND', (0,0), (-1,0), MID_BLUE),
        ('ROWBACKGROUNDS', (0,1), (-1,-2), [WHITE, LIGHT_GRAY]),
        ('BACKGROUND', (0,-1), (-1,-1), LIGHT_BLUE),
        ('FONTNAME', (0,-1), (-1,-1), 'Helvetica-Bold'),
        ('TOPPADDING', (0,0), (-1,-1), 3),
        ('BOTTOMPADDING', (0,0), (-1,-1), 3),
        ('LEFTPADDING', (0,0), (-1,-1), 4),
    ]))
    story.append(tbl)
    story.append(Spacer(1, 6*mm))

    summary = (f"Total PF Liability (Employee + Employer): Rs. {t_pf_e + t_pf_er:,.2f}<br/>"
               f"Total ESI Liability (Employee + Employer): Rs. {t_esi_e + t_esi_er:,.2f}")
    story.append(_para(summary, s['Bold']))

    doc.build(story)
    return output_path
