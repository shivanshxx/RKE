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

    c.execute("""CREATE TABLE IF NOT EXISTS attendance (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        emp_id INTEGER NOT NULL,
        year INTEGER NOT NULL,
        month INTEGER NOT NULL,
        day INTEGER NOT NULL,
        status TEXT NOT NULL,
        UNIQUE(emp_id, year, month, day),
        FOREIGN KEY (emp_id) REFERENCES employees(id)
    )""")

    c.execute("""CREATE TABLE IF NOT EXISTS salary_history (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        emp_id INTEGER NOT NULL,
        effective_from TEXT NOT NULL,
        basic REAL, hra REAL, da REAL,
        special_allowance REAL, other_allowance REAL,
        note TEXT DEFAULT '',
        FOREIGN KEY (emp_id) REFERENCES employees(id)
    )""")

    # Migration: bonus / one-off earnings column on salary records
    sr_cols = {row['name'] for row in c.execute("PRAGMA table_info(salary_records)").fetchall()}
    if 'additional_earnings' not in sr_cols:
        c.execute("ALTER TABLE salary_records ADD COLUMN additional_earnings REAL DEFAULT 0")

    # Migration: every employee gets a baseline rate-history row so past months
    # always have effective-dated rates to compute from
    c.execute("""INSERT INTO salary_history
                 (emp_id, effective_from, basic, hra, da, special_allowance, other_allowance, note)
                 SELECT id, '2000-01-01', basic, hra, da, special_allowance, other_allowance, 'Baseline'
                 FROM employees
                 WHERE id NOT IN (SELECT DISTINCT emp_id FROM salary_history)""")

    c.execute("""CREATE TABLE IF NOT EXISTS tax_slabs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        regime TEXT NOT NULL,
        fy_start INTEGER NOT NULL,
        min_income REAL NOT NULL,
        max_income REAL,
        rate REAL NOT NULL,
        UNIQUE(regime, fy_start, min_income)
    )""")

    # Seed slabs. FY 2025-26 (Budget 2025) and FY 2026-27 (Income Tax Act 2025 —
    # same slab structure carried forward). Update via SQL when Budget changes rates;
    # no code change or re-release needed.
    new_regime = [(0, 400000, 0.00), (400000, 800000, 0.05), (800000, 1200000, 0.10),
                  (1200000, 1600000, 0.15), (1600000, 2000000, 0.20),
                  (2000000, 2400000, 0.25), (2400000, None, 0.30)]
    old_regime = [(0, 250000, 0.00), (250000, 500000, 0.05),
                  (500000, 1000000, 0.20), (1000000, None, 0.30)]
    for fy in (2025, 2026):
        for lo, hi, rate in new_regime:
            c.execute("""INSERT OR IGNORE INTO tax_slabs (regime, fy_start, min_income, max_income, rate)
                         VALUES ('new', ?, ?, ?, ?)""", (fy, lo, hi, rate))
        for lo, hi, rate in old_regime:
            c.execute("""INSERT OR IGNORE INTO tax_slabs (regime, fy_start, min_income, max_income, rate)
                         VALUES ('old', ?, ?, ?, ?)""", (fy, lo, hi, rate))

    conn.commit()
    conn.close()


