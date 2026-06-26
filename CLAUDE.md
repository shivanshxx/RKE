# EMS — Employee Management System
## Master Build Brief for Claude Code

This is a complete offline Employee Management System for an Indian MSME (5–30 employees).
Read every section before writing a single line of code.

---

## CONSTRAINTS (Non-negotiable)

- Fully offline. No network calls. No cloud. No external APIs.
- Single machine deployment. Runs on Windows laptop via double-click.
- SQLite database — one file: `data/ems.db`
- GUI: PyQt6
- PDF: ReportLab
- Excel: openpyxl
- Word (.docx): python-docx
- Plain text exports: Python stdlib only
- Packaged via PyInstaller into a single `.exe`
- Git + GitHub for source code only. `data/` is ALWAYS gitignored. Never commit `.db` files.

---

## FOLDER STRUCTURE

Create this exact structure:

```
ems/
    main.py                         # Entry point — launches PyQt6 app
    requirements.txt
    README.md
    .gitignore
    build.spec                      # PyInstaller spec

    core/
        __init__.py
        database.py                 # SQLite connection, schema init, WAL mode
        models.py                   # Dataclasses for all entities
        settings.py                 # App config (paths, company state)

    modules/
        __init__.py
        employees.py                # Employee CRUD logic
        attendance.py               # Attendance + leave logic
        payroll.py                  # Payroll computation engine
        compliance.py               # PF/ESIC/PT/TDS calculators
        documents.py                # Document generation dispatcher

    generators/
        __init__.py
        payslip_pdf.py              # ReportLab payslip
        form16_pdf.py               # ReportLab Form 16
        offer_letter_docx.py        # python-docx
        appointment_docx.py
        experience_docx.py
        payroll_excel.py            # openpyxl payroll register
        attendance_excel.py
        pf_ecr_txt.py               # Plain text PF ECR file (EPFO format)
        esic_excel.py
        tds_excel.py

    ui/
        __init__.py
        main_window.py              # Main window, sidebar navigation
        dashboard_ui.py
        employees_ui.py
        attendance_ui.py
        payroll_ui.py
        compliance_ui.py
        reports_ui.py
        documents_ui.py
        settings_ui.py
        backup_ui.py
        widgets.py                  # Reusable custom widgets

    assets/
        logo.png                    # Placeholder company logo
        fonts/                      # Any custom fonts

    data/                           # GITIGNORED — never committed
        ems.db
        documents/
            payslips/
            form16/
            letters/
        backups/
```

---

## REQUIREMENTS.TXT

```
PyQt6==6.7.0
reportlab==4.1.0
openpyxl==3.1.2
python-docx==1.1.0
Pillow==10.3.0
```

---

## .GITIGNORE

```
data/
*.db
__pycache__/
*.pyc
*.pyo
dist/
build/
*.spec.bak
.env
```

---

## DATABASE SCHEMA

File: `core/database.py`

On first run, create all tables. Enable WAL mode on every connection.

```python
PRAGMA journal_mode=WAL;
PRAGMA foreign_keys=ON;
```

### Tables (create in this order due to FK dependencies):

#### company
```sql
CREATE TABLE IF NOT EXISTS company (
    id INTEGER PRIMARY KEY DEFAULT 1,
    name TEXT NOT NULL DEFAULT '',
    trade_name TEXT DEFAULT '',
    pan TEXT DEFAULT '',
    gstin TEXT DEFAULT '',
    address TEXT DEFAULT '',
    city TEXT DEFAULT '',
    state TEXT NOT NULL DEFAULT 'Maharashtra',
    pincode TEXT DEFAULT '',
    phone TEXT DEFAULT '',
    email TEXT DEFAULT '',
    pf_registration TEXT DEFAULT '',
    esic_registration TEXT DEFAULT '',
    pt_registration TEXT DEFAULT '',
    logo_path TEXT DEFAULT '',
    fy_start_month INTEGER DEFAULT 4
);
INSERT OR IGNORE INTO company (id) VALUES (1);
```

#### departments
```sql
CREATE TABLE IF NOT EXISTS departments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE,
    is_active INTEGER DEFAULT 1
);
```

#### designations
```sql
CREATE TABLE IF NOT EXISTS designations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    department_id INTEGER REFERENCES departments(id),
    is_active INTEGER DEFAULT 1
);
```

