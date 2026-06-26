import sqlite3
import os
import sys
import hashlib
import secrets
from datetime import datetime

# In a PyInstaller --onefile build, __file__ resolves inside a temp extraction
# folder that's wiped after each run. Use the .exe's own folder instead so the
# database persists across runs.
if getattr(sys, 'frozen', False):
    BASE_DIR = os.path.dirname(os.path.abspath(sys.executable))
else:
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))

DB_PATH = os.path.join(BASE_DIR, "rke_payroll.db")


def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db():
    conn = get_conn()
    c = conn.cursor()

    c.execute("""CREATE TABLE IF NOT EXISTS company (
        id INTEGER PRIMARY KEY,
        name TEXT DEFAULT 'Ram Krishna Enterprises',
        address TEXT DEFAULT 'Prayagraj, Uttar Pradesh',
        pan TEXT DEFAULT '',
        tan TEXT DEFAULT '',
        pf_reg TEXT DEFAULT '',
        esi_reg TEXT DEFAULT '',
        city TEXT DEFAULT 'Prayagraj',
        state TEXT DEFAULT 'Uttar Pradesh',
        pincode TEXT DEFAULT '',
        phone TEXT DEFAULT '',
        email TEXT DEFAULT '',
        financial_year TEXT DEFAULT '2025-26'
    )""")

    c.execute("SELECT COUNT(*) FROM company")
    if c.fetchone()[0] == 0:
        c.execute("""INSERT INTO company (name, city, state)
                     VALUES ('Ram Krishna Enterprises', 'Prayagraj', 'Uttar Pradesh')""")

    # Migration: add password columns if they don't exist yet (older databases)
    existing_cols = {row['name'] for row in c.execute("PRAGMA table_info(company)").fetchall()}
    if 'password_hash' not in existing_cols:
        c.execute("ALTER TABLE company ADD COLUMN password_hash TEXT DEFAULT ''")
    if 'password_salt' not in existing_cols:
        c.execute("ALTER TABLE company ADD COLUMN password_salt TEXT DEFAULT ''")

    c.execute("""CREATE TABLE IF NOT EXISTS employees (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        emp_code TEXT UNIQUE NOT NULL,
        name TEXT NOT NULL,
        father_name TEXT DEFAULT '',
        dob TEXT DEFAULT '',
        doj TEXT DEFAULT '',
        designation TEXT DEFAULT '',
        department TEXT DEFAULT '',
        gender TEXT DEFAULT 'Male',
        pan TEXT DEFAULT '',
        aadhaar TEXT DEFAULT '',
        bank_name TEXT DEFAULT '',
        bank_account TEXT DEFAULT '',
        ifsc TEXT DEFAULT '',
        pf_number TEXT DEFAULT '',
        esi_number TEXT DEFAULT '',
        uan TEXT DEFAULT '',
        basic REAL DEFAULT 0,
        hra REAL DEFAULT 0,
        da REAL DEFAULT 0,
        special_allowance REAL DEFAULT 0,
        other_allowance REAL DEFAULT 0,
        pf_applicable INTEGER DEFAULT 1,
        esi_applicable INTEGER DEFAULT 1,
        tds_applicable INTEGER DEFAULT 0,
        tax_regime TEXT DEFAULT 'new',
        status TEXT DEFAULT 'Active'
    )""")

    c.execute("""CREATE TABLE IF NOT EXISTS salary_records (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        emp_id INTEGER NOT NULL,
        year INTEGER NOT NULL,
        month INTEGER NOT NULL,
        total_days INTEGER DEFAULT 26,
        days_worked REAL DEFAULT 26,
        basic REAL DEFAULT 0,
        hra REAL DEFAULT 0,
        da REAL DEFAULT 0,
        special_allowance REAL DEFAULT 0,
        other_allowance REAL DEFAULT 0,
        gross_salary REAL DEFAULT 0,
        pf_employee REAL DEFAULT 0,
        esi_employee REAL DEFAULT 0,
        tds REAL DEFAULT 0,
        pt REAL DEFAULT 0,
        other_deductions REAL DEFAULT 0,
        total_deductions REAL DEFAULT 0,
        net_salary REAL DEFAULT 0,
        pf_employer REAL DEFAULT 0,
        esi_employer REAL DEFAULT 0,
        payment_mode TEXT DEFAULT 'Bank Transfer',
        remarks TEXT DEFAULT '',
        generated_on TEXT,
        FOREIGN KEY (emp_id) REFERENCES employees(id),
        UNIQUE(emp_id, year, month)
    )""")

    conn.commit()
    conn.close()


# ---------- Company ----------

def get_company():
    conn = get_conn()
    row = conn.execute("SELECT * FROM company WHERE id=1").fetchone()
    conn.close()
    return dict(row) if row else {}


