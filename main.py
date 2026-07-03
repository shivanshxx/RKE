"""
Ram Krishna Enterprises — Desktop Payroll Software
Python + SQLite | Shram Sahinta Compliant
PF / ESI / TDS / PT (UP) | Salary Slip | Form 16
"""
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import threading
import os
import sys
from datetime import datetime

import database as db
import calculations as calc
import reports
import update_checker

APP_VERSION = "1.2.0"

# ── Bootstrap ──────────────────────────────────────────────────────────────────
db.init_db()

# ── Global palette ─────────────────────────────────────────────────────────────
C_SIDEBAR   = "#1B3A6B"
C_SIDEBAR_H = "#2E6DA4"
C_ACTIVE    = "#F0A500"
C_BG        = "#F5F7FA"
C_WHITE     = "#FFFFFF"
C_DARK      = "#1A1A2E"
C_GREEN     = "#1E7E34"
C_RED       = "#C0392B"
C_HEADER    = "#2E6DA4"
C_BORDER    = "#D0D7DE"

MONTHS = [(i, calc.MONTH_NAMES[i]) for i in range(1, 13)]
CURRENT_YEAR  = datetime.now().year
CURRENT_MONTH = datetime.now().month


# ═══════════════════════════════════════════════════════════════════════════════
#  MAIN APPLICATION WINDOW
# ═══════════════════════════════════════════════════════════════════════════════

class PayrollApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Ram Krishna Enterprises — Payroll Management System")
        self.geometry("1280x780")
        self.minsize(1100, 700)
        self.configure(bg=C_BG)

        # Maximise on start
        try:
            self.state('zoomed')
        except Exception:
            pass

        self._build_ui()
        self.show_dashboard()
        self.after(800, self._check_for_updates)

    # ── Auto-update ────────────────────────────────────────────────────────────

    def _check_for_updates(self):
        def worker():
            latest_tag, download_url = update_checker.check_for_update(APP_VERSION)
            if latest_tag:
                self.after(0, lambda: self._prompt_update(latest_tag, download_url))
        threading.Thread(target=worker, daemon=True).start()

    def _prompt_update(self, latest_tag, download_url):
        if not getattr(sys, 'frozen', False):
            return  # running from source — update via `git pull` instead
        if not messagebox.askyesno(
            "Update Available",
            f"A new version ({latest_tag}) is available. You're on v{APP_VERSION}.\n\n"
            "Download and install now? The app will restart automatically."
        ):
            return

        progress = tk.Toplevel(self)
        progress.title("Updating...")
        progress.geometry("320x100")
        progress.configure(bg=C_BG)
        progress.grab_set()
        tk.Label(progress, text="Downloading update, please wait...",
                 font=("Helvetica", 10), bg=C_BG).pack(pady=15)
        pbar = ttk.Progressbar(progress, length=260, mode='determinate')
        pbar.pack(pady=5)

        def on_progress(downloaded, total):
            pct = int(downloaded / total * 100)
            self.after(0, lambda: pbar.config(value=pct))

        def worker():
            try:
                update_checker.download_and_apply_update(download_url, progress_callback=on_progress)
                self.after(0, self.destroy)
            except Exception as ex:
                self.after(0, lambda: messagebox.showerror("Update Failed", str(ex), parent=progress))
                self.after(0, progress.destroy)

        threading.Thread(target=worker, daemon=True).start()

    # ── Layout ─────────────────────────────────────────────────────────────────

    def _build_ui(self):
        # Left sidebar
        self.sidebar = tk.Frame(self, bg=C_SIDEBAR, width=220)
        self.sidebar.pack(side=tk.LEFT, fill=tk.Y)
        self.sidebar.pack_propagate(False)

        # Logo area
        logo_frame = tk.Frame(self.sidebar, bg=C_SIDEBAR, pady=18)
        logo_frame.pack(fill=tk.X)
        tk.Label(logo_frame, text="RKE", font=("Helvetica", 26, "bold"),
                 bg=C_SIDEBAR, fg=C_ACTIVE).pack()
        tk.Label(logo_frame, text="Payroll System", font=("Helvetica", 10),
                 bg=C_SIDEBAR, fg="#A0BCD8").pack()
        tk.Label(logo_frame, text="Ram Krishna Enterprises", font=("Helvetica", 8),
                 bg=C_SIDEBAR, fg="#7090B0", wraplength=180).pack(pady=(2, 0))

        ttk.Separator(self.sidebar, orient='horizontal').pack(fill=tk.X, padx=15, pady=5)

        # Nav buttons
        self._nav_btns = {}
        nav_items = [
            ("🏠  Dashboard",        self.show_dashboard),
            ("👥  Employees",         self.show_employees),
            ("💰  Process Salary",    self.show_salary_processing),
            ("📄  Salary Slips",      self.show_salary_slips),
            ("📋  Form 16",           self.show_form16),
            ("📊  Reports",           self.show_reports),
            ("⚙️  Company Settings",  self.show_settings),
        ]
        for label, cmd in nav_items:
            btn = tk.Button(self.sidebar, text=label, anchor='w', padx=20,
                            font=("Helvetica", 10), bg=C_SIDEBAR, fg="#CFDEF3",
                            bd=0, relief=tk.FLAT, cursor='hand2',
                            activebackground=C_SIDEBAR_H, activeforeground=C_WHITE,
                            command=cmd)
            btn.pack(fill=tk.X, ipady=10)
            btn.bind("<Enter>", lambda e, b=btn: b.config(bg=C_SIDEBAR_H))
            btn.bind("<Leave>", lambda e, b=btn: self._nav_leave(b))
            self._nav_btns[label] = btn

        # Version at bottom
        tk.Label(self.sidebar, text="v1.0  •  Shram Sahinta", font=("Helvetica", 7),
                 bg=C_SIDEBAR, fg="#506070").pack(side=tk.BOTTOM, pady=8)

        # Right content area
        self.content = tk.Frame(self, bg=C_BG)
        self.content.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

    def _nav_leave(self, btn):
        active_text = getattr(self, '_active_nav', None)
        if btn.cget('text') != active_text:
            btn.config(bg=C_SIDEBAR)

    def _set_active_nav(self, label):
        self._active_nav = label
        for lbl, btn in self._nav_btns.items():
            if lbl == label:
                btn.config(bg=C_ACTIVE, fg=C_DARK)
            else:
                btn.config(bg=C_SIDEBAR, fg="#CFDEF3")

    def _clear_content(self):
        for w in self.content.winfo_children():
            w.destroy()

    def _page_header(self, title, subtitle=""):
        hdr = tk.Frame(self.content, bg=C_HEADER, height=60)
        hdr.pack(fill=tk.X)
        hdr.pack_propagate(False)
        tk.Label(hdr, text=title, font=("Helvetica", 16, "bold"),
                 bg=C_HEADER, fg=C_WHITE).pack(side=tk.LEFT, padx=20, pady=10)
        if subtitle:
            tk.Label(hdr, text=subtitle, font=("Helvetica", 10),
                     bg=C_HEADER, fg="#D0E8FF").pack(side=tk.LEFT, padx=5, pady=10)

    # ══════════════════════════════════════════════════════════════════════════
    #  DASHBOARD
    # ══════════════════════════════════════════════════════════════════════════

    def show_dashboard(self):
        self._clear_content()
        self._set_active_nav("🏠  Dashboard")
        self._page_header("Dashboard", "Quick Overview")

        stats = db.get_dashboard_stats()

        cards_frame = tk.Frame(self.content, bg=C_BG)
        cards_frame.pack(fill=tk.X, padx=20, pady=20)

        cards = [
            ("Total Employees", str(stats['emp_count']), C_HEADER, "Active"),
            ("Current Month Payroll", f"₹ {stats['month_total']:,.0f}", C_GREEN, "Net Salary"),
            ("Salaries Processed", str(stats['month_count']), "#7B2D8B", "This Month"),
            ("Financial Year", "2025-26", "#E67E22", "Current FY"),
        ]

        for i, (title, val, color, sub) in enumerate(cards):
            card = tk.Frame(cards_frame, bg=C_WHITE, bd=0,
                            highlightbackground=color, highlightthickness=2,
                            padx=20, pady=15)
            card.grid(row=0, column=i, padx=10, pady=5, sticky='nsew')
            cards_frame.columnconfigure(i, weight=1)

            tk.Frame(card, bg=color, width=4).pack(side=tk.LEFT, fill=tk.Y, padx=(0, 12))
            info = tk.Frame(card, bg=C_WHITE)
            info.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
            tk.Label(info, text=title, font=("Helvetica", 9), bg=C_WHITE,
                     fg="#666").pack(anchor='w')
            tk.Label(info, text=val, font=("Helvetica", 18, "bold"), bg=C_WHITE,
                     fg=color).pack(anchor='w')
            tk.Label(info, text=sub, font=("Helvetica", 8), bg=C_WHITE,
                     fg="#999").pack(anchor='w')

        # Quick actions
        tk.Label(self.content, text="Quick Actions", font=("Helvetica", 13, "bold"),
                 bg=C_BG, fg=C_DARK).pack(anchor='w', padx=20, pady=(10, 5))

        qa_frame = tk.Frame(self.content, bg=C_BG)
        qa_frame.pack(fill=tk.X, padx=20)

        actions = [
            ("➕ Add Employee",      self.show_employees,          "#2E6DA4"),
            ("💰 Process Salary",    self.show_salary_processing,  "#1E7E34"),
            ("📄 Print Salary Slip", self.show_salary_slips,        "#7B2D8B"),
            ("📋 Generate Form 16",  self.show_form16,              "#E67E22"),
        ]
        for label, cmd, color in actions:
            tk.Button(qa_frame, text=label, font=("Helvetica", 10, "bold"),
                      bg=color, fg=C_WHITE, bd=0, relief=tk.FLAT, cursor='hand2',
                      padx=18, pady=10, command=cmd).pack(side=tk.LEFT, padx=8)

        # Compliance deadlines (previous wage month)
        dl_frame = tk.Frame(self.content, bg=C_WHITE, padx=15, pady=10,
                            highlightbackground=C_BORDER, highlightthickness=1)
        dl_frame.pack(fill=tk.X, padx=20, pady=(15, 0))
        tk.Label(dl_frame, text="📅 Compliance Deadlines", font=("Helvetica", 10, "bold"),
                 bg=C_WHITE, fg=C_DARK).pack(anchor='w')
        status_styles = {'overdue': ("#C0392B", "OVERDUE"), 'due_soon': ("#E67E22", "DUE SOON"),
                         'upcoming': ("#1E7E34", "Upcoming")}
        for name, due, status in calc.compliance_deadlines():
            color, tag = status_styles[status]
            row = tk.Frame(dl_frame, bg=C_WHITE)
            row.pack(fill=tk.X, pady=1)
            tk.Label(row, text=f"[{tag}]", font=("Helvetica", 9, "bold"), bg=C_WHITE,
                     fg=color, width=10, anchor='w').pack(side=tk.LEFT)
            tk.Label(row, text=f"{name} — due {due.strftime('%d %b %Y')}",
                     font=("Helvetica", 9), bg=C_WHITE, fg="#444").pack(side=tk.LEFT)

        # Statutory notice
        notice = tk.Frame(self.content, bg="#FFF3CD", padx=15, pady=10)
        notice.pack(fill=tk.X, padx=20, pady=20)
        tk.Label(notice, text="ℹ️  Statutory Rates Applied",
                 font=("Helvetica", 10, "bold"), bg="#FFF3CD", fg="#856404").pack(anchor='w')
        notes = [
            "• PF Employee 12% | Employer 12% of Basic+DA (wage ceiling ₹15,000 per EPFO)",
            "• ESI Employee 0.75% | Employer 3.25% of Gross (applicable if Gross ≤ ₹21,000)",
            "• TDS as per Income Tax slabs (New/Old Regime) | Standard deduction included",
            "• Professional Tax (PT): Uttar Pradesh does NOT levy PT — PT = ₹0",
            "• Shram Sahinta (UP Minimum Wages): Unskilled ₹10,000 | Semi-Skilled ₹11,000 | Skilled ₹13,000",
        ]
        for note in notes:
            tk.Label(notice, text=note, font=("Helvetica", 9), bg="#FFF3CD",
                     fg="#533F03", anchor='w').pack(anchor='w')

    # ══════════════════════════════════════════════════════════════════════════
    #  EMPLOYEES
    # ══════════════════════════════════════════════════════════════════════════

    def show_employees(self):
        self._clear_content()
        self._set_active_nav("👥  Employees")
        self._page_header("Employee Management", "Add, Edit, View Employees")

        toolbar = tk.Frame(self.content, bg=C_BG)
        toolbar.pack(fill=tk.X, padx=20, pady=10)

        tk.Button(toolbar, text="➕ Add Employee", font=("Helvetica", 10, "bold"),
                  bg=C_GREEN, fg=C_WHITE, bd=0, relief=tk.FLAT, cursor='hand2',
                  padx=14, pady=7,
                  command=self._open_employee_form).pack(side=tk.LEFT, padx=(0, 8))

        tk.Button(toolbar, text="🔄 Refresh", font=("Helvetica", 10),
                  bg=C_HEADER, fg=C_WHITE, bd=0, relief=tk.FLAT, cursor='hand2',
                  padx=14, pady=7,
                  command=self.show_employees).pack(side=tk.LEFT, padx=(0, 8))

        # Search
        tk.Label(toolbar, text="Search:", font=("Helvetica", 10), bg=C_BG).pack(side=tk.LEFT, padx=8)
        self._emp_search = tk.StringVar()
        entry = tk.Entry(toolbar, textvariable=self._emp_search, font=("Helvetica", 10), width=25)
        entry.pack(side=tk.LEFT)
        self._emp_search.trace_add('write', lambda *a: self._filter_employees())

        # Table
        table_frame = tk.Frame(self.content, bg=C_BG)
        table_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=(0, 10))

        cols = ('Code', 'Name', 'Designation', 'Department', 'Basic/Day', 'Gross/Day', 'Est. Gross (26d)', 'Status')
        self.emp_tree = ttk.Treeview(table_frame, columns=cols, show='headings', selectmode='browse')

        widths = [70, 160, 120, 110, 80, 80, 110, 70]
        for col, w in zip(cols, widths):
            self.emp_tree.heading(col, text=col)
            self.emp_tree.column(col, width=w, minwidth=w, anchor='center')

        vsb = ttk.Scrollbar(table_frame, orient='vertical', command=self.emp_tree.yview)
        self.emp_tree.configure(yscrollcommand=vsb.set)
        vsb.pack(side=tk.RIGHT, fill=tk.Y)
        self.emp_tree.pack(fill=tk.BOTH, expand=True)

        # Context menu
        self.emp_tree.bind('<Double-1>', lambda e: self._edit_selected_employee())
        ctx = tk.Menu(self, tearoff=0)
        ctx.add_command(label="✏️ Edit Employee", command=self._edit_selected_employee)
        ctx.add_command(label="🗑 Deactivate",    command=self._deactivate_employee)
        self.emp_tree.bind('<Button-3>', lambda e: ctx.post(e.x_root, e.y_root))

        self._all_employees = db.get_all_employees()
        self._filter_employees()

    def _filter_employees(self):
        search = self._emp_search.get().lower() if hasattr(self, '_emp_search') else ''
        self.emp_tree.delete(*self.emp_tree.get_children())
        for emp in self._all_employees:
            if search and search not in emp['name'].lower() and search not in emp['emp_code'].lower():
                continue
            per_day_gross = emp['basic'] + emp['hra'] + emp['da'] + emp['special_allowance'] + emp['other_allowance']
            est_monthly_gross = per_day_gross * 26
            self.emp_tree.insert('', 'end', iid=str(emp['id']),
                                 values=(emp['emp_code'], emp['name'], emp['designation'],
                                         emp['department'], f"₹{emp['basic']:,.2f}",
                                         f"₹{per_day_gross:,.2f}", f"₹{est_monthly_gross:,.0f}",
                                         emp['status']))

    def _open_employee_form(self, emp_id=None):
        EmployeeForm(self, emp_id, callback=self.show_employees)

    def _edit_selected_employee(self):
        sel = self.emp_tree.focus()
        if sel:
            self._open_employee_form(int(sel))

    def _deactivate_employee(self):
        sel = self.emp_tree.focus()
        if sel and messagebox.askyesno("Confirm", "Deactivate this employee?"):
            db.delete_employee(int(sel))
            self.show_employees()

    # ══════════════════════════════════════════════════════════════════════════
    #  SALARY PROCESSING
    # ══════════════════════════════════════════════════════════════════════════

    def show_salary_processing(self):
        self._clear_content()
        self._set_active_nav("💰  Process Salary")
        self._page_header("Process Monthly Salary", "Calculate and save salary for all employees")

        ctrl = tk.Frame(self.content, bg=C_BG)
        ctrl.pack(fill=tk.X, padx=20, pady=15)

        # Month / Year selection
        tk.Label(ctrl, text="Month:", font=("Helvetica", 10, "bold"), bg=C_BG).pack(side=tk.LEFT)
        self._proc_month = tk.IntVar(value=CURRENT_MONTH)
        ttk.Combobox(ctrl, textvariable=self._proc_month, state='readonly',
                     values=[m for m, _ in MONTHS],
                     width=5).pack(side=tk.LEFT, padx=(4, 15))

        tk.Label(ctrl, text="Year:", font=("Helvetica", 10, "bold"), bg=C_BG).pack(side=tk.LEFT)
        self._proc_year = tk.IntVar(value=CURRENT_YEAR)
        ttk.Spinbox(ctrl, from_=2020, to=2035, textvariable=self._proc_year, width=7).pack(side=tk.LEFT, padx=(4, 15))

        tk.Label(ctrl, text="Days in Month:", font=("Helvetica", 10, "bold"), bg=C_BG).pack(side=tk.LEFT)
        self._proc_wdays = tk.IntVar(value=calc.calendar_days_in_month(CURRENT_YEAR, CURRENT_MONTH))
        ttk.Spinbox(ctrl, from_=1, to=31, textvariable=self._proc_wdays, width=5, state='readonly').pack(side=tk.LEFT, padx=(4, 15))

        def _sync_calendar_days(*_a):
            self._proc_wdays.set(calc.calendar_days_in_month(self._proc_year.get(), self._proc_month.get()))
        self._proc_month.trace_add('write', _sync_calendar_days)
        self._proc_year.trace_add('write', _sync_calendar_days)

        tk.Label(ctrl, text="Default Days Present:", font=("Helvetica", 10, "bold"), bg=C_BG).pack(side=tk.LEFT)
        self._proc_present = tk.IntVar(value=26)
        ttk.Spinbox(ctrl, from_=0, to=31, textvariable=self._proc_present, width=5).pack(side=tk.LEFT, padx=(4, 15))

        tk.Button(ctrl, text="🔢 Calculate All", font=("Helvetica", 10, "bold"),
                  bg=C_HEADER, fg=C_WHITE, bd=0, relief=tk.FLAT, cursor='hand2',
                  padx=14, pady=7, command=self._calculate_all_salaries).pack(side=tk.LEFT, padx=4)
        tk.Button(ctrl, text="💾 Save All", font=("Helvetica", 10, "bold"),
                  bg=C_GREEN, fg=C_WHITE, bd=0, relief=tk.FLAT, cursor='hand2',
                  padx=14, pady=7, command=self._save_all_salaries).pack(side=tk.LEFT, padx=4)
        tk.Button(ctrl, text="📊 Summary PDF", font=("Helvetica", 10, "bold"),
                  bg="#7B2D8B", fg=C_WHITE, bd=0, relief=tk.FLAT, cursor='hand2',
                  padx=14, pady=7, command=self._export_summary_pdf).pack(side=tk.LEFT, padx=4)

        # Salary table
        table_frame = tk.Frame(self.content, bg=C_BG)
        table_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=(0, 10))

        cols = ('Code', 'Name', 'Days', 'PerDay', 'Basic', 'HRA', 'DA', 'Spec', 'Gross',
                'PF(E)', 'ESI(E)', 'TDS', 'PT', 'TotDed', 'NetPay', 'PF(Er)', 'ESI(Er)')
        self.sal_tree = ttk.Treeview(table_frame, columns=cols, show='headings', selectmode='browse')

        widths = [60, 130, 50, 60, 70, 60, 60, 60, 75, 55, 55, 55, 45, 65, 75, 60, 60]
        for col, w in zip(cols, widths):
            self.sal_tree.heading(col, text=col)
            self.sal_tree.column(col, width=w, minwidth=w, anchor='center')

        vsb2 = ttk.Scrollbar(table_frame, orient='vertical', command=self.sal_tree.yview)
        hsb2 = ttk.Scrollbar(table_frame, orient='horizontal', command=self.sal_tree.xview)
        self.sal_tree.configure(yscrollcommand=vsb2.set, xscrollcommand=hsb2.set)
        vsb2.pack(side=tk.RIGHT, fill=tk.Y)
        hsb2.pack(side=tk.BOTTOM, fill=tk.X)
        self.sal_tree.pack(fill=tk.BOTH, expand=True)

        self.sal_tree.bind('<Double-1>', self._edit_salary_row)

        # Status bar
        self._proc_status = tk.StringVar(value="Ready — click 'Calculate All' to begin")
        tk.Label(self.content, textvariable=self._proc_status, font=("Helvetica", 9),
                 bg="#E8F4F8", fg=C_DARK, anchor='w', padx=10).pack(fill=tk.X, padx=20, pady=(0, 5))

        self._calculated_salaries = {}   # emp_id -> salary_dict
        self._load_existing_salaries()

    def _load_existing_salaries(self):
        year  = self._proc_year.get()
        month = self._proc_month.get()
        existing = db.get_monthly_salaries(year, month)
        self.sal_tree.delete(*self.sal_tree.get_children())
        self._calculated_salaries = {}
        for rec in existing:
            self._calculated_salaries[rec['emp_id']] = rec
            self._insert_salary_row(rec)
        self._proc_status.set(f"Loaded {len(existing)} existing records for {calc.MONTH_NAMES[month]} {year}")

    def _calculate_all_salaries(self):
        year   = self._proc_year.get()
        month  = self._proc_month.get()
        wdays  = self._proc_wdays.get()       # calendar days in month (for ESI/PT eligibility)
        default_present = self._proc_present.get()  # default days worked for employees with no saved record
        employees = db.get_all_employees()
        company_state = db.get_company().get('state', 'Uttar Pradesh')
        months_remaining = calc.months_remaining_in_fy(month)

        self.sal_tree.delete(*self.sal_tree.get_children())
        self._calculated_salaries = {}

        for emp in employees:
            # Check if record already exists — use saved days_worked (actual attendance)
            existing = db.get_salary_record(emp['id'], year, month)
            dworked  = existing['days_worked'] if existing else float(default_present)
            ytd_gross, ytd_tds = db.get_ytd_totals(emp['id'], year, month)

            sal = calc.compute_salary(emp, wdays, dworked, company_state=company_state,
                                       ytd_gross=ytd_gross, ytd_tds=ytd_tds,
                                       months_remaining=months_remaining)
            sal.update({'emp_id': emp['id'], 'year': year, 'month': month,
                        'total_days': wdays, 'days_worked': dworked,
                        'payment_mode': 'Bank Transfer', 'remarks': '',
                        'generated_on': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                        'emp_code': emp['emp_code'], 'name': emp['name']})
            self._calculated_salaries[emp['id']] = sal
            self._insert_salary_row(sal)

        self._proc_status.set(f"Calculated {len(employees)} salaries for {calc.MONTH_NAMES[month]} {year}. "
                               "Click 'Save All' to persist.")

    def _insert_salary_row(self, sal):
        code = sal.get('emp_code', '')
        name = sal.get('name', '')
        if 'per_day_gross' not in sal:
            sal['per_day_gross'] = calc.per_day_rate(sal['gross_salary'], sal.get('total_days') or 1)
        self.sal_tree.insert('', 'end', iid=str(sal.get('emp_id', id(sal))),
                             values=(code, name, sal['days_worked'],
                                     f"{sal.get('per_day_gross', 0):,.0f}",
                                     f"{sal['basic']:,.0f}", f"{sal['hra']:,.0f}",
                                     f"{sal['da']:,.0f}", f"{sal['special_allowance']:,.0f}",
                                     f"{sal['gross_salary']:,.0f}",
                                     f"{sal['pf_employee']:,.0f}", f"{sal['esi_employee']:,.0f}",
                                     f"{sal['tds']:,.0f}", f"{sal['pt']:,.0f}",
                                     f"{sal['total_deductions']:,.0f}", f"{sal['net_salary']:,.0f}",
                                     f"{sal['pf_employer']:,.0f}", f"{sal['esi_employer']:,.0f}"))

    def _save_all_salaries(self):
        if not self._calculated_salaries:
            messagebox.showwarning("No Data", "Please calculate salaries first.")
            return
        saved = 0
        for sal in self._calculated_salaries.values():
            db.save_salary_record(sal)
            saved += 1
        month = self._proc_month.get()
        messagebox.showinfo("Saved", f"✅ {saved} salary records saved for {calc.MONTH_NAMES[month]} {self._proc_year.get()}")
        self._proc_status.set(f"✅ {saved} records saved.")

    def _edit_salary_row(self, event):
        sel = self.sal_tree.focus()
        if sel:
            emp_id = int(sel)
            SalaryEditDialog(self, emp_id, self._proc_year.get(), self._proc_month.get(),
                             self._proc_wdays.get(), callback=self._load_existing_salaries)

    def _export_summary_pdf(self):
        year  = self._proc_year.get()
        month = self._proc_month.get()
        records = db.get_monthly_salaries(year, month)
        if not records:
            messagebox.showwarning("No Data", "No salary records found. Please process salaries first.")
            return
        company = db.get_company()
        path = reports.generate_payroll_summary(company, records, year, month)
        messagebox.showinfo("PDF Generated", f"Summary saved to:\n{path}")
        os.startfile(path)

    # ══════════════════════════════════════════════════════════════════════════
    #  SALARY SLIPS
    # ══════════════════════════════════════════════════════════════════════════

    def show_salary_slips(self):
        self._clear_content()
        self._set_active_nav("📄  Salary Slips")
        self._page_header("Generate Salary Slips", "Print individual or bulk salary slips")

        ctrl = tk.Frame(self.content, bg=C_BG)
        ctrl.pack(fill=tk.X, padx=20, pady=15)

        tk.Label(ctrl, text="Month:", font=("Helvetica", 10, "bold"), bg=C_BG).pack(side=tk.LEFT)
        self._slip_month = tk.IntVar(value=CURRENT_MONTH)
        ttk.Combobox(ctrl, textvariable=self._slip_month, state='readonly',
                     values=[m for m, _ in MONTHS], width=5).pack(side=tk.LEFT, padx=(4, 15))

        tk.Label(ctrl, text="Year:", font=("Helvetica", 10, "bold"), bg=C_BG).pack(side=tk.LEFT)
        self._slip_year = tk.IntVar(value=CURRENT_YEAR)
        ttk.Spinbox(ctrl, from_=2020, to=2035, textvariable=self._slip_year, width=7).pack(side=tk.LEFT, padx=(4, 15))

        tk.Button(ctrl, text="🔍 Load", font=("Helvetica", 10),
                  bg=C_HEADER, fg=C_WHITE, bd=0, padx=12, pady=7, cursor='hand2',
                  command=self._load_slip_list).pack(side=tk.LEFT, padx=4)
        tk.Button(ctrl, text="📄 Print Selected", font=("Helvetica", 10, "bold"),
                  bg=C_GREEN, fg=C_WHITE, bd=0, padx=12, pady=7, cursor='hand2',
                  command=self._print_selected_slip).pack(side=tk.LEFT, padx=4)
        tk.Button(ctrl, text="📦 Print All Slips", font=("Helvetica", 10, "bold"),
                  bg="#7B2D8B", fg=C_WHITE, bd=0, padx=12, pady=7, cursor='hand2',
                  command=self._print_all_slips).pack(side=tk.LEFT, padx=4)

        table_frame = tk.Frame(self.content, bg=C_BG)
        table_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=(0, 10))

        cols = ('Select', 'Code', 'Name', 'Gross', 'Deductions', 'Net Salary', 'Status')
        self.slip_tree = ttk.Treeview(table_frame, columns=cols, show='headings')
        for col in cols:
            w = 200 if col == 'Name' else (80 if col == 'Select' else 110)
            self.slip_tree.heading(col, text=col)
            self.slip_tree.column(col, width=w, anchor='center')

        vsb = ttk.Scrollbar(table_frame, orient='vertical', command=self.slip_tree.yview)
        vsb.pack(side=tk.RIGHT, fill=tk.Y)
        self.slip_tree.pack(fill=tk.BOTH, expand=True)
        self.slip_tree.configure(yscrollcommand=vsb.set)
        self.slip_tree.bind('<Double-1>', lambda e: self._print_selected_slip())

        self._load_slip_list()

    def _load_slip_list(self):
        year  = self._slip_year.get()
        month = self._slip_month.get()
        records = db.get_monthly_salaries(year, month)
        self.slip_tree.delete(*self.slip_tree.get_children())
        self._slip_records = {r['emp_id']: r for r in records}
        for r in records:
            self.slip_tree.insert('', 'end', iid=str(r['emp_id']),
                                  values=('☐', r.get('emp_code', ''), r.get('name', ''),
                                          f"₹{r['gross_salary']:,.0f}",
                                          f"₹{r['total_deductions']:,.0f}",
                                          f"₹{r['net_salary']:,.0f}", "✅ Processed"))

    def _print_selected_slip(self):
        sel = self.slip_tree.focus()
        if not sel:
            messagebox.showwarning("No Selection", "Please select an employee.")
            return
        emp_id = int(sel)
        self._generate_slip(emp_id)

    def _print_all_slips(self):
        if not self._slip_records:
            messagebox.showwarning("No Data", "No processed salaries found for this month.")
            return
        count = 0
        for emp_id in self._slip_records:
            self._generate_slip(emp_id, open_file=False)
            count += 1
        messagebox.showinfo("Done", f"✅ {count} salary slips generated in:\n{reports.OUTPUT_DIR}")
        os.startfile(reports.OUTPUT_DIR)

    def _generate_slip(self, emp_id, open_file=True):
        sal = self._slip_records.get(emp_id)
        if not sal:
            messagebox.showerror("Error", "Salary record not found.")
            return
        emp     = db.get_employee(emp_id)
        company = db.get_company()
        path    = reports.generate_salary_slip(company, emp, sal)
        if open_file:
            messagebox.showinfo("PDF Generated", f"Salary slip saved to:\n{path}")
            os.startfile(path)

    # ══════════════════════════════════════════════════════════════════════════
    #  FORM 16
    # ══════════════════════════════════════════════════════════════════════════

    def show_form16(self):
        self._clear_content()
        self._set_active_nav("📋  Form 16")
        self._page_header("Form 16 Generator", "Annual TDS Certificate (Part A + Part B)")

        ctrl = tk.Frame(self.content, bg=C_BG)
        ctrl.pack(fill=tk.X, padx=20, pady=15)

        tk.Label(ctrl, text="Financial Year:", font=("Helvetica", 10, "bold"), bg=C_BG).pack(side=tk.LEFT)
        self._f16_fy = tk.StringVar(value="2025-26")
        fy_options = [f"{y}-{str(y+1)[2:]}" for y in range(2022, 2028)]
        ttk.Combobox(ctrl, textvariable=self._f16_fy, state='readonly',
                     values=fy_options, width=10).pack(side=tk.LEFT, padx=(4, 15))

        tk.Button(ctrl, text="🔍 Load Employees", font=("Helvetica", 10),
                  bg=C_HEADER, fg=C_WHITE, bd=0, padx=12, pady=7, cursor='hand2',
                  command=self._load_f16_list).pack(side=tk.LEFT, padx=4)
        tk.Button(ctrl, text="📋 Generate Selected", font=("Helvetica", 10, "bold"),
                  bg=C_GREEN, fg=C_WHITE, bd=0, padx=12, pady=7, cursor='hand2',
                  command=self._gen_f16_selected).pack(side=tk.LEFT, padx=4)
        tk.Button(ctrl, text="📦 Generate All Form 16", font=("Helvetica", 10, "bold"),
                  bg="#7B2D8B", fg=C_WHITE, bd=0, padx=12, pady=7, cursor='hand2',
                  command=self._gen_f16_all).pack(side=tk.LEFT, padx=4)

        table_frame = tk.Frame(self.content, bg=C_BG)
        table_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=(0, 10))

        cols = ('Code', 'Name', 'PAN', 'Annual Gross', 'Annual TDS', 'Months', 'Regime')
        self.f16_tree = ttk.Treeview(table_frame, columns=cols, show='headings')
        widths = [80, 180, 110, 120, 110, 70, 80]
        for col, w in zip(cols, widths):
            self.f16_tree.heading(col, text=col)
            self.f16_tree.column(col, width=w, anchor='center')

        vsb = ttk.Scrollbar(table_frame, orient='vertical', command=self.f16_tree.yview)
        vsb.pack(side=tk.RIGHT, fill=tk.Y)
        self.f16_tree.pack(fill=tk.BOTH, expand=True)
        self.f16_tree.configure(yscrollcommand=vsb.set)

        self._f16_data = {}
        self._load_f16_list()

    def _load_f16_list(self):
        fy = self._f16_fy.get()
        fy_parts = fy.split('-')
        start_year = int(fy_parts[0])

        employees = db.get_all_employees()
        self.f16_tree.delete(*self.f16_tree.get_children())
        self._f16_data = {}

        for emp in employees:
            # April (start_year) to March (start_year+1)
            records = []
            for month in range(4, 13):
                r = db.get_salary_record(emp['id'], start_year, month)
                if r:
                    records.append(r)
            for month in range(1, 4):
                r = db.get_salary_record(emp['id'], start_year + 1, month)
                if r:
                    records.append(r)

            annual_gross = sum(r.get('gross_salary', 0) for r in records)
            annual_tds   = sum(r.get('tds', 0) for r in records)
            self._f16_data[emp['id']] = {'employee': emp, 'records': records}

            self.f16_tree.insert('', 'end', iid=str(emp['id']),
                                 values=(emp['emp_code'], emp['name'], emp['pan'],
                                         f"₹{annual_gross:,.0f}", f"₹{annual_tds:,.0f}",
                                         len(records), emp.get('tax_regime', 'new').title()))

    def _gen_f16_selected(self):
        sel = self.f16_tree.focus()
        if not sel:
            messagebox.showwarning("No Selection", "Please select an employee.")
            return
        emp_id = int(sel)
        self._generate_f16(emp_id)

    def _gen_f16_all(self):
        if not self._f16_data:
            messagebox.showwarning("No Data", "No data loaded.")
            return
        count = 0
        for emp_id in self._f16_data:
            data = self._f16_data[emp_id]
            if data['records']:
                self._generate_f16(emp_id, open_file=False)
                count += 1
        messagebox.showinfo("Done", f"✅ Form 16 generated for {count} employees.\nSaved in:\n{reports.OUTPUT_DIR}")
        os.startfile(reports.OUTPUT_DIR)

    def _generate_f16(self, emp_id, open_file=True):
        data = self._f16_data.get(emp_id)
        if not data or not data['records']:
            messagebox.showwarning("No Records", "No salary records found for this employee in the selected FY.")
            return
        company = db.get_company()
        fy      = self._f16_fy.get()
        path    = reports.generate_form16(company, data['employee'], data['records'], fy)
        if open_file:
            messagebox.showinfo("Form 16 Generated", f"Form 16 saved to:\n{path}")
            os.startfile(path)

    # ══════════════════════════════════════════════════════════════════════════
    #  REPORTS
    # ══════════════════════════════════════════════════════════════════════════

    def show_reports(self):
        self._clear_content()
        self._set_active_nav("📊  Reports")
        self._page_header("Reports", "Payroll summaries and statutory reports")

        frame = tk.Frame(self.content, bg=C_BG, padx=20, pady=20)
        frame.pack(fill=tk.BOTH, expand=True)

        tk.Label(frame, text="Available Reports", font=("Helvetica", 13, "bold"),
                 bg=C_BG, fg=C_DARK).pack(anchor='w', pady=(0, 15))

        report_items = [
            ("📊 Monthly Payroll Summary", "Consolidated salary sheet for a selected month",
             self._report_monthly_summary),
            ("📈 Annual Payroll Register", "Full-year salary register for all employees",
             self._report_annual_register),
            ("🏦 PF/ESI Contribution Report", "Monthly PF & ESI liabilities (Employee + Employer)",
             self._report_pf_esi),
            ("📤 PF ECR File (EPFO Upload)", "Generate the ||-delimited ECR text file for the EPFO unified portal",
             self._report_pf_ecr),
        ]

        for title, desc, cmd in report_items:
            card = tk.Frame(frame, bg=C_WHITE, bd=0,
                            highlightbackground=C_BORDER, highlightthickness=1,
                            padx=20, pady=15)
            card.pack(fill=tk.X, pady=6)
            tk.Label(card, text=title, font=("Helvetica", 11, "bold"),
                     bg=C_WHITE, fg=C_DARK).pack(anchor='w')
            tk.Label(card, text=desc, font=("Helvetica", 9), bg=C_WHITE,
                     fg="#666").pack(anchor='w', pady=(2, 8))
            tk.Button(card, text="Generate →", font=("Helvetica", 10),
                      bg=C_HEADER, fg=C_WHITE, bd=0, padx=12, pady=5, cursor='hand2',
                      command=cmd).pack(anchor='w')

    def _report_monthly_summary(self):
        self.show_salary_processing()

    def _report_annual_register(self):
        dlg = tk.Toplevel(self)
        dlg.title("Annual Payroll Register")
        dlg.geometry("380x160")
        dlg.configure(bg=C_BG)
        dlg.grab_set()

        tk.Label(dlg, text="Employee:", font=("Helvetica", 10, "bold"), bg=C_BG).grid(
            row=0, column=0, sticky='e', padx=10, pady=12)
        employees = db.get_all_employees()
        emp_var = tk.StringVar()
        emp_map = {f"{e['emp_code']} - {e['name']}": e['id'] for e in employees}
        ttk.Combobox(dlg, textvariable=emp_var, values=list(emp_map.keys()),
                     state='readonly', width=28).grid(row=0, column=1, padx=10, pady=12)

        tk.Label(dlg, text="Financial Year:", font=("Helvetica", 10, "bold"), bg=C_BG).grid(
            row=1, column=0, sticky='e', padx=10, pady=12)
        fy_var = tk.StringVar(value="2025-26")
        fy_options = [f"{y}-{str(y+1)[2:]}" for y in range(2022, 2028)]
        ttk.Combobox(dlg, textvariable=fy_var, values=fy_options, state='readonly', width=10).grid(
            row=1, column=1, sticky='w', padx=10, pady=12)

        def generate():
            if not emp_var.get():
                messagebox.showwarning("No Selection", "Please select an employee.", parent=dlg)
                return
            emp_id = emp_map[emp_var.get()]
            start_year = int(fy_var.get().split('-')[0])
            records = [r for r in (
                [db.get_salary_record(emp_id, start_year, m) for m in range(4, 13)] +
                [db.get_salary_record(emp_id, start_year + 1, m) for m in range(1, 4)]
            ) if r]
            if not records:
                messagebox.showwarning("No Data", "No salary records found for this employee in this FY.", parent=dlg)
                return
            emp = db.get_employee(emp_id)
            company = db.get_company()
            path = reports.generate_annual_register(company, emp, records, fy_var.get())
            messagebox.showinfo("Generated", f"Annual register saved to:\n{path}", parent=dlg)
            os.startfile(path)
            dlg.destroy()

        tk.Button(dlg, text="📈 Generate PDF", font=("Helvetica", 10, "bold"),
                  bg=C_GREEN, fg=C_WHITE, bd=0, padx=14, pady=8, cursor='hand2',
                  command=generate).grid(row=2, column=0, columnspan=2, pady=15)

    def _report_pf_esi(self):
        month = CURRENT_MONTH
        year  = CURRENT_YEAR
        records = db.get_monthly_salaries(year, month)
        if not records:
            messagebox.showwarning("No Data", f"No salary records found for {calc.MONTH_NAMES[month]} {year}.\n"
                                               "Please process salaries first.")
            return
        company = db.get_company()
        path = reports.generate_pf_esi_report(company, records, year, month)
        messagebox.showinfo("PDF Generated", f"PF/ESI report saved to:\n{path}")
        os.startfile(path)

    def _report_pf_ecr(self):
        month = CURRENT_MONTH
        year  = CURRENT_YEAR
        records = db.get_monthly_salaries(year, month)
        if not records:
            # Fall back to the previous month — ECR is usually filed for last month's wages
            month = month - 1 or 12
            year = year if CURRENT_MONTH > 1 else year - 1
            records = db.get_monthly_salaries(year, month)
        if not records:
            messagebox.showwarning("No Data", "No processed salary records found for this or last month.")
            return
        employees_by_id = {e['id']: e for e in db.get_all_employees()}
        path, skipped = reports.generate_pf_ecr(records, employees_by_id, year, month)
        msg = f"ECR file for {calc.MONTH_NAMES[month]} {year} saved to:\n{path}"
        if skipped:
            msg += "\n\n⚠️ Skipped (no UAN on record):\n" + "\n".join(skipped)
        messagebox.showinfo("ECR Generated", msg)
        os.startfile(reports.OUTPUT_DIR)

    # ══════════════════════════════════════════════════════════════════════════
    #  SETTINGS
    # ══════════════════════════════════════════════════════════════════════════

    def show_settings(self):
        self._clear_content()
        self._set_active_nav("⚙️  Company Settings")
        self._page_header("Company Settings", "Update company and statutory details")

        frame = tk.Frame(self.content, bg=C_BG, padx=20, pady=15)
        frame.pack(fill=tk.BOTH, expand=True)

        company = db.get_company()

        fields = [
            ("Company Name",      "name",          40),
            ("Address",           "address",       60),
            ("City",              "city",          30),
            ("State",             "state",         30),
            ("Pin Code",          "pincode",       15),
            ("Phone",             "phone",         20),
            ("Email",             "email",         40),
            ("PAN",               "pan",           15),
            ("TAN",               "tan",           15),
            ("PF Registration No","pf_reg",        25),
            ("ESI Registration No","esi_reg",      25),
            ("Financial Year",    "financial_year",10),
        ]

        self._setting_vars = {}
        for i, (label, key, w) in enumerate(fields):
            row = i // 2
            col = (i % 2) * 3
            tk.Label(frame, text=label + ":", font=("Helvetica", 10, "bold"),
                     bg=C_BG, anchor='e').grid(row=row, column=col, sticky='e', padx=(10, 5), pady=8)
            var = tk.StringVar(value=company.get(key, ''))
            tk.Entry(frame, textvariable=var, width=w, font=("Helvetica", 10)).grid(
                row=row, column=col+1, sticky='w', pady=8)
            self._setting_vars[key] = var

        tk.Button(frame, text="💾 Save Settings", font=("Helvetica", 11, "bold"),
                  bg=C_GREEN, fg=C_WHITE, bd=0, padx=20, pady=10, cursor='hand2',
                  command=self._save_settings).grid(row=len(fields)//2 + 1, column=0,
                                                    columnspan=6, pady=20)

        # ── Security ──────────────────────────────────────────────────────────
        sec_row = len(fields)//2 + 2
        ttk.Separator(frame, orient='horizontal').grid(row=sec_row, column=0, columnspan=6,
                                                        sticky='ew', pady=(10, 15))
        tk.Label(frame, text="🔒 Account Security", font=("Helvetica", 12, "bold"),
                 bg=C_BG, fg=C_DARK).grid(row=sec_row+1, column=0, columnspan=6, sticky='w', padx=10)

        has_pwd = db.has_password()
        status_text = "Password protection is ON." if has_pwd else "No password set — app opens without a login screen."
        tk.Label(frame, text=status_text, font=("Helvetica", 9), bg=C_BG, fg="#666").grid(
            row=sec_row+2, column=0, columnspan=6, sticky='w', padx=10, pady=(2, 8))

        btn_text = "🔑 Change Password" if has_pwd else "🔑 Set Password"
        tk.Button(frame, text=btn_text, font=("Helvetica", 10, "bold"),
                  bg=C_HEADER, fg=C_WHITE, bd=0, padx=14, pady=7, cursor='hand2',
                  command=self._open_password_dialog).grid(row=sec_row+3, column=0, sticky='w', padx=10)

        if has_pwd:
            tk.Button(frame, text="🗑 Remove Password", font=("Helvetica", 10),
                      bg=C_RED, fg=C_WHITE, bd=0, padx=14, pady=7, cursor='hand2',
                      command=self._remove_password).grid(row=sec_row+3, column=1, sticky='w', padx=10)

        # ── Backup / Restore ──────────────────────────────────────────────────
        bk_row = sec_row + 4
        ttk.Separator(frame, orient='horizontal').grid(row=bk_row, column=0, columnspan=6,
                                                        sticky='ew', pady=(15, 15))
        tk.Label(frame, text="💾 Data Backup", font=("Helvetica", 12, "bold"),
                 bg=C_BG, fg=C_DARK).grid(row=bk_row+1, column=0, columnspan=6, sticky='w', padx=10)
        tk.Label(frame, text="Back up all employee and salary data to a file you can copy to a pen drive or cloud folder.",
                 font=("Helvetica", 9), bg=C_BG, fg="#666").grid(
            row=bk_row+2, column=0, columnspan=6, sticky='w', padx=10, pady=(2, 8))
        tk.Button(frame, text="📤 Backup Now", font=("Helvetica", 10, "bold"),
                  bg=C_GREEN, fg=C_WHITE, bd=0, padx=14, pady=7, cursor='hand2',
                  command=self._backup_now).grid(row=bk_row+3, column=0, sticky='w', padx=10)
        tk.Button(frame, text="📥 Restore From Backup", font=("Helvetica", 10),
                  bg=C_HEADER, fg=C_WHITE, bd=0, padx=14, pady=7, cursor='hand2',
                  command=self._restore_backup).grid(row=bk_row+3, column=1, sticky='w', padx=10)

    def _backup_now(self):
        dest_dir = filedialog.askdirectory(title="Choose backup folder")
        if not dest_dir:
            return
        try:
            path = db.backup_db(dest_dir)
            messagebox.showinfo("Backup Complete", f"Backup saved to:\n{path}")
        except Exception as ex:
            messagebox.showerror("Backup Failed", str(ex))

    def _restore_backup(self):
        if not messagebox.askyesno(
            "Confirm Restore",
            "Restoring will REPLACE all current data with the backup.\n"
            "A safety copy of the current data will be kept.\n\nContinue?"):
            return
        path = filedialog.askopenfilename(title="Select backup file",
                                           filetypes=[("Database backup", "*.db"), ("All files", "*.*")])
        if not path:
            return
        try:
            safety = db.restore_db(path)
            messagebox.showinfo("Restore Complete",
                                f"Data restored. Previous data saved at:\n{safety}\n\n"
                                "The app will now close — reopen it to load the restored data.")
            self.destroy()
        except Exception as ex:
            messagebox.showerror("Restore Failed", str(ex))

    def _save_settings(self):
        data = {k: v.get() for k, v in self._setting_vars.items()}
        db.save_company(data)
        messagebox.showinfo("Saved", "✅ Company settings saved successfully.")

    def _open_password_dialog(self):
        PasswordDialog(self, has_existing=db.has_password(), callback=self.show_settings)

    def _remove_password(self):
        if messagebox.askyesno("Confirm", "Remove password protection? The app will open without a login screen."):
            db.clear_password()
            messagebox.showinfo("Done", "Password protection removed.")
            self.show_settings()