#### employees
```sql
CREATE TABLE IF NOT EXISTS employees (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    employee_code TEXT NOT NULL UNIQUE,
    first_name TEXT NOT NULL,
    last_name TEXT NOT NULL DEFAULT '',
    dob TEXT,
    gender TEXT DEFAULT 'M',
    personal_email TEXT DEFAULT '',
    official_email TEXT DEFAULT '',
    phone TEXT DEFAULT '',
    emergency_contact_name TEXT DEFAULT '',
    emergency_contact_phone TEXT DEFAULT '',
    address TEXT DEFAULT '',
    city TEXT DEFAULT '',
    state TEXT DEFAULT '',
    pincode TEXT DEFAULT '',
    joining_date TEXT NOT NULL,
    probation_days INTEGER DEFAULT 90,
    confirmation_date TEXT,
    department_id INTEGER REFERENCES departments(id),
    designation_id INTEGER REFERENCES designations(id),
    employment_type TEXT DEFAULT 'full_time',
    status TEXT DEFAULT 'active',
    notice_date TEXT,
    last_working_date TEXT,
    manager_id INTEGER REFERENCES employees(id),
    uan TEXT DEFAULT '',
    esic_ip TEXT DEFAULT '',
    pan TEXT DEFAULT '',
    aadhaar_last4 TEXT DEFAULT '',
    bank_name TEXT DEFAULT '',
    bank_account TEXT DEFAULT '',
    bank_ifsc TEXT DEFAULT '',
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT DEFAULT CURRENT_TIMESTAMP
);
```

#### salary_structures
```sql
CREATE TABLE IF NOT EXISTS salary_structures (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    employee_id INTEGER NOT NULL REFERENCES employees(id),
    effective_from TEXT NOT NULL,
    ctc_annual REAL NOT NULL,
    basic_pct REAL DEFAULT 40.0,
    hra_pct REAL DEFAULT 20.0,
    special_allowance REAL DEFAULT 0,
    other_allowance REAL DEFAULT 0,
    pf_applicable INTEGER DEFAULT 1,
    esic_applicable INTEGER DEFAULT 1,
    pt_applicable INTEGER DEFAULT 1,
    tds_regime TEXT DEFAULT 'new',
    variable_monthly REAL DEFAULT 0,
    is_current INTEGER DEFAULT 1
);
```

#### leave_types
```sql
CREATE TABLE IF NOT EXISTS leave_types (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    code TEXT NOT NULL UNIQUE,
    name TEXT NOT NULL,
    max_days_per_year INTEGER,
    carry_forward INTEGER DEFAULT 0,
    carry_forward_max INTEGER DEFAULT 0,
    is_paid INTEGER DEFAULT 1,
    gender_specific TEXT
);
INSERT OR IGNORE INTO leave_types (code, name, max_days_per_year, carry_forward, carry_forward_max, is_paid) VALUES
    ('CL',   'Casual Leave',        12, 0, 0, 1),
    ('EL',   'Earned Leave',        15, 1, 30, 1),
    ('SL',   'Sick Leave',          7,  0, 0, 1),
    ('COMP', 'Compensatory Off',    NULL, 0, 0, 1),
    ('LWP',  'Leave Without Pay',   NULL, 0, 0, 0),
    ('MAT',  'Maternity Leave',     182, 0, 0, 1),
    ('PAT',  'Paternity Leave',     15,  0, 0, 1);
```

#### leave_balances
```sql
CREATE TABLE IF NOT EXISTS leave_balances (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    employee_id INTEGER NOT NULL REFERENCES employees(id),
    leave_type_id INTEGER NOT NULL REFERENCES leave_types(id),
    year INTEGER NOT NULL,
    allocated REAL DEFAULT 0,
    used REAL DEFAULT 0,
    carried_forward REAL DEFAULT 0,
    UNIQUE(employee_id, leave_type_id, year)
);
```

#### leave_applications
```sql
CREATE TABLE IF NOT EXISTS leave_applications (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    employee_id INTEGER NOT NULL REFERENCES employees(id),
    leave_type_id INTEGER NOT NULL REFERENCES leave_types(id),
    from_date TEXT NOT NULL,
    to_date TEXT NOT NULL,
    days REAL NOT NULL,
    reason TEXT DEFAULT '',
    status TEXT DEFAULT 'pending',
    applied_at TEXT DEFAULT CURRENT_TIMESTAMP,
    actioned_at TEXT,
    remarks TEXT DEFAULT ''
);
```