def get_tax_slabs(regime, fy_start):
    """Slabs for a regime/FY, falling back to the latest earlier FY that has rows
    (so a new FY keeps working with last year's slabs until updated)."""
    conn = get_conn()
    rows = conn.execute("""SELECT min_income, max_income, rate FROM tax_slabs
                           WHERE regime=? AND fy_start=? ORDER BY min_income""",
                        (regime, fy_start)).fetchall()
    if not rows:
        fallback = conn.execute("""SELECT MAX(fy_start) FROM tax_slabs
                                   WHERE regime=? AND fy_start<?""", (regime, fy_start)).fetchone()[0]
        if fallback:
            rows = conn.execute("""SELECT min_income, max_income, rate FROM tax_slabs
                                   WHERE regime=? AND fy_start=? ORDER BY min_income""",
                                (regime, fallback)).fetchall()
    conn.close()
    return [(r['min_income'], r['max_income'], r['rate']) for r in rows]


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
    cur = conn.execute("""INSERT INTO employees
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
    emp_id = cur.lastrowid
    conn.commit()
    conn.close()
    return emp_id


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
    add_earn = data.get('additional_earnings', 0)
    if existing:
        conn.execute("""UPDATE salary_records SET
            total_days=?, days_worked=?, basic=?, hra=?, da=?, special_allowance=?, other_allowance=?,
            gross_salary=?, pf_employee=?, esi_employee=?, tds=?, pt=?, other_deductions=?,
            total_deductions=?, net_salary=?, pf_employer=?, esi_employer=?,
            payment_mode=?, remarks=?, generated_on=?, additional_earnings=?
            WHERE emp_id=? AND year=? AND month=?""",
                     (data['total_days'], data['days_worked'], data['basic'], data['hra'],
                      data['da'], data['special_allowance'], data['other_allowance'],
                      data['gross_salary'], data['pf_employee'], data['esi_employee'],
                      data['tds'], data['pt'], data['other_deductions'],
                      data['total_deductions'], data['net_salary'],
                      data['pf_employer'], data['esi_employer'],
                      data['payment_mode'], data['remarks'], data['generated_on'], add_earn,
                      data['emp_id'], data['year'], data['month']))
    else:
        conn.execute("""INSERT INTO salary_records
            (emp_id, year, month, total_days, days_worked, basic, hra, da, special_allowance,
             other_allowance, gross_salary, pf_employee, esi_employee, tds, pt, other_deductions,
             total_deductions, net_salary, pf_employer, esi_employer, payment_mode, remarks,
             generated_on, additional_earnings)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                     (data['emp_id'], data['year'], data['month'],
                      data['total_days'], data['days_worked'], data['basic'], data['hra'],
                      data['da'], data['special_allowance'], data['other_allowance'],
                      data['gross_salary'], data['pf_employee'], data['esi_employee'],
                      data['tds'], data['pt'], data['other_deductions'],
                      data['total_deductions'], data['net_salary'],
                      data['pf_employer'], data['esi_employer'],
                      data['payment_mode'], data['remarks'], data['generated_on'], add_earn))
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


# ---------- Attendance ----------

def get_attendance(year, month):
    """{emp_id: {day: status}} for a month. Only exceptions are stored;
    an unmarked day counts as Present."""
    conn = get_conn()
    rows = conn.execute("SELECT emp_id, day, status FROM attendance WHERE year=? AND month=?",
                        (year, month)).fetchall()
    conn.close()
    out = {}
    for r in rows:
        out.setdefault(r['emp_id'], {})[r['day']] = r['status']
    return out


def save_attendance(year, month, marks):
    """marks: {emp_id: {day: status}} — replaces the month's records."""
    conn = get_conn()
    conn.execute("DELETE FROM attendance WHERE year=? AND month=?", (year, month))
    for emp_id, days in marks.items():
        for day, status in days.items():
            conn.execute("INSERT INTO attendance (emp_id, year, month, day, status) VALUES (?,?,?,?,?)",
                         (emp_id, year, month, day, status))
    conn.commit()
    conn.close()


def attendance_days_worked(emp_id, year, month, total_days):
    """Days worked from attendance marks: total days minus absences,
    half-days count 0.5. Returns None if nothing is marked for this employee."""
    conn = get_conn()
    rows = conn.execute("SELECT status FROM attendance WHERE emp_id=? AND year=? AND month=?",
                        (emp_id, year, month)).fetchall()
    conn.close()
    if not rows:
        return None
    absent = sum(1 for r in rows if r['status'] == 'A')
    half = sum(1 for r in rows if r['status'] == 'H')
    return max(0.0, total_days - absent - 0.5 * half)