def save_company(data):
    conn = get_conn()
    conn.execute("""UPDATE company SET name=?, address=?, pan=?, tan=?, pf_reg=?, esi_reg=?,
                    city=?, state=?, pincode=?, phone=?, email=?, financial_year=? WHERE id=1""",
                 (data['name'], data['address'], data['pan'], data['tan'], data['pf_reg'],
                  data['esi_reg'], data['city'], data['state'], data['pincode'],
                  data['phone'], data['email'], data['financial_year']))
    conn.commit()
    conn.close()


# ---------- Employees ----------

def get_all_employees(status='Active'):
    conn = get_conn()
    rows = conn.execute("SELECT * FROM employees WHERE status=? ORDER BY emp_code", (status,)).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_employee(emp_id):
    conn = get_conn()
    row = conn.execute("SELECT * FROM employees WHERE id=?", (emp_id,)).fetchone()
    conn.close()
    return dict(row) if row else None


def add_employee(data):
    conn = get_conn()
    conn.execute("""INSERT INTO employees
        (emp_code, name, father_name, dob, doj, designation, department, gender,
         pan, aadhaar, bank_name, bank_account, ifsc, pf_number, esi_number, uan,
         basic, hra, da, special_allowance, other_allowance,
         pf_applicable, esi_applicable, tds_applicable, tax_regime, status)
        VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                 (data['emp_code'], data['name'], data['father_name'], data['dob'],
                  data['doj'], data['designation'], data['department'], data['gender'],
                  data['pan'], data['aadhaar'], data['bank_name'], data['bank_account'],
                  data['ifsc'], data['pf_number'], data['esi_number'], data['uan'],
                  data['basic'], data['hra'], data['da'],
                  data['special_allowance'], data['other_allowance'],
                  data['pf_applicable'], data['esi_applicable'], data['tds_applicable'],
                  data['tax_regime'], data['status']))
    conn.commit()
    conn.close()


def update_employee(emp_id, data):
    conn = get_conn()
    conn.execute("""UPDATE employees SET
        emp_code=?, name=?, father_name=?, dob=?, doj=?, designation=?, department=?, gender=?,
        pan=?, aadhaar=?, bank_name=?, bank_account=?, ifsc=?, pf_number=?, esi_number=?, uan=?,
        basic=?, hra=?, da=?, special_allowance=?, other_allowance=?,
        pf_applicable=?, esi_applicable=?, tds_applicable=?, tax_regime=?, status=?
        WHERE id=?""",
                 (data['emp_code'], data['name'], data['father_name'], data['dob'],
                  data['doj'], data['designation'], data['department'], data['gender'],
                  data['pan'], data['aadhaar'], data['bank_name'], data['bank_account'],
                  data['ifsc'], data['pf_number'], data['esi_number'], data['uan'],
                  data['basic'], data['hra'], data['da'],
                  data['special_allowance'], data['other_allowance'],
                  data['pf_applicable'], data['esi_applicable'], data['tds_applicable'],
                  data['tax_regime'], data['status'], emp_id))
    conn.commit()
    conn.close()


def delete_employee(emp_id):
    conn = get_conn()
    conn.execute("UPDATE employees SET status='Inactive' WHERE id=?", (emp_id,))
    conn.commit()
    conn.close()


def emp_code_exists(code, exclude_id=None):
    conn = get_conn()
    if exclude_id:
        row = conn.execute("SELECT id FROM employees WHERE emp_code=? AND id!=?", (code, exclude_id)).fetchone()
    else:
        row = conn.execute("SELECT id FROM employees WHERE emp_code=?", (code,)).fetchone()
    conn.close()
    return row is not None


# ---------- Salary Records ----------

def get_salary_record(emp_id, year, month):
    conn = get_conn()
    row = conn.execute("SELECT * FROM salary_records WHERE emp_id=? AND year=? AND month=?",
                       (emp_id, year, month)).fetchone()
    conn.close()
    return dict(row) if row else None


def save_salary_record(data):
    conn = get_conn()
    existing = conn.execute("SELECT id FROM salary_records WHERE emp_id=? AND year=? AND month=?",
                            (data['emp_id'], data['year'], data['month'])).fetchone()
    if existing:
        conn.execute("""UPDATE salary_records SET
            total_days=?, days_worked=?, basic=?, hra=?, da=?, special_allowance=?, other_allowance=?,
            gross_salary=?, pf_employee=?, esi_employee=?, tds=?, pt=?, other_deductions=?,
            total_deductions=?, net_salary=?, pf_employer=?, esi_employer=?,
            payment_mode=?, remarks=?, generated_on=?
            WHERE emp_id=? AND year=? AND month=?""",
                     (data['total_days'], data['days_worked'], data['basic'], data['hra'],
                      data['da'], data['special_allowance'], data['other_allowance'],
                      data['gross_salary'], data['pf_employee'], data['esi_employee'],
                      data['tds'], data['pt'], data['other_deductions'],
                      data['total_deductions'], data['net_salary'],
                      data['pf_employer'], data['esi_employer'],
                      data['payment_mode'], data['remarks'], data['generated_on'],
                      data['emp_id'], data['year'], data['month']))
    else:
        conn.execute("""INSERT INTO salary_records
            (emp_id, year, month, total_days, days_worked, basic, hra, da, special_allowance,
             other_allowance, gross_salary, pf_employee, esi_employee, tds, pt, other_deductions,
             total_deductions, net_salary, pf_employer, esi_employer, payment_mode, remarks, generated_on)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                     (data['emp_id'], data['year'], data['month'],
                      data['total_days'], data['days_worked'], data['basic'], data['hra'],
                      data['da'], data['special_allowance'], data['other_allowance'],
                      data['gross_salary'], data['pf_employee'], data['esi_employee'],
                      data['tds'], data['pt'], data['other_deductions'],
                      data['total_deductions'], data['net_salary'],
                      data['pf_employer'], data['esi_employer'],
                      data['payment_mode'], data['remarks'], data['generated_on']))
    conn.commit()
    conn.close()