#### attendance
```sql
CREATE TABLE IF NOT EXISTS attendance (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    employee_id INTEGER NOT NULL REFERENCES employees(id),
    date TEXT NOT NULL,
    status TEXT NOT NULL,
    check_in TEXT DEFAULT '',
    check_out TEXT DEFAULT '',
    remarks TEXT DEFAULT '',
    UNIQUE(employee_id, date)
);
```

#### holidays
```sql
CREATE TABLE IF NOT EXISTS holidays (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    date TEXT NOT NULL UNIQUE,
    name TEXT NOT NULL,
    type TEXT DEFAULT 'national'
);
```

#### pt_slabs (state-wise PT slabs — never hardcode)
```sql
CREATE TABLE IF NOT EXISTS pt_slabs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    state TEXT NOT NULL,
    effective_fy INTEGER NOT NULL,
    min_gross REAL NOT NULL,
    max_gross REAL,
    monthly_pt REAL NOT NULL,
    february_pt REAL,
    UNIQUE(state, effective_fy, min_gross)
);
-- Seed Maharashtra slabs (FY 2024)
INSERT OR IGNORE INTO pt_slabs (state, effective_fy, min_gross, max_gross, monthly_pt, february_pt) VALUES
    ('Maharashtra', 2024, 0,     7500,  0,   0),
    ('Maharashtra', 2024, 7501,  10000, 175, 175),
    ('Maharashtra', 2024, 10001, NULL,  200, 300);
-- Karnataka
INSERT OR IGNORE INTO pt_slabs (state, effective_fy, min_gross, max_gross, monthly_pt) VALUES
    ('Karnataka', 2024, 0,     14999, 0),
    ('Karnataka', 2024, 15000, NULL,  200);
-- Others states: UP, Delhi, Rajasthan have no PT
INSERT OR IGNORE INTO pt_slabs (state, effective_fy, min_gross, max_gross, monthly_pt) VALUES
    ('Uttar Pradesh', 2024, 0, NULL, 0),
    ('Delhi',         2024, 0, NULL, 0),
    ('Rajasthan',     2024, 0, NULL, 0);
```

#### tax_slabs (TDS slabs — never hardcode)
```sql
CREATE TABLE IF NOT EXISTS tax_slabs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    regime TEXT NOT NULL,
    effective_fy INTEGER NOT NULL,
    min_income REAL NOT NULL,
    max_income REAL,
    rate REAL NOT NULL,
    UNIQUE(regime, effective_fy, min_income)
);
-- New regime FY 2025-26 (Budget 2025)
INSERT OR IGNORE INTO tax_slabs (regime, effective_fy, min_income, max_income, rate) VALUES
    ('new', 2025, 0,        400000,  0.00),
    ('new', 2025, 400001,   800000,  0.05),
    ('new', 2025, 800001,   1200000, 0.10),
    ('new', 2025, 1200001,  1600000, 0.15),
    ('new', 2025, 1600001,  2000000, 0.20),
    ('new', 2025, 2000001,  2400000, 0.25),
    ('new', 2025, 2400001,  NULL,    0.30);
-- Old regime FY 2025-26
INSERT OR IGNORE INTO tax_slabs (regime, effective_fy, min_income, max_income, rate) VALUES
    ('old', 2025, 0,       250000,  0.00),
    ('old', 2025, 250001,  500000,  0.05),
    ('old', 2025, 500001,  1000000, 0.20),
    ('old', 2025, 1000001, NULL,    0.30);
```

#### payroll_runs
```sql
CREATE TABLE IF NOT EXISTS payroll_runs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    month INTEGER NOT NULL,
    year INTEGER NOT NULL,
    status TEXT DEFAULT 'draft',
    processed_at TEXT,
    approved_at TEXT,
    total_gross REAL DEFAULT 0,
    total_deductions REAL DEFAULT 0,
    total_net REAL DEFAULT 0,
    notes TEXT DEFAULT '',
    UNIQUE(month, year)
);
```

#### payroll_details
```sql
CREATE TABLE IF NOT EXISTS payroll_details (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id INTEGER NOT NULL REFERENCES payroll_runs(id),
    employee_id INTEGER NOT NULL REFERENCES employees(id),
    working_days INTEGER NOT NULL,
    present_days REAL NOT NULL,
    lop_days REAL DEFAULT 0,
    gross_salary REAL NOT NULL,
    basic REAL DEFAULT 0,
    hra REAL DEFAULT 0,
    special_allowance REAL DEFAULT 0,
    other_allowance REAL DEFAULT 0,
    pf_employee REAL DEFAULT 0,
    pf_employer REAL DEFAULT 0,
    esic_employee REAL DEFAULT 0,
    esic_employer REAL DEFAULT 0,
    pt REAL DEFAULT 0,
    tds REAL DEFAULT 0,
    total_deductions REAL DEFAULT 0,
    net_salary REAL NOT NULL,
    payslip_path TEXT DEFAULT '',
    UNIQUE(run_id, employee_id)
);
```