# ---------- Salary history ----------

RATE_FIELDS = ('basic', 'hra', 'da', 'special_allowance', 'other_allowance')


def record_salary_revision(emp_id, data, note=''):
    """Store a pay-revision snapshot if rates differ from the latest one."""
    conn = get_conn()
    last = conn.execute("""SELECT basic, hra, da, special_allowance, other_allowance
                           FROM salary_history WHERE emp_id=? ORDER BY id DESC LIMIT 1""",
                        (emp_id,)).fetchone()
    changed = last is None or any(abs((last[f] or 0) - float(data[f] or 0)) > 0.005 for f in RATE_FIELDS)
    if changed:
        # First-ever row is the baseline: effective from the beginning, so months
        # before today still have rates to compute from. Later revisions apply
        # from today onward — past months keep their old rates.
        effective = '2000-01-01' if last is None else datetime.now().strftime('%Y-%m-%d')
        conn.execute("""INSERT INTO salary_history
            (emp_id, effective_from, basic, hra, da, special_allowance, other_allowance, note)
            VALUES (?,?,?,?,?,?,?,?)""",
            (emp_id, effective,
             data['basic'], data['hra'], data['da'],
             data['special_allowance'], data['other_allowance'], note))
        conn.commit()
    conn.close()


def get_rates_for_month(emp_id, year, month):
    """Pay rates in effect for a given month (effective-dated): the latest
    revision whose effective_from is on or before the end of that month.
    Revising DA/basic today therefore never changes past months' salaries."""
    month_end = f"{year:04d}-{month:02d}-31"
    conn = get_conn()
    row = conn.execute("""SELECT basic, hra, da, special_allowance, other_allowance
                          FROM salary_history
                          WHERE emp_id=? AND effective_from <= ?
                          ORDER BY effective_from DESC, id DESC LIMIT 1""",
                       (emp_id, month_end)).fetchone()
    conn.close()
    if row:
        return dict(row)
    emp = get_employee(emp_id)
    return {f: emp[f] for f in RATE_FIELDS} if emp else None


def get_salary_history(emp_id):
    conn = get_conn()
    rows = conn.execute("SELECT * FROM salary_history WHERE emp_id=? ORDER BY id DESC", (emp_id,)).fetchall()
    conn.close()
    return [dict(r) for r in rows]


# ---------- Backup / Restore ----------

def backup_db(dest_dir):
    """Consistent snapshot of the database (uses SQLite's online backup API,
    safe even while the app is running). Returns the backup file path."""
    ts = datetime.now().strftime('%Y%m%d_%H%M%S')
    dest = os.path.join(dest_dir, f"rke_payroll_backup_{ts}.db")
    src = sqlite3.connect(DB_PATH)
    dst = sqlite3.connect(dest)
    with dst:
        src.backup(dst)
    dst.close()
    src.close()
    return dest


def restore_db(backup_path):
    """Replace the live database with a backup. A safety copy of the current
    DB is made first. Caller must restart the app afterwards."""
    con = sqlite3.connect(backup_path)
    try:
        ok = con.execute("PRAGMA integrity_check").fetchone()[0] == 'ok'
        has_tables = con.execute(
            "SELECT COUNT(*) FROM sqlite_master WHERE name IN ('company','employees','salary_records')"
        ).fetchone()[0] == 3
    finally:
        con.close()
    if not (ok and has_tables):
        raise ValueError("Not a valid RKE payroll backup file.")

    ts = datetime.now().strftime('%Y%m%d_%H%M%S')
    safety = os.path.join(BASE_DIR, f"pre_restore_{ts}.db")
    import shutil
    if os.path.exists(DB_PATH):
        shutil.copy2(DB_PATH, safety)
    shutil.copy2(backup_path, DB_PATH)
    return safety


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