def get_monthly_salaries(year, month):
    conn = get_conn()
    rows = conn.execute("""
        SELECT sr.*, e.name, e.emp_code, e.designation, e.department
        FROM salary_records sr
        JOIN employees e ON sr.emp_id = e.id
        WHERE sr.year=? AND sr.month=?
        ORDER BY e.emp_code""", (year, month)).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_annual_salary_records(emp_id, year):
    conn = get_conn()
    rows = conn.execute("""SELECT * FROM salary_records WHERE emp_id=? AND year=? ORDER BY month""",
                        (emp_id, year)).fetchall()
    conn.close()
    return [dict(r) for r in rows]


# ---------- Password / Login ----------

def _hash_password(plain, salt):
    return hashlib.pbkdf2_hmac('sha256', plain.encode('utf-8'), salt.encode('utf-8'), 200_000).hex()


def has_password():
    conn = get_conn()
    row = conn.execute("SELECT password_hash FROM company WHERE id=1").fetchone()
    conn.close()
    return bool(row and row['password_hash'])


def set_password(plain):
    salt = secrets.token_hex(16)
    pwd_hash = _hash_password(plain, salt)
    conn = get_conn()
    conn.execute("UPDATE company SET password_hash=?, password_salt=? WHERE id=1", (pwd_hash, salt))
    conn.commit()
    conn.close()


def clear_password():
    conn = get_conn()
    conn.execute("UPDATE company SET password_hash='', password_salt='' WHERE id=1")
    conn.commit()
    conn.close()


def verify_password(plain):
    conn = get_conn()
    row = conn.execute("SELECT password_hash, password_salt FROM company WHERE id=1").fetchone()
    conn.close()
    if not row or not row['password_hash']:
        return True  # no password set — open access
    return _hash_password(plain, row['password_salt']) == row['password_hash']


def get_ytd_totals(emp_id, year, month):
    """Sum gross_salary and tds for an employee's current FY (Apr-Mar) up to but
    excluding the given (year, month) — used to true-up monthly TDS."""
    if month >= 4:
        fy_start_year = year
    else:
        fy_start_year = year - 1

    conn = get_conn()
    rows = conn.execute("""SELECT year, month, gross_salary, tds FROM salary_records
                          WHERE emp_id=? AND
                          ((year=? AND month>=4) OR (year=? AND month<4))""",
                        (emp_id, fy_start_year, fy_start_year + 1)).fetchall()
    conn.close()

    ytd_gross = ytd_tds = 0.0
    for r in rows:
        if (r['year'], r['month']) < (year, month):
            ytd_gross += r['gross_salary'] or 0
            ytd_tds += r['tds'] or 0
    return ytd_gross, ytd_tds


def get_dashboard_stats():
    conn = get_conn()
    emp_count = conn.execute("SELECT COUNT(*) FROM employees WHERE status='Active'").fetchone()[0]
    now = datetime.now()
    month_total = conn.execute("""SELECT COALESCE(SUM(net_salary),0) FROM salary_records
                                   WHERE year=? AND month=?""", (now.year, now.month)).fetchone()[0]
    month_count = conn.execute("""SELECT COUNT(*) FROM salary_records
                                   WHERE year=? AND month=?""", (now.year, now.month)).fetchone()[0]
    conn.close()
    return {'emp_count': emp_count, 'month_total': month_total, 'month_count': month_count}