#### audit_log
```sql
CREATE TABLE IF NOT EXISTS audit_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    entity_type TEXT NOT NULL,
    entity_id INTEGER NOT NULL,
    action TEXT NOT NULL,
    old_value TEXT,
    new_value TEXT,
    changed_at TEXT DEFAULT CURRENT_TIMESTAMP,
    changed_by TEXT DEFAULT 'owner'
);
```

---

## PAYROLL COMPUTATION ENGINE

File: `modules/payroll.py`

Implement this exact logic. All monetary values rounded to 2 decimal places.
Use Python `decimal.Decimal` for TDS computation.

### Component Computation

```python
monthly_ctc = ctc_annual / 12
basic = round(monthly_ctc * basic_pct / 100, 2)
hra = round(basic * hra_pct / 100, 2)
# special_allowance = balancing component
special_allowance = round(monthly_ctc - basic - hra - other_allowance - pf_employer - esic_employer, 2)
gross_salary = basic + hra + special_allowance + other_allowance
```

### LOP (Loss of Pay)

```python
# working_days = total days in month minus all Sundays minus company holidays
# present_days = P + (0.5 * HD) + approved_paid_leaves
lop_days = max(0, working_days - present_days)
lop_amount = round((gross_salary / working_days) * lop_days, 2)
lop_adjusted_gross = round(gross_salary - lop_amount, 2)
```

### PF Computation

```python
if pf_applicable:
    pf_wage = min(basic, 15000)  # wage ceiling
    pf_employee = round(pf_wage * 0.12, 2)
    pf_employer_epf = round(pf_wage * 0.0367, 2)
    pf_employer_eps = round(pf_wage * 0.0833, 2)
    pf_employer = round(pf_wage * 0.12, 2)
else:
    pf_employee = pf_employer = 0
```

### ESIC Computation

```python
if gross_salary <= 21000 and esic_applicable:
    esic_employee = round(gross_salary * 0.0075, 0)
    esic_employer = round(gross_salary * 0.0325, 0)
else:
    esic_employee = esic_employer = 0
```

### PT Computation

```python
# Fetch slabs from pt_slabs table for company state and current FY
# FY = April to March; current FY = year if month >= April else year - 1
# February: use february_pt column if not null
def compute_pt(gross, state, month, fy, db_conn):
    slabs = fetch_pt_slabs(state, fy, db_conn)
    for slab in sorted(slabs, key=lambda x: x.min_gross):
        if slab.max_gross is None or gross <= slab.max_gross:
            if month == 2 and slab.february_pt is not None:
                return slab.february_pt
            return slab.monthly_pt
    return 0
```

### TDS Computation (Section 192)

```python
from decimal import Decimal, ROUND_HALF_UP

def compute_monthly_tds(employee_id, current_month, current_year, db_conn):
    # Determine FY
    if current_month >= 4:
        fy_start_year = current_year
    else:
        fy_start_year = current_year - 1
    april_year = fy_start_year
    
    # Months elapsed since April (April=0, May=1 ... March=11)
    if current_month >= 4:
        months_elapsed = current_month - 4
    else:
        months_elapsed = current_month + 8
    months_remaining = 12 - months_elapsed  # includes current month

    # YTD gross from payroll_details for this FY
    ytd_gross = fetch_ytd_gross(employee_id, april_year, current_month, db_conn)
    
    # Current month gross
    current_gross = fetch_current_month_gross(employee_id, current_month, current_year, db_conn)
    
    # Project annual gross
    projected_annual = ytd_gross + (current_gross * months_remaining)
    
    # Get employee regime
    regime = fetch_employee_regime(employee_id, db_conn)
    
    # Standard deduction (New: 75000, Old: 50000)
    std_deduction = 75000 if regime == 'new' else 50000
    taxable_income = max(0, projected_annual - std_deduction)
    
    # Compute tax from slabs table
    annual_tax = compute_slab_tax(taxable_income, regime, fy_start_year, db_conn)
    
    # Rebate u/s 87A
    if regime == 'new' and taxable_income <= 700000:
        annual_tax = 0
    elif regime == 'old' and taxable_income <= 500000:
        annual_tax = 0
    
    # Add cess 4%
    annual_tax_with_cess = Decimal(str(annual_tax)) * Decimal('1.04')
    
    # TDS already deducted this FY
    tds_deducted = fetch_ytd_tds(employee_id, april_year, current_month, db_conn)
    
    # Monthly TDS
    monthly_tds = (annual_tax_with_cess - Decimal(str(tds_deducted))) / Decimal(str(months_remaining))
    monthly_tds = max(Decimal('0'), monthly_tds.quantize(Decimal('1'), rounding=ROUND_HALF_UP))
    
    return int(monthly_tds)
```