# ═══════════════════════════════════════════════════════════════════════════════
#  PASSWORD DIALOG (Set / Change)
# ═══════════════════════════════════════════════════════════════════════════════

class PasswordDialog(tk.Toplevel):
    def __init__(self, parent, has_existing=False, callback=None):
        super().__init__(parent)
        self.has_existing = has_existing
        self.callback = callback
        self.title("Change Password" if has_existing else "Set Password")
        self.geometry("360x280" if has_existing else "360x220")
        self.configure(bg=C_BG)
        self.grab_set()

        frame = tk.Frame(self, bg=C_BG, padx=25, pady=20)
        frame.pack(fill=tk.BOTH, expand=True)

        row_n = 0
        self._current_var = None
        if has_existing:
            tk.Label(frame, text="Current Password:", font=("Helvetica", 10, "bold"), bg=C_BG,
                     width=18, anchor='e').grid(row=row_n, column=0, sticky='e', pady=8)
            self._current_var = tk.StringVar()
            tk.Entry(frame, textvariable=self._current_var, show='*', width=20,
                     font=("Helvetica", 10)).grid(row=row_n, column=1, sticky='w', pady=8)
            row_n += 1

        tk.Label(frame, text="New Password:", font=("Helvetica", 10, "bold"), bg=C_BG,
                 width=18, anchor='e').grid(row=row_n, column=0, sticky='e', pady=8)
        self._new_var = tk.StringVar()
        tk.Entry(frame, textvariable=self._new_var, show='*', width=20,
                 font=("Helvetica", 10)).grid(row=row_n, column=1, sticky='w', pady=8)
        row_n += 1

        tk.Label(frame, text="Confirm Password:", font=("Helvetica", 10, "bold"), bg=C_BG,
                 width=18, anchor='e').grid(row=row_n, column=0, sticky='e', pady=8)
        self._confirm_var = tk.StringVar()
        tk.Entry(frame, textvariable=self._confirm_var, show='*', width=20,
                 font=("Helvetica", 10)).grid(row=row_n, column=1, sticky='w', pady=8)
        row_n += 1

        tk.Button(frame, text="💾 Save Password", font=("Helvetica", 10, "bold"),
                  bg=C_GREEN, fg=C_WHITE, bd=0, padx=16, pady=8, cursor='hand2',
                  command=self._save).grid(row=row_n, column=0, columnspan=2, pady=20)

    def _save(self):
        if self.has_existing:
            if not db.verify_password(self._current_var.get()):
                messagebox.showerror("Error", "Current password is incorrect.", parent=self)
                return

        new_pwd = self._new_var.get()
        confirm = self._confirm_var.get()
        if not new_pwd or len(new_pwd) < 4:
            messagebox.showerror("Error", "Password must be at least 4 characters.", parent=self)
            return
        if new_pwd != confirm:
            messagebox.showerror("Error", "Passwords do not match.", parent=self)
            return

        db.set_password(new_pwd)
        messagebox.showinfo("Saved", "Password updated successfully.", parent=self)
        if self.callback:
            self.callback()
        self.destroy()