### Net Salary

```python
total_deductions = pf_employee + esic_employee + pt + tds
net_salary = round(lop_adjusted_gross - total_deductions, 2)
```

---

## DOCUMENT GENERATION

### Payslip PDF (`generators/payslip_pdf.py`)

ReportLab. A4 portrait. Include:
- Company header with logo, name, address, PF/ESIC reg numbers
- Employee details: name, code, designation, department, PAN, UAN, bank details
- Pay period (month, year)
- Earnings table: Basic, HRA, Special Allowance, Other Allowance, Gross
- Deductions table: PF, ESIC, PT, TDS, Total Deductions
- Net Pay in large font
- Working days, present days, LOP days
- Rupee symbol: use ₹ (Unicode) — embed a font that supports it or use "Rs."
- Footer: "This is a computer-generated document"

### PF ECR Text File (`generators/pf_ecr_txt.py`)

EPFO ECR sub-member file format 2.0. Pipe-delimited.
Header row: `#~version~establishment_id~establishment_name~wage_month~total_members~total_pf_wages~total_contribution`
Detail rows: `UAN~MemberName~EPFWages~EPSWages~EPFContribution~EPSContribution~DiffEPFandEPS~NCP_Days~Refund`

### Offer Letter DOCX (`generators/offer_letter_docx.py`)

python-docx. Professional letter format.
Fields: company letterhead, date, candidate name, designation, department, CTC, joining date, probation period.
Use a clean template with company name in header.

### Excel Payroll Register (`generators/payroll_excel.py`)

openpyxl. One sheet. Columns:
Emp Code | Name | Department | Designation | Basic | HRA | Special Allowance | Other | Gross | PF(Emp) | ESIC(Emp) | PT | TDS | Total Deductions | Net Salary

Header row: dark background, white bold text. Alternate row colours. Auto-fit column widths. Freeze top row.

---

## COMPLIANCE CALENDAR

File: `modules/compliance.py`

Compute status for each compliance item for the current and next month.
Status logic:
- `done`: payroll_run for that month exists with status='approved'
- `overdue`: deadline passed and not done
- `due_soon`: deadline within 7 days and not done
- `upcoming`: deadline more than 7 days away

Compliance items to track:
1. EPF Contribution Payment — 15th of following month
2. EPF ECR Filing — 25th of following month
3. ESIC Contribution Payment — 15th of following month
4. TDS Payment (Salary) — 7th of following month
5. TDS Return Form 24Q — Quarterly (31 Jul, 31 Oct, 31 Jan, 31 May)
6. PT Payment — last working day of month (state-dependent, simplify to EOM)
7. Form 16 Issue — 15th June

---

## BACKUP / PORTABILITY

File: `ui/backup_ui.py` + `core/database.py`

### Export

```python
import zipfile, shutil, os, datetime

def export_backup(export_dir):
    ts = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
    zip_name = f'ems_backup_{ts}.zip'
    zip_path = os.path.join(export_dir, zip_name)
    with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zf:
        zf.write('data/ems.db', 'ems.db')
        for root, dirs, files in os.walk('data/documents'):
            for file in files:
                fp = os.path.join(root, file)
                zf.write(fp, os.path.relpath(fp, 'data'))
        if os.path.exists('assets/logo.png'):
            zf.write('assets/logo.png', 'logo.png')
    return zip_path
```

### Import

```python
def import_backup(zip_path):
    with zipfile.ZipFile(zip_path, 'r') as zf:
        if 'ems.db' not in zf.namelist():
            raise ValueError('Invalid backup: ems.db not found')
    # Safety copy
    if os.path.exists('data/ems.db'):
        ts = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
        shutil.copy('data/ems.db', f'data/ems_pre_restore_{ts}.db')
    with zipfile.ZipFile(zip_path, 'r') as zf:
        zf.extractall('data/')
    # Caller must restart the app
```

---

## UI RULES

1. Framework: PyQt6. Main window with left sidebar navigation.
2. Date format: DD-MM-YYYY everywhere. No MM/DD/YYYY.
3. Currency format: Indian notation — 1,23,456.78 (not 123,456.78).
   Use a helper: `format_inr(amount)` in `ui/widgets.py`
4. Every destructive action has a QMessageBox confirmation dialog.
5. Payroll lock (approval) shows a red warning dialog before proceeding.
6. All export dialogs use QFileDialog to let user choose save location.
7. Search field on every list screen (employee list, payroll history etc.)
8. Minimum font size: 11pt throughout.
9. Color scheme: clean light theme. Sidebar: dark (#1a1a2e), accent (#e8b84b), content area: white.
10. Status bar at bottom showing current user ("Owner") and current date.

---

## PYINSTALLER BUILD

`build.spec` or `build command`:

```bash
pyinstaller --onefile --windowed --name "EMS" \
  --add-data "assets:assets" \
  --hidden-import PyQt6 \
  --hidden-import reportlab \
  --hidden-import openpyxl \
  --hidden-import docx \
  main.py
```

`main.py` must ensure `data/` directory exists on startup:

```python
import os
os.makedirs('data/documents/payslips', exist_ok=True)
os.makedirs('data/documents/form16', exist_ok=True)
os.makedirs('data/documents/letters', exist_ok=True)
os.makedirs('data/backups', exist_ok=True)
```

---

## BUILD SEQUENCE

Build phases in this exact order. Complete and test each before starting the next.

**Phase 0 (Days 1-2):** Folder structure, requirements.txt, .gitignore, database.py with full schema init, main.py entry point, PyQt6 shell with sidebar, company settings screen. Verify: app launches, DB creates all tables, company info saves.

**Phase 1 (Days 3-12):** Department CRUD, designation CRUD, full employee form (all fields), employee list with search and filter by status/department, employee view/edit screen, audit log wiring on all employee changes.

**Phase 2 (Days 13-22):** Holiday calendar screen, leave type management screen, monthly attendance grid (rows=employees, columns=days, mark status per cell), leave application form, approve/reject workflow, leave balance computation, LOP calculation. Verify: LOP days for a test month are correct.

**Phase 3 (Days 23-35):** Salary structure form per employee, payroll computation engine (all 7 steps), payroll run screen (select month/year, compute, show draft table), manual override on individual cells, approve+lock with red confirmation, payslip PDF generation, bulk payslip export.

**Phase 4 (Days 36-46):** PF ECR text file, ESIC Excel, TDS working sheet Excel, Form 16 PDF, offer letter DOCX, appointment letter DOCX, experience letter DOCX, compliance calendar screen.

**Phase 5 (Days 47-55):** Dashboard with headcount/payroll/compliance widgets, payroll register Excel, attendance register Excel, leave register Excel, backup export/import screen, PyInstaller build and test on clean Windows machine.

---

## CRITICAL RULES

1. `data/` is NEVER committed to Git. Add pre-commit hook blocking `*.db` commits.
2. Tax slabs and PT slabs are in database tables. Never hardcode rates.
3. Approved payroll runs are immutable. Enforce at application layer with status check before any UPDATE.
4. Store only last 4 digits of Aadhaar (`aadhaar_last4`). Never store full Aadhaar.
5. All monetary computations round to 2 decimal places. Use `Decimal` for TDS.
6. Enable `PRAGMA journal_mode=WAL` and `PRAGMA foreign_keys=ON` on every DB connection.
7. Every list screen must have a working search input.
8. Every salary structure has an `effective_from` date. Never overwrite old structures — insert new row and set old `is_current=0`.
9. All exports use `QFileDialog` — never auto-save to unknown path.
10. Pre-restore safety copy before any import operation.

---

## STARTING POINT

Begin with Phase 0. Deliver:
1. Complete folder structure with all `__init__.py` files
2. `core/database.py` with full schema creation function
3. `main.py` entry point that creates directories and launches app
4. `ui/main_window.py` with PyQt6 main window, left sidebar with all navigation items
5. `ui/settings_ui.py` with company info form (all fields, save/load from DB)
6. `requirements.txt` and `.gitignore`
7. `README.md` with setup instructions

After Phase 0 is verified working, proceed to Phase 1.