# ═══════════════════════════════════════════════════════════════════════════════
#  EMPLOYEE FORM (Add / Edit)
# ═══════════════════════════════════════════════════════════════════════════════

class EmployeeForm(tk.Toplevel):
    def __init__(self, parent, emp_id=None, callback=None):
        super().__init__(parent)
        self.emp_id   = emp_id
        self.callback = callback
        self.title("Edit Employee" if emp_id else "Add New Employee")
        self.geometry("860x680")
        self.resizable(True, True)
        self.configure(bg=C_BG)
        self.grab_set()

        emp = db.get_employee(emp_id) if emp_id else {}

        # Scrollable canvas
        canvas = tk.Canvas(self, bg=C_BG, highlightthickness=0)
        scrollbar = ttk.Scrollbar(self, orient='vertical', command=canvas.yview)
        canvas.configure(yscrollcommand=scrollbar.set)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        canvas.pack(fill=tk.BOTH, expand=True)

        inner = tk.Frame(canvas, bg=C_BG, padx=20, pady=10)
        canvas.create_window((0, 0), window=inner, anchor='nw')
        inner.bind('<Configure>', lambda e: canvas.configure(scrollregion=canvas.bbox('all')))
        canvas.bind('<MouseWheel>', lambda e: canvas.yview_scroll(-1*(e.delta//120), 'units'))

        self._vars = {}

        def section(title):
            f = tk.Frame(inner, bg=C_HEADER, padx=10, pady=5)
            f.pack(fill=tk.X, pady=(12, 5))
            tk.Label(f, text=title, font=("Helvetica", 10, "bold"),
                     bg=C_HEADER, fg=C_WHITE).pack(anchor='w')
            return tk.Frame(inner, bg=C_BG)

        def field(parent_frame, row, col, label, key, default='', width=22, is_bool=False, options=None):
            tk.Label(parent_frame, text=label + ":", font=("Helvetica", 9, "bold"),
                     bg=C_BG, anchor='e', width=18).grid(row=row, column=col*2, sticky='e', padx=(10, 4), pady=5)
            if is_bool:
                var = tk.IntVar(value=int(emp.get(key, default)))
                tk.Checkbutton(parent_frame, variable=var, bg=C_BG).grid(
                    row=row, column=col*2+1, sticky='w', pady=5)
            elif options:
                var = tk.StringVar(value=str(emp.get(key, default)))
                ttk.Combobox(parent_frame, textvariable=var, values=options,
                             state='readonly', width=width-2).grid(
                    row=row, column=col*2+1, sticky='w', pady=5)
            else:
                var = tk.StringVar(value=str(emp.get(key, default)))
                tk.Entry(parent_frame, textvariable=var, width=width,
                         font=("Helvetica", 10)).grid(
                    row=row, column=col*2+1, sticky='w', pady=5)
            self._vars[key] = var

        # Personal info
        sec1 = section("Personal Information")
        sec1.pack(fill=tk.X)
        field(sec1, 0, 0, "Employee Code", "emp_code", '', 15)
        field(sec1, 0, 1, "Full Name",     "name",     '', 28)
        field(sec1, 1, 0, "Father's Name", "father_name", '', 22)
        field(sec1, 1, 1, "Gender",        "gender",    'Male',   15, options=['Male', 'Female', 'Other'])
        field(sec1, 2, 0, "Date of Birth", "dob",       '', 15)
        field(sec1, 2, 1, "Date of Joining","doj",      '', 15)
        field(sec1, 3, 0, "PAN",           "pan",       '', 15)
        field(sec1, 3, 1, "Aadhaar",       "aadhaar",   '', 18)
        # Mask stored Aadhaar on display (UIDAI guidance): show XXXX-XXXX-1234.
        # On save, a masked value means "unchanged" and the original is kept.
        self._orig_aadhaar = str(emp.get('aadhaar', '') or '')
        if len(self._orig_aadhaar) >= 4 and self._orig_aadhaar.isdigit():
            self._vars['aadhaar'].set(f"XXXX-XXXX-{self._orig_aadhaar[-4:]}")

        # Job info
        sec2 = section("Job Details")
        sec2.pack(fill=tk.X)
        field(sec2, 0, 0, "Designation",   "designation", '', 22)
        field(sec2, 0, 1, "Department",    "department",  '', 22)
        field(sec2, 1, 0, "Status",        "status", 'Active', 12, options=['Active', 'Inactive'])
        field(sec2, 1, 1, "Tax Regime",    "tax_regime", 'new', 12, options=['new', 'old'])

        # Salary — entered as PER-DAY rates. The month's salary = per-day rate x days the
        # employee actually came (entered while processing salary), not a flat monthly figure.
        sec3 = section("Salary Components (₹ PER DAY)")
        sec3.pack(fill=tk.X)
        field(sec3, 0, 0, "Basic (Per Day)",       "basic", 0, 12)
        field(sec3, 0, 1, "HRA (Per Day)",         "hra",   0, 12)
        field(sec3, 1, 0, "DA (Per Day)",          "da",    0, 12)
        field(sec3, 1, 1, "Special Allow. (Per Day)", "special_allowance", 0, 12)
        field(sec3, 2, 0, "Other Allow. (Per Day)",   "other_allowance", 0, 12)

        # Statutory
        sec4 = section("Statutory Deductions")
        sec4.pack(fill=tk.X)
        field(sec4, 0, 0, "PF Applicable",  "pf_applicable",  1, is_bool=True)
        field(sec4, 0, 1, "ESI Applicable", "esi_applicable", 1, is_bool=True)
        field(sec4, 1, 0, "TDS Applicable", "tds_applicable", 0, is_bool=True)
        field(sec4, 1, 1, "PF Number",      "pf_number",  '', 20)
        field(sec4, 2, 0, "ESI Number",     "esi_number", '', 20)
        field(sec4, 2, 1, "UAN",            "uan",        '', 18)

        # Bank
        sec5 = section("Bank Details")
        sec5.pack(fill=tk.X)
        field(sec5, 0, 0, "Bank Name",    "bank_name",    '', 22)
        field(sec5, 0, 1, "Account No",   "bank_account", '', 22)
        field(sec5, 1, 0, "IFSC Code",    "ifsc",         '', 15)

        # Buttons
        btn_frame = tk.Frame(inner, bg=C_BG, pady=15)
        btn_frame.pack(fill=tk.X)
        tk.Button(btn_frame, text="💾 Save", font=("Helvetica", 11, "bold"),
                  bg=C_GREEN, fg=C_WHITE, bd=0, padx=20, pady=8, cursor='hand2',
                  command=self._save).pack(side=tk.LEFT, padx=(10, 8))
        tk.Button(btn_frame, text="Cancel", font=("Helvetica", 10),
                  bg=C_RED, fg=C_WHITE, bd=0, padx=20, pady=8, cursor='hand2',
                  command=self.destroy).pack(side=tk.LEFT)

    def _save(self):
        data = {}
        for key, var in self._vars.items():
            val = var.get()
            try:
                if key in ('basic', 'hra', 'da', 'special_allowance', 'other_allowance'):
                    val = float(val)
                elif key in ('pf_applicable', 'esi_applicable', 'tds_applicable'):
                    val = int(val)
            except ValueError:
                val = 0
            data[key] = val

        if not data.get('emp_code') or not data.get('name'):
            messagebox.showerror("Validation", "Employee Code and Name are required.", parent=self)
            return

        if db.emp_code_exists(data['emp_code'], self.emp_id):
            messagebox.showerror("Duplicate", "Employee code already exists.", parent=self)
            return

        # Masked Aadhaar means unchanged — keep the stored original
        if 'X' in str(data.get('aadhaar', '')):
            data['aadhaar'] = self._orig_aadhaar

        # Labour Codes: basic+DA must be >= 50% of gross wages
        gross_day = (data['basic'] + data['hra'] + data['da'] +
                     data['special_allowance'] + data['other_allowance'])
        ok50, pct = calc.check_wage_code_50pct(data['basic'], data['da'], gross_day)
        if not ok50:
            if not messagebox.askyesno(
                "Wage Code Warning",
                f"Basic + DA is only {pct}% of gross pay.\n\n"
                "The Labour Codes (in force since Nov 2025) require wages (Basic + DA) "
                "to be at least 50% of total remuneration. Keeping it lower is "
                "non-compliant and understates PF/gratuity.\n\nSave anyway?",
                parent=self):
                return

        # UP minimum wage check (per-day rates -> monthly equivalent at 26 days)
        ok_mw, min_w, shortfall = calc.check_minimum_wage((data['basic'] + data['da']) * 26)
        if not ok_mw:
            if not messagebox.askyesno(
                "Minimum Wage Warning",
                f"Basic + DA (~Rs {(data['basic'] + data['da']) * 26:,.0f}/month at 26 days) is below the "
                f"UP minimum wage of Rs {min_w:,.0f}/month (unskilled) by Rs {shortfall:,.0f}.\n\nSave anyway?",
                parent=self):
                return

        try:
            if self.emp_id:
                db.update_employee(self.emp_id, data)
                messagebox.showinfo("Saved", "Employee updated successfully.", parent=self)
            else:
                db.add_employee(data)
                messagebox.showinfo("Saved", "Employee added successfully.", parent=self)
            if self.callback:
                self.callback()
            self.destroy()
        except Exception as ex:
            messagebox.showerror("Error", str(ex), parent=self)


# ═══════════════════════════════════════════════════════════════════════════════
#  SALARY EDIT DIALOG
# ═══════════════════════════════════════════════════════════════════════════════

class SalaryEditDialog(tk.Toplevel):
    """Edit attendance and additional deductions for a single employee."""
    def __init__(self, parent, emp_id, year, month, total_days, callback=None):
        super().__init__(parent)
        self.emp_id    = emp_id
        self.year      = year
        self.month     = month
        self.total_days = total_days
        self.callback  = callback

        emp = db.get_employee(emp_id)
        self.title(f"Edit Salary — {emp['name']} — {calc.MONTH_NAMES[month]} {year}")
        self.geometry("480x380")
        self.configure(bg=C_BG)
        self.grab_set()

        existing = db.get_salary_record(emp_id, year, month) or {}

        frame = tk.Frame(self, bg=C_BG, padx=25, pady=20)
        frame.pack(fill=tk.BOTH, expand=True)

        def row(lbl, key, default, is_float=True, row_n=0):
            tk.Label(frame, text=lbl, font=("Helvetica", 10, "bold"), bg=C_BG, width=22, anchor='e').grid(
                row=row_n, column=0, sticky='e', padx=8, pady=8)
            var = tk.StringVar(value=str(existing.get(key, default)))
            tk.Entry(frame, textvariable=var, width=15, font=("Helvetica", 10)).grid(
                row=row_n, column=1, sticky='w', pady=8)
            return var

        self._wdays  = row("Working Days in Month",  'total_days',       total_days, row_n=0)
        self._dwork  = row("Days Actually Worked",   'days_worked',      float(total_days), row_n=1)
        self._oth_ded = row("Other Deductions (₹)",  'other_deductions', 0, row_n=2)
        self._pmmode  = row("Payment Mode",          'payment_mode',     'Bank Transfer', row_n=3)
        self._rem     = row("Remarks",               'remarks',          '', row_n=4)

        tk.Button(frame, text="💾 Recalculate & Save", font=("Helvetica", 10, "bold"),
                  bg=C_GREEN, fg=C_WHITE, bd=0, padx=16, pady=8, cursor='hand2',
                  command=self._save).grid(row=5, column=0, columnspan=2, pady=20)

    def _save(self):
        try:
            wdays  = int(self._wdays.get())
            dwork  = float(self._dwork.get())
            oth    = float(self._oth_ded.get())
            mode   = self._pmmode.get()
            rem    = self._rem.get()
        except ValueError:
            messagebox.showerror("Error", "Invalid numeric value.", parent=self)
            return

        emp = db.get_employee(self.emp_id)
        company_state = db.get_company().get('state', 'Uttar Pradesh')
        months_remaining = calc.months_remaining_in_fy(self.month)
        ytd_gross, ytd_tds = db.get_ytd_totals(self.emp_id, self.year, self.month)
        sal = calc.compute_salary(emp, wdays, dwork, company_state=company_state,
                                   ytd_gross=ytd_gross, ytd_tds=ytd_tds,
                                   months_remaining=months_remaining)
        sal['other_deductions']  = oth
        sal['total_deductions'] += oth
        sal['net_salary']        = round(sal['gross_salary'] - sal['total_deductions'], 2)
        sal.update({'emp_id': self.emp_id, 'year': self.year, 'month': self.month,
                    'total_days': wdays, 'days_worked': dwork,
                    'payment_mode': mode, 'remarks': rem,
                    'generated_on': datetime.now().strftime('%Y-%m-%d %H:%M:%S')})
        db.save_salary_record(sal)
        messagebox.showinfo("Saved", "Salary record updated.", parent=self)
        if self.callback:
            self.callback()
        self.destroy()


# ═══════════════════════════════════════════════════════════════════════════════
#  LOGIN GATE
# ═══════════════════════════════════════════════════════════════════════════════

class LoginWindow(tk.Tk):
    """Shown before the main app if a password has been set. Max 3 attempts."""
    MAX_ATTEMPTS = 3

    def __init__(self):
        super().__init__()
        self.title("RKE Payroll — Login")
        self.geometry("380x220")
        self.resizable(False, False)
        self.configure(bg=C_BG)
        self.attempts = 0
        self.authenticated = False

        tk.Label(self, text="🔒 RKE Payroll", font=("Helvetica", 16, "bold"),
                 bg=C_BG, fg=C_SIDEBAR).pack(pady=(25, 5))
        tk.Label(self, text="Enter password to continue", font=("Helvetica", 10),
                 bg=C_BG, fg="#666").pack(pady=(0, 15))

        self._pwd_var = tk.StringVar()
        entry = tk.Entry(self, textvariable=self._pwd_var, show='*', font=("Helvetica", 11), width=26)
        entry.pack(pady=5)
        entry.focus_set()
        entry.bind('<Return>', lambda e: self._try_login())

        self._err_label = tk.Label(self, text="", font=("Helvetica", 9), bg=C_BG, fg=C_RED)
        self._err_label.pack(pady=(5, 0))

        tk.Button(self, text="Login", font=("Helvetica", 10, "bold"), bg=C_HEADER, fg=C_WHITE,
                  bd=0, padx=20, pady=8, cursor='hand2', command=self._try_login).pack(pady=15)

        self.protocol("WM_DELETE_WINDOW", self._on_close)

    def _try_login(self):
        if db.verify_password(self._pwd_var.get()):
            self.authenticated = True
            self.destroy()
        else:
            self.attempts += 1
            remaining = self.MAX_ATTEMPTS - self.attempts
            if remaining <= 0:
                messagebox.showerror("Locked Out", "Too many incorrect attempts. Exiting.")
                self.authenticated = False
                self.destroy()
                return
            self._err_label.config(text=f"Incorrect password. {remaining} attempt(s) left.")
            self._pwd_var.set("")

    def _on_close(self):
        self.authenticated = False
        self.destroy()


# ═══════════════════════════════════════════════════════════════════════════════
#  ENTRY POINT
# ═══════════════════════════════════════════════════════════════════════════════

if __name__ == '__main__':
    proceed = True
    if db.has_password():
        login = LoginWindow()
        login.mainloop()
        proceed = login.authenticated

    if proceed:
        app = PayrollApp()
        app.mainloop()
