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
import ttkbootstrap as tb

UI_THEME = "cosmo"

APP_VERSION = "1.5.0"

# ── Bootstrap ──────────────────────────────────────────────────────────────────
db.init_db()

# ── Global palette (modern flat theme) ────────────────────────────────────────
C_SIDEBAR   = "#111827"   # slate-900 — sidebar
C_SIDEBAR_H = "#1F2937"   # slate-800 — sidebar hover
C_ACTIVE    = "#F59E0B"   # amber-500 — active nav highlight
C_BG        = "#F3F4F6"   # gray-100 — app background
C_WHITE     = "#FFFFFF"
C_DARK      = "#111827"   # near-black text
C_GREEN     = "#059669"   # emerald-600 — success / primary actions
C_RED       = "#DC2626"   # red-600 — destructive actions
C_HEADER    = "#4F46E5"   # indigo-600 — accents, section bars, info buttons
C_BORDER    = "#E5E7EB"   # gray-200 — card borders
C_MUTED     = "#6B7280"   # gray-500 — secondary text

def stripe_rows(tree):
    """Apply alternating row backgrounds to a Treeview (call after filling it)."""
    tree.tag_configure('odd', background="#F9FAFB")
    tree.tag_configure('even', background=C_WHITE)
    for i, iid in enumerate(tree.get_children()):
        tree.item(iid, tags=('odd' if i % 2 else 'even',))


MONTHS = [(i, calc.MONTH_NAMES[i]) for i in range(1, 13)]
CURRENT_YEAR  = datetime.now().year
CURRENT_MONTH = datetime.now().month


# ═══════════════════════════════════════════════════════════════════════════════
#  MAIN APPLICATION WINDOW
# ═══════════════════════════════════════════════════════════════════════════════

class PayrollApp(tb.Window):
    def __init__(self):
        super().__init__(themename=UI_THEME)
        self.title("Ram Krishna Enterprises — Payroll Management System")
        self.geometry("1280x780")
        self.minsize(1100, 700)
        self.configure(bg=C_BG)

        # Maximise on start
        try:
            self.state('zoomed')
        except Exception:
            pass

        self._setup_styles()
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
                 font=("Segoe UI", 10), bg=C_BG).pack(pady=15)
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

    # ── Theme / styles ─────────────────────────────────────────────────────────

    def _setup_styles(self):
        style = ttk.Style(self)

        # Tables: taller rows, clean flat headers, indigo selection
        style.configure('Treeview', rowheight=32, font=("Segoe UI", 10),
                        background=C_WHITE, fieldbackground=C_WHITE,
                        foreground=C_DARK, borderwidth=0)
        style.configure('Treeview.Heading', font=("Segoe UI", 10, "bold"),
                        background="#F9FAFB", foreground=C_MUTED,
                        relief='flat', padding=(8, 8))
        style.map('Treeview.Heading', background=[('active', '#F3F4F6')])
        style.map('Treeview',
                  background=[('selected', C_HEADER)],
                  foreground=[('selected', C_WHITE)])

        # Inputs
        style.configure('TCombobox', padding=4)
        style.configure('TSpinbox', padding=4)
        style.configure('Vertical.TScrollbar', background='#D1D5DB',
                        troughcolor=C_BG, borderwidth=0, arrowsize=12)
        style.configure('Horizontal.TProgressbar', background=C_GREEN,
                        troughcolor=C_BORDER, borderwidth=0, thickness=8)

    # ── Layout ─────────────────────────────────────────────────────────────────

    def _build_ui(self):
        # Left sidebar
        self.sidebar = tk.Frame(self, bg=C_SIDEBAR, width=236)
        self.sidebar.pack(side=tk.LEFT, fill=tk.Y)
        self.sidebar.pack_propagate(False)

        # Logo area
        logo_frame = tk.Frame(self.sidebar, bg=C_SIDEBAR, pady=24)
        logo_frame.pack(fill=tk.X)
        tk.Label(logo_frame, text="RKE", font=("Segoe UI", 24, "bold"),
                 bg=C_SIDEBAR, fg=C_WHITE).pack()
        tk.Label(logo_frame, text="PAYROLL", font=("Segoe UI", 9, "bold"),
                 bg=C_SIDEBAR, fg=C_ACTIVE).pack()
        tk.Label(logo_frame, text="Ram Krishna Enterprises", font=("Segoe UI", 8),
                 bg=C_SIDEBAR, fg="#6B7280", wraplength=190).pack(pady=(4, 0))

        # Nav buttons — flat rows with a left accent bar on the active item
        self._nav_btns = {}
        nav_frame = tk.Frame(self.sidebar, bg=C_SIDEBAR)
        nav_frame.pack(fill=tk.X, pady=(10, 0))
        nav_items = [
            ("🏠  Dashboard",        self.show_dashboard),
            ("👥  Employees",         self.show_employees),
            ("📆  Attendance",        self.show_attendance),
            ("💰  Process Salary",    self.show_salary_processing),
            ("📄  Salary Slips",      self.show_salary_slips),
            ("📋  Form 16",           self.show_form16),
            ("📊  Reports",           self.show_reports),
            ("⚙️  Company Settings",  self.show_settings),
        ]
        for label, cmd in nav_items:
            row = tk.Frame(nav_frame, bg=C_SIDEBAR)
            row.pack(fill=tk.X)
            accent = tk.Frame(row, bg=C_SIDEBAR, width=4)
            accent.pack(side=tk.LEFT, fill=tk.Y)
            btn = tk.Button(row, text=label, anchor='w', padx=18,
                            font=("Segoe UI", 10), bg=C_SIDEBAR, fg="#9CA3AF",
                            bd=0, relief=tk.FLAT, cursor='hand2',
                            activebackground=C_SIDEBAR_H, activeforeground=C_WHITE,
                            command=cmd)
            btn.pack(side=tk.LEFT, fill=tk.X, expand=True, ipady=11)
            btn.bind("<Enter>", lambda e, b=btn: b.config(bg=C_SIDEBAR_H, fg=C_WHITE)
                     if b.cget('text') != getattr(self, '_active_nav', None) else None)
            btn.bind("<Leave>", lambda e, b=btn: self._nav_leave(b))
            self._nav_btns[label] = (btn, accent, row)

        # Version at bottom
        tk.Label(self.sidebar, text=f"v{APP_VERSION}  •  Shram Sahinta Compliant",
                 font=("Segoe UI", 8), bg=C_SIDEBAR, fg="#4B5563").pack(side=tk.BOTTOM, pady=12)

        # Right content area
        self.content = tk.Frame(self, bg=C_BG)
        self.content.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

    def _nav_leave(self, btn):
        active_text = getattr(self, '_active_nav', None)
        if btn.cget('text') != active_text:
            btn.config(bg=C_SIDEBAR, fg="#9CA3AF")

    def _set_active_nav(self, label):
        self._active_nav = label
        for lbl, (btn, accent, row) in self._nav_btns.items():
            if lbl == label:
                btn.config(bg=C_SIDEBAR_H, fg=C_WHITE, font=("Segoe UI", 10, "bold"))
                accent.config(bg=C_ACTIVE)
                row.config(bg=C_SIDEBAR_H)
            else:
                btn.config(bg=C_SIDEBAR, fg="#9CA3AF", font=("Segoe UI", 10))
                accent.config(bg=C_SIDEBAR)
                row.config(bg=C_SIDEBAR)

    def _clear_content(self):
        for w in self.content.winfo_children():
            w.destroy()

    def _page_header(self, title, subtitle=""):
        hdr = tk.Frame(self.content, bg=C_WHITE)
        hdr.pack(fill=tk.X)
        inner = tk.Frame(hdr, bg=C_WHITE, padx=24, pady=14)
        inner.pack(fill=tk.X)
        tk.Label(inner, text=title, font=("Segoe UI", 17, "bold"),
                 bg=C_WHITE, fg=C_DARK).pack(side=tk.LEFT)
        if subtitle:
            tk.Label(inner, text=subtitle, font=("Segoe UI", 10),
                     bg=C_WHITE, fg=C_MUTED).pack(side=tk.LEFT, padx=(12, 0), pady=(6, 0))
        tk.Frame(hdr, bg=C_BORDER, height=1).pack(fill=tk.X)

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
            ("Salaries Processed", str(stats['month_count']), "#7C3AED", "This Month"),
            ("Financial Year", f"{calc.current_fy_start()}-{str(calc.current_fy_start() + 1)[2:]}", "#D97706", "Current FY"),
        ]

        for i, (title, val, color, sub) in enumerate(cards):
            card = tk.Frame(cards_frame, bg=C_WHITE, bd=0,
                            highlightbackground=C_BORDER, highlightthickness=1,
                            padx=22, pady=18)
            card.grid(row=0, column=i, padx=(0 if i == 0 else 14, 0), pady=5, sticky='nsew')
            cards_frame.columnconfigure(i, weight=1)

            tk.Label(card, text=title.upper(), font=("Segoe UI", 8, "bold"), bg=C_WHITE,
                     fg=C_MUTED).pack(anchor='w')
            tk.Label(card, text=val, font=("Segoe UI", 22, "bold"), bg=C_WHITE,
                     fg=C_DARK).pack(anchor='w', pady=(4, 2))
            badge = tk.Frame(card, bg=C_WHITE)
            badge.pack(anchor='w')
            tk.Frame(badge, bg=color, width=8, height=8).pack(side=tk.LEFT, pady=3)
            tk.Label(badge, text=" " + sub, font=("Segoe UI", 9), bg=C_WHITE,
                     fg=C_MUTED).pack(side=tk.LEFT)

        # Quick actions
        tk.Label(self.content, text="Quick Actions", font=("Segoe UI", 13, "bold"),
                 bg=C_BG, fg=C_DARK).pack(anchor='w', padx=20, pady=(10, 5))

        qa_frame = tk.Frame(self.content, bg=C_BG)
        qa_frame.pack(fill=tk.X, padx=20)

        actions = [
            ("➕ Add Employee",      self.show_employees,          "#4F46E5"),
            ("💰 Process Salary",    self.show_salary_processing,  "#1E7E34"),
            ("📄 Print Salary Slip", self.show_salary_slips,        "#7C3AED"),
            ("📋 Generate Form 16",  self.show_form16,              "#D97706"),
        ]
        for label, cmd, color in actions:
            tb.Button(qa_frame, text=label, command=cmd, bootstyle="primary").pack(side=tk.LEFT, padx=8)

        # Compliance deadlines (previous wage month)
        dl_frame = tk.Frame(self.content, bg=C_WHITE, padx=15, pady=10,
                            highlightbackground=C_BORDER, highlightthickness=1)
        dl_frame.pack(fill=tk.X, padx=20, pady=(15, 0))
        tk.Label(dl_frame, text="📅 Compliance Deadlines", font=("Segoe UI", 10, "bold"),
                 bg=C_WHITE, fg=C_DARK).pack(anchor='w')
        status_styles = {'overdue': ("#C0392B", "OVERDUE"), 'due_soon': ("#D97706", "DUE SOON"),
                         'upcoming': ("#1E7E34", "Upcoming")}
        for name, due, status in calc.compliance_deadlines():
            color, tag = status_styles[status]
            row = tk.Frame(dl_frame, bg=C_WHITE)
            row.pack(fill=tk.X, pady=1)
            tk.Label(row, text=f"[{tag}]", font=("Segoe UI", 9, "bold"), bg=C_WHITE,
                     fg=color, width=10, anchor='w').pack(side=tk.LEFT)
            tk.Label(row, text=f"{name} — due {due.strftime('%d %b %Y')}",
                     font=("Segoe UI", 9), bg=C_WHITE, fg="#444").pack(side=tk.LEFT)

        # Statutory notice
        notice = tk.Frame(self.content, bg="#FFF3CD", padx=15, pady=10)
        notice.pack(fill=tk.X, padx=20, pady=20)
        tk.Label(notice, text="ℹ️  Statutory Rates Applied",
                 font=("Segoe UI", 10, "bold"), bg="#FFF3CD", fg="#856404").pack(anchor='w')
        notes = [
            "• PF Employee 12% | Employer 12% of Basic+DA (wage ceiling ₹15,000 per EPFO)",
            "• ESI Employee 0.75% | Employer 3.25% of Gross (applicable if Gross ≤ ₹21,000)",
            "• TDS as per Income Tax slabs (New/Old Regime) | Standard deduction included",
            "• Professional Tax (PT): Uttar Pradesh does NOT levy PT — PT = ₹0",
            "• Shram Sahinta (UP Minimum Wages): Unskilled ₹10,000 | Semi-Skilled ₹11,000 | Skilled ₹13,000",
        ]
        for note in notes:
            tk.Label(notice, text=note, font=("Segoe UI", 9), bg="#FFF3CD",
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

        tb.Button(toolbar, text="➕ Add Employee", command=self._open_employee_form, bootstyle="success").pack(side=tk.LEFT, padx=(0, 8))

        tb.Button(toolbar, text="🔄 Refresh", command=self.show_employees, bootstyle="primary").pack(side=tk.LEFT, padx=(0, 8))

        # Search
        tk.Label(toolbar, text="Search:", font=("Segoe UI", 10), bg=C_BG).pack(side=tk.LEFT, padx=8)
        self._emp_search = tk.StringVar()
        entry = tk.Entry(toolbar, textvariable=self._emp_search, font=("Segoe UI", 10), width=25)
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
        ctx.add_command(label="📜 Pay Revision History", command=self._pay_history_selected)
        ctx.add_command(label="🧾 Full & Final Settlement", command=self._fnf_selected)
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
        stripe_rows(self.emp_tree)

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

    def _pay_history_selected(self):
        sel = self.emp_tree.focus()
        if not sel:
            return
        emp = db.get_employee(int(sel))
        hist = db.get_salary_history(int(sel))
        dlg = tk.Toplevel(self)
        dlg.title(f"Pay Revision History — {emp['name']}")
        dlg.geometry("640x360")
        dlg.configure(bg=C_BG)
        cols = ('From', 'Basic/day', 'HRA/day', 'DA/day', 'Special/day', 'Other/day', 'Gross/day')
        tree = ttk.Treeview(dlg, columns=cols, show='headings')
        for col in cols:
            tree.heading(col, text=col)
            tree.column(col, width=85, anchor='center')
        for h in hist:
            gross = (h['basic'] or 0) + (h['hra'] or 0) + (h['da'] or 0) +                     (h['special_allowance'] or 0) + (h['other_allowance'] or 0)
            tree.insert('', 'end', values=(h['effective_from'], f"{h['basic']:,.2f}",
                                           f"{h['hra']:,.2f}", f"{h['da']:,.2f}",
                                           f"{h['special_allowance']:,.2f}",
                                           f"{h['other_allowance']:,.2f}", f"{gross:,.2f}"))
        tree.pack(fill=tk.BOTH, expand=True, padx=12, pady=12)
        stripe_rows(tree)
        if not hist:
            tk.Label(dlg, text="No revisions recorded yet — history starts when you next save this employee.",
                     font=("Segoe UI", 9), bg=C_BG, fg=C_MUTED).pack(pady=(0, 10))

    def _fnf_selected(self):
        sel = self.emp_tree.focus()
        if not sel:
            return
        FnFDialog(self, int(sel))

    # ══════════════════════════════════════════════════════════════════════════
    #  ATTENDANCE (simple exception-based: unmarked = Present)
    # ══════════════════════════════════════════════════════════════════════════

    def show_attendance(self):
        self._clear_content()
        self._set_active_nav("📆  Attendance")
        self._page_header("Attendance", "Click a day to mark: Absent → Half-day → Present. Unmarked = Present.")

        ctrl = tk.Frame(self.content, bg=C_BG)
        ctrl.pack(fill=tk.X, padx=20, pady=12)

        tk.Label(ctrl, text="Month:", font=("Segoe UI", 10, "bold"), bg=C_BG).pack(side=tk.LEFT)
        self._att_month = tk.IntVar(value=CURRENT_MONTH)
        ttk.Combobox(ctrl, textvariable=self._att_month, state='readonly',
                     values=[m for m, _ in MONTHS], width=5).pack(side=tk.LEFT, padx=(4, 15))
        tk.Label(ctrl, text="Year:", font=("Segoe UI", 10, "bold"), bg=C_BG).pack(side=tk.LEFT)
        self._att_year = tk.IntVar(value=CURRENT_YEAR)
        ttk.Spinbox(ctrl, from_=2020, to=2035, textvariable=self._att_year, width=7).pack(side=tk.LEFT, padx=(4, 15))
        tb.Button(ctrl, text="Load", command=self._load_attendance_grid, bootstyle="primary").pack(side=tk.LEFT, padx=4)
        tb.Button(ctrl, text="💾 Save Attendance", command=self._save_attendance, bootstyle="success").pack(side=tk.LEFT, padx=4)

        # Legend
        legend = tk.Frame(ctrl, bg=C_BG)
        legend.pack(side=tk.RIGHT)
        for text, color in (("Present", "#D1FAE5"), ("Half-day", "#FEF3C7"), ("Absent", "#FEE2E2")):
            tk.Label(legend, text="  " + text + "  ", font=("Segoe UI", 9), bg=color,
                     fg=C_DARK).pack(side=tk.LEFT, padx=3)

        # Scrollable grid
        wrap = tk.Frame(self.content, bg=C_WHITE, highlightbackground=C_BORDER, highlightthickness=1)
        wrap.pack(fill=tk.BOTH, expand=True, padx=20, pady=(0, 12))
        canvas = tk.Canvas(wrap, bg=C_WHITE, highlightthickness=0)
        vsb = ttk.Scrollbar(wrap, orient='vertical', command=canvas.yview)
        hsb = ttk.Scrollbar(wrap, orient='horizontal', command=canvas.xview)
        canvas.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)
        vsb.pack(side=tk.RIGHT, fill=tk.Y)
        hsb.pack(side=tk.BOTTOM, fill=tk.X)
        canvas.pack(fill=tk.BOTH, expand=True)
        self._att_grid_frame = tk.Frame(canvas, bg=C_WHITE)
        canvas.create_window((0, 0), window=self._att_grid_frame, anchor='nw')
        self._att_grid_frame.bind('<Configure>',
                                   lambda e: canvas.configure(scrollregion=canvas.bbox('all')))
        canvas.bind('<MouseWheel>', lambda e: canvas.yview_scroll(-1 * (e.delta // 120), 'units'))

        self._load_attendance_grid()

    def _load_attendance_grid(self):
        import calendar as _cal
        for w in self._att_grid_frame.winfo_children():
            w.destroy()

        year, month = self._att_year.get(), self._att_month.get()
        ndays = _cal.monthrange(year, month)[1]
        employees = db.get_all_employees()
        saved = db.get_attendance(year, month)
        # marks kept in memory until saved: {emp_id: {day: 'A'|'H'}}
        self._att_marks = {e['id']: dict(saved.get(e['id'], {})) for e in employees}
        self._att_cells = {}

        hdr_bg = "#F9FAFB"
        tk.Label(self._att_grid_frame, text="Employee", font=("Segoe UI", 9, "bold"),
                 bg=hdr_bg, fg=C_MUTED, width=20, anchor='w', padx=8).grid(row=0, column=0, sticky='nsew')
        for d in range(1, ndays + 1):
            wd = _cal.weekday(year, month, d)
            fg = C_RED if wd == 6 else C_MUTED
            tk.Label(self._att_grid_frame, text=str(d), font=("Segoe UI", 8, "bold"),
                     bg=hdr_bg, fg=fg, width=3).grid(row=0, column=d, sticky='nsew')
        tk.Label(self._att_grid_frame, text="Worked", font=("Segoe UI", 9, "bold"),
                 bg=hdr_bg, fg=C_MUTED, width=8).grid(row=0, column=ndays + 1, sticky='nsew')

        colors = {'': "#D1FAE5", 'H': "#FEF3C7", 'A': "#FEE2E2"}
        texts = {'': "P", 'H': "½", 'A': "A"}

        for r, emp in enumerate(employees, start=1):
            row_bg = C_WHITE if r % 2 else "#F9FAFB"
            tk.Label(self._att_grid_frame, text=emp['name'][:22], font=("Segoe UI", 9),
                     bg=row_bg, anchor='w', padx=8).grid(row=r, column=0, sticky='nsew')
            for d in range(1, ndays + 1):
                status = self._att_marks[emp['id']].get(d, '')
                cell = tk.Label(self._att_grid_frame, text=texts[status], width=3,
                                font=("Segoe UI", 8), bg=colors[status], fg=C_DARK,
                                bd=1, relief=tk.FLAT, cursor='hand2')
                cell.grid(row=r, column=d, sticky='nsew', padx=1, pady=1)
                cell.bind('<Button-1>', lambda e, eid=emp['id'], day=d: self._cycle_attendance(eid, day))
                self._att_cells[(emp['id'], d)] = cell
            total_lbl = tk.Label(self._att_grid_frame, text="", font=("Segoe UI", 9, "bold"),
                                 bg=row_bg, fg=C_DARK)
            total_lbl.grid(row=r, column=ndays + 1, sticky='nsew')
            self._att_cells[(emp['id'], 'total')] = total_lbl
            self._update_att_total(emp['id'], ndays)

    def _cycle_attendance(self, emp_id, day):
        import calendar as _cal
        cur = self._att_marks[emp_id].get(day, '')
        nxt = {'': 'A', 'A': 'H', 'H': ''}[cur]
        if nxt:
            self._att_marks[emp_id][day] = nxt
        else:
            self._att_marks[emp_id].pop(day, None)
        colors = {'': "#D1FAE5", 'H': "#FEF3C7", 'A': "#FEE2E2"}
        texts = {'': "P", 'H': "½", 'A': "A"}
        cell = self._att_cells[(emp_id, day)]
        cell.config(text=texts[nxt], bg=colors[nxt])
        ndays = _cal.monthrange(self._att_year.get(), self._att_month.get())[1]
        self._update_att_total(emp_id, ndays)

    def _update_att_total(self, emp_id, ndays):
        marks = self._att_marks[emp_id]
        worked = ndays - sum(1 for s in marks.values() if s == 'A') \
                 - 0.5 * sum(1 for s in marks.values() if s == 'H')
        lbl = self._att_cells.get((emp_id, 'total'))
        if lbl:
            lbl.config(text=f"{worked:g}")

    def _save_attendance(self):
        year, month = self._att_year.get(), self._att_month.get()
        db.save_attendance(year, month, self._att_marks)
        marked = sum(len(v) for v in self._att_marks.values())
        messagebox.showinfo("Saved", f"Attendance saved for {calc.MONTH_NAMES[month]} {year} "
                                     f"({marked} exception mark(s)).\n\n"
                                     "Process Salary will now use these day counts automatically.")

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
        tk.Label(ctrl, text="Month:", font=("Segoe UI", 10, "bold"), bg=C_BG).pack(side=tk.LEFT)
        self._proc_month = tk.IntVar(value=CURRENT_MONTH)
        ttk.Combobox(ctrl, textvariable=self._proc_month, state='readonly',
                     values=[m for m, _ in MONTHS],
                     width=5).pack(side=tk.LEFT, padx=(4, 15))

        tk.Label(ctrl, text="Year:", font=("Segoe UI", 10, "bold"), bg=C_BG).pack(side=tk.LEFT)
        self._proc_year = tk.IntVar(value=CURRENT_YEAR)
        ttk.Spinbox(ctrl, from_=2020, to=2035, textvariable=self._proc_year, width=7).pack(side=tk.LEFT, padx=(4, 15))

        tk.Label(ctrl, text="Days in Month:", font=("Segoe UI", 10, "bold"), bg=C_BG).pack(side=tk.LEFT)
        self._proc_wdays = tk.IntVar(value=calc.calendar_days_in_month(CURRENT_YEAR, CURRENT_MONTH))
        ttk.Spinbox(ctrl, from_=1, to=31, textvariable=self._proc_wdays, width=5, state='readonly').pack(side=tk.LEFT, padx=(4, 15))

        def _sync_calendar_days(*_a):
            self._proc_wdays.set(calc.calendar_days_in_month(self._proc_year.get(), self._proc_month.get()))
        self._proc_month.trace_add('write', _sync_calendar_days)
        self._proc_year.trace_add('write', _sync_calendar_days)

        tk.Label(ctrl, text="Default Days Present:", font=("Segoe UI", 10, "bold"), bg=C_BG).pack(side=tk.LEFT)
        self._proc_present = tk.IntVar(value=26)
        ttk.Spinbox(ctrl, from_=0, to=31, textvariable=self._proc_present, width=5).pack(side=tk.LEFT, padx=(4, 15))

        tb.Button(ctrl, text="🔢 Calculate All", command=self._calculate_all_salaries, bootstyle="primary").pack(side=tk.LEFT, padx=4)
        tb.Button(ctrl, text="💾 Save All", command=self._save_all_salaries, bootstyle="success").pack(side=tk.LEFT, padx=4)
        tb.Button(ctrl, text="📊 Summary PDF", command=self._export_summary_pdf, bootstyle="info").pack(side=tk.LEFT, padx=4)

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
        tk.Label(self.content, textvariable=self._proc_status, font=("Segoe UI", 9),
                 bg="#EEF2FF", fg=C_DARK, anchor='w', padx=10).pack(fill=tk.X, padx=20, pady=(0, 5))

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
        stripe_rows(self.sal_tree)
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

        locked = 0
        computed = 0
        for emp in employees:
            existing = db.get_salary_record(emp['id'], year, month)
            if existing:
                # Saved months are LOCKED: show as-is, never recompute or overwrite.
                # Changes require the supervisory override in the edit dialog.
                rec = dict(existing)
                rec.update({'emp_code': emp['emp_code'], 'name': emp['name'] + '  🔒'})
                self._insert_salary_row(rec)
                locked += 1
                continue

            # Days worked priority: attendance grid > default spinner
            att_days = db.attendance_days_worked(emp['id'], year, month, wdays)
            dworked = att_days if att_days is not None else float(default_present)
            ytd_gross, ytd_tds = db.get_ytd_totals(emp['id'], year, month)

            # Rates in effect for THIS month (effective-dated), not today's rates
            rates = db.get_rates_for_month(emp['id'], year, month)
            emp_eff = dict(emp)
            emp_eff.update(rates)

            sal = calc.compute_salary(emp_eff, wdays, dworked, company_state=company_state,
                                       ytd_gross=ytd_gross, ytd_tds=ytd_tds,
                                       months_remaining=months_remaining)
            calc.apply_extras(sal, additional_earnings=0, other_deductions=0)
            sal.update({'emp_id': emp['id'], 'year': year, 'month': month,
                        'total_days': wdays, 'days_worked': dworked,
                        'payment_mode': 'Bank Transfer', 'remarks': '',
                        'generated_on': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                        'emp_code': emp['emp_code'], 'name': emp['name']})
            self._calculated_salaries[emp['id']] = sal
            self._insert_salary_row(sal)
            computed += 1
        stripe_rows(self.sal_tree)

        self._proc_status.set(
            f"{calc.MONTH_NAMES[month]} {year}: {computed} computed (unsaved), {locked} locked 🔒. "
            "'Save All' saves only new records — saved months never change.")

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

        tk.Label(ctrl, text="Month:", font=("Segoe UI", 10, "bold"), bg=C_BG).pack(side=tk.LEFT)
        self._slip_month = tk.IntVar(value=CURRENT_MONTH)
        ttk.Combobox(ctrl, textvariable=self._slip_month, state='readonly',
                     values=[m for m, _ in MONTHS], width=5).pack(side=tk.LEFT, padx=(4, 15))

        tk.Label(ctrl, text="Year:", font=("Segoe UI", 10, "bold"), bg=C_BG).pack(side=tk.LEFT)
        self._slip_year = tk.IntVar(value=CURRENT_YEAR)
        ttk.Spinbox(ctrl, from_=2020, to=2035, textvariable=self._slip_year, width=7).pack(side=tk.LEFT, padx=(4, 15))

        tb.Button(ctrl, text="🔍 Load", command=self._load_slip_list, bootstyle="primary").pack(side=tk.LEFT, padx=4)
        tb.Button(ctrl, text="📄 Print Selected", command=self._print_selected_slip, bootstyle="success").pack(side=tk.LEFT, padx=4)
        tb.Button(ctrl, text="📦 Print All Slips", command=self._print_all_slips, bootstyle="info").pack(side=tk.LEFT, padx=4)

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
        stripe_rows(self.slip_tree)

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

        tk.Label(ctrl, text="Financial Year:", font=("Segoe UI", 10, "bold"), bg=C_BG).pack(side=tk.LEFT)
        self._f16_fy = tk.StringVar(value="2025-26")
        fy_options = [f"{y}-{str(y+1)[2:]}" for y in range(2022, 2028)]
        ttk.Combobox(ctrl, textvariable=self._f16_fy, state='readonly',
                     values=fy_options, width=10).pack(side=tk.LEFT, padx=(4, 15))

        tb.Button(ctrl, text="🔍 Load Employees", command=self._load_f16_list, bootstyle="primary").pack(side=tk.LEFT, padx=4)
        tb.Button(ctrl, text="📋 Generate Selected", command=self._gen_f16_selected, bootstyle="success").pack(side=tk.LEFT, padx=4)
        tb.Button(ctrl, text="📦 Generate All Form 16", command=self._gen_f16_all, bootstyle="info").pack(side=tk.LEFT, padx=4)

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
        stripe_rows(self.f16_tree)

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

        tk.Label(frame, text="Available Reports", font=("Segoe UI", 13, "bold"),
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
            ("🏧 Bank Advice (Salary Transfer)", "CSV sheet of account numbers, IFSC and net pay — hand to your bank for disbursement",
             self._report_bank_advice),
            ("📗 Excel Payroll Register (.xlsx)", "Full financial-year workbook: one sheet per month + FY summary, straight from saved records",
             self._report_excel_register),
        ]

        for title, desc, cmd in report_items:
            card = tk.Frame(frame, bg=C_WHITE, bd=0,
                            highlightbackground=C_BORDER, highlightthickness=1,
                            padx=20, pady=15)
            card.pack(fill=tk.X, pady=6)
            tk.Label(card, text=title, font=("Segoe UI", 11, "bold"),
                     bg=C_WHITE, fg=C_DARK).pack(anchor='w')
            tk.Label(card, text=desc, font=("Segoe UI", 9), bg=C_WHITE,
                     fg="#666").pack(anchor='w', pady=(2, 8))
            tb.Button(card, text="Generate →", command=cmd, bootstyle="primary").pack(anchor='w')

    def _report_monthly_summary(self):
        self.show_salary_processing()

    def _report_annual_register(self):
        dlg = tk.Toplevel(self)
        dlg.title("Annual Payroll Register")
        dlg.geometry("380x160")
        dlg.configure(bg=C_BG)
        dlg.grab_set()

        tk.Label(dlg, text="Employee:", font=("Segoe UI", 10, "bold"), bg=C_BG).grid(
            row=0, column=0, sticky='e', padx=10, pady=12)
        employees = db.get_all_employees()
        emp_var = tk.StringVar()
        emp_map = {f"{e['emp_code']} - {e['name']}": e['id'] for e in employees}
        ttk.Combobox(dlg, textvariable=emp_var, values=list(emp_map.keys()),
                     state='readonly', width=28).grid(row=0, column=1, padx=10, pady=12)

        tk.Label(dlg, text="Financial Year:", font=("Segoe UI", 10, "bold"), bg=C_BG).grid(
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

        tb.Button(dlg, text="📈 Generate PDF", command=generate, bootstyle="success").grid(row=2, column=0, columnspan=2, pady=15)

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

    def _report_excel_register(self):
        fy = calc.current_fy_start()
        months_data = {}
        for m in list(range(4, 13)) + list(range(1, 4)):
            y = fy if m >= 4 else fy + 1
            recs = db.get_monthly_salaries(y, m)
            if recs:
                months_data[(y, m)] = recs
        if not months_data:
            messagebox.showwarning("No Data", f"No saved salary records found for FY {fy}-{str(fy+1)[2:]}.")
            return
        path = filedialog.asksaveasfilename(
            title="Save Excel Register", defaultextension=".xlsx",
            initialfile=f"PayrollRegister_FY{fy}-{str(fy+1)[2:]}.xlsx",
            filetypes=[("Excel Workbook", "*.xlsx")])
        if not path:
            return
        company = db.get_company()
        reports.generate_excel_register(company, fy, months_data, path)
        messagebox.showinfo("Exported", f"Excel register saved to:\n{path}")
        os.startfile(path)

    def _report_bank_advice(self):
        month, year = CURRENT_MONTH, CURRENT_YEAR
        records = db.get_monthly_salaries(year, month)
        if not records:
            month = month - 1 or 12
            year = year if CURRENT_MONTH > 1 else year - 1
            records = db.get_monthly_salaries(year, month)
        if not records:
            messagebox.showwarning("No Data", "No processed salary records found for this or last month.")
            return
        path = filedialog.asksaveasfilename(
            title="Save Bank Advice", defaultextension=".csv",
            initialfile=f"BankAdvice_{year}_{month:02d}.csv",
            filetypes=[("CSV (opens in Excel)", "*.csv")])
        if not path:
            return
        import csv
        missing = []
        with open(path, 'w', newline='', encoding='utf-8-sig') as f:
            w = csv.writer(f)
            w.writerow(["Sr", "Employee Code", "Name", "Bank", "Account Number", "IFSC", "Net Pay (Rs)"])
            total = 0
            for i, r in enumerate(records, 1):
                emp = db.get_employee(r['emp_id'])
                if not emp.get('bank_account'):
                    missing.append(emp['name'])
                w.writerow([i, r.get('emp_code', ''), r.get('name', ''),
                            emp.get('bank_name', ''), emp.get('bank_account', ''),
                            emp.get('ifsc', ''), f"{r['net_salary']:.2f}"])
                total += r['net_salary']
            w.writerow([])
            w.writerow(["", "", "", "", "", "TOTAL", f"{total:.2f}"])
        msg = f"Bank advice for {calc.MONTH_NAMES[month]} {year} saved to:\n{path}"
        if missing:
            msg += "\n\n⚠️ Missing bank account for:\n" + "\n".join(missing)
        messagebox.showinfo("Exported", msg)

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
            tk.Label(frame, text=label + ":", font=("Segoe UI", 10, "bold"),
                     bg=C_BG, anchor='e').grid(row=row, column=col, sticky='e', padx=(10, 5), pady=8)
            var = tk.StringVar(value=company.get(key, ''))
            tk.Entry(frame, textvariable=var, width=w, font=("Segoe UI", 10)).grid(
                row=row, column=col+1, sticky='w', pady=8)
            self._setting_vars[key] = var

        tb.Button(frame, text="💾 Save Settings", command=self._save_settings, bootstyle="success").grid(row=len(fields)//2 + 1, column=0,
                                                    columnspan=6, pady=20)

        # ── Security ──────────────────────────────────────────────────────────
        sec_row = len(fields)//2 + 2
        ttk.Separator(frame, orient='horizontal').grid(row=sec_row, column=0, columnspan=6,
                                                        sticky='ew', pady=(10, 15))
        tk.Label(frame, text="🔒 Account Security", font=("Segoe UI", 12, "bold"),
                 bg=C_BG, fg=C_DARK).grid(row=sec_row+1, column=0, columnspan=6, sticky='w', padx=10)

        has_pwd = db.has_password()
        status_text = "Password protection is ON." if has_pwd else "No password set — app opens without a login screen."
        tk.Label(frame, text=status_text, font=("Segoe UI", 9), bg=C_BG, fg="#666").grid(
            row=sec_row+2, column=0, columnspan=6, sticky='w', padx=10, pady=(2, 8))

        btn_text = "🔑 Change Password" if has_pwd else "🔑 Set Password"
        tb.Button(frame, text=btn_text, command=self._open_password_dialog, bootstyle="primary").grid(row=sec_row+3, column=0, sticky='w', padx=10)

        if has_pwd:
            tb.Button(frame, text="🗑 Remove Password", command=self._remove_password, bootstyle="danger").grid(row=sec_row+3, column=1, sticky='w', padx=10)

        # ── Backup / Restore ──────────────────────────────────────────────────
        bk_row = sec_row + 4
        ttk.Separator(frame, orient='horizontal').grid(row=bk_row, column=0, columnspan=6,
                                                        sticky='ew', pady=(15, 15))
        tk.Label(frame, text="💾 Data Backup", font=("Segoe UI", 12, "bold"),
                 bg=C_BG, fg=C_DARK).grid(row=bk_row+1, column=0, columnspan=6, sticky='w', padx=10)
        tk.Label(frame, text="Back up all employee and salary data to a file you can copy to a pen drive or cloud folder.",
                 font=("Segoe UI", 9), bg=C_BG, fg="#666").grid(
            row=bk_row+2, column=0, columnspan=6, sticky='w', padx=10, pady=(2, 8))
        tb.Button(frame, text="📤 Backup Now", command=self._backup_now, bootstyle="success").grid(row=bk_row+3, column=0, sticky='w', padx=10)
        tb.Button(frame, text="📥 Restore From Backup", command=self._restore_backup, bootstyle="primary").grid(row=bk_row+3, column=1, sticky='w', padx=10)

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
            tk.Label(frame, text="Current Password:", font=("Segoe UI", 10, "bold"), bg=C_BG,
                     width=18, anchor='e').grid(row=row_n, column=0, sticky='e', pady=8)
            self._current_var = tk.StringVar()
            tk.Entry(frame, textvariable=self._current_var, show='*', width=20,
                     font=("Segoe UI", 10)).grid(row=row_n, column=1, sticky='w', pady=8)
            row_n += 1

        tk.Label(frame, text="New Password:", font=("Segoe UI", 10, "bold"), bg=C_BG,
                 width=18, anchor='e').grid(row=row_n, column=0, sticky='e', pady=8)
        self._new_var = tk.StringVar()
        tk.Entry(frame, textvariable=self._new_var, show='*', width=20,
                 font=("Segoe UI", 10)).grid(row=row_n, column=1, sticky='w', pady=8)
        row_n += 1

        tk.Label(frame, text="Confirm Password:", font=("Segoe UI", 10, "bold"), bg=C_BG,
                 width=18, anchor='e').grid(row=row_n, column=0, sticky='e', pady=8)
        self._confirm_var = tk.StringVar()
        tk.Entry(frame, textvariable=self._confirm_var, show='*', width=20,
                 font=("Segoe UI", 10)).grid(row=row_n, column=1, sticky='w', pady=8)
        row_n += 1

        tb.Button(frame, text="💾 Save Password", command=self._save, bootstyle="success").grid(row=row_n, column=0, columnspan=2, pady=20)

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
            tk.Label(f, text=title, font=("Segoe UI", 10, "bold"),
                     bg=C_HEADER, fg=C_WHITE).pack(anchor='w')
            return tk.Frame(inner, bg=C_BG)

        def field(parent_frame, row, col, label, key, default='', width=22, is_bool=False, options=None):
            tk.Label(parent_frame, text=label + ":", font=("Segoe UI", 9, "bold"),
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
                         font=("Segoe UI", 10)).grid(
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
        tb.Button(btn_frame, text="💾 Save", command=self._save, bootstyle="success").pack(side=tk.LEFT, padx=(10, 8))
        tb.Button(btn_frame, text="Cancel", command=self.destroy, bootstyle="danger").pack(side=tk.LEFT)

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
                db.record_salary_revision(self.emp_id, data)
                messagebox.showinfo("Saved", "Employee updated successfully.", parent=self)
            else:
                new_id = db.add_employee(data)
                db.record_salary_revision(new_id, data, note='Initial pay')
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
        self.geometry("480x430")
        self.configure(bg=C_BG)
        self.grab_set()

        existing = db.get_salary_record(emp_id, year, month) or {}

        frame = tk.Frame(self, bg=C_BG, padx=25, pady=20)
        frame.pack(fill=tk.BOTH, expand=True)

        def row(lbl, key, default, is_float=True, row_n=0):
            tk.Label(frame, text=lbl, font=("Segoe UI", 10, "bold"), bg=C_BG, width=22, anchor='e').grid(
                row=row_n, column=0, sticky='e', padx=8, pady=8)
            var = tk.StringVar(value=str(existing.get(key, default)))
            tk.Entry(frame, textvariable=var, width=15, font=("Segoe UI", 10)).grid(
                row=row_n, column=1, sticky='w', pady=8)
            return var

        self._wdays  = row("Working Days in Month",  'total_days',       total_days, row_n=0)
        self._dwork  = row("Days Actually Worked",   'days_worked',      float(total_days), row_n=1)
        self._bonus  = row("Bonus / Overtime (₹)",   'additional_earnings', 0, row_n=2)
        self._oth_ded = row("Other Deductions (₹)",  'other_deductions', 0, row_n=3)
        self._pmmode  = row("Payment Mode",          'payment_mode',     'Bank Transfer', row_n=4)
        self._rem     = row("Remarks",               'remarks',          '', row_n=5)

        tb.Button(frame, text="💾 Recalculate & Save", command=self._save, bootstyle="success").grid(row=6, column=0, columnspan=2, pady=20)

    def _save(self):
        try:
            wdays  = int(self._wdays.get())
            dwork  = float(self._dwork.get())
            bonus  = float(self._bonus.get())
            oth    = float(self._oth_ded.get())
            mode   = self._pmmode.get()
            rem    = self._rem.get()
        except ValueError:
            messagebox.showerror("Error", "Invalid numeric value.", parent=self)
            return

        # Supervisory override: saved salary records are locked
        if db.get_salary_record(self.emp_id, self.year, self.month):
            if db.has_password():
                from tkinter import simpledialog
                pwd = simpledialog.askstring(
                    "Supervisory Override",
                    "This month's salary is already saved and locked.\n"
                    "Enter the supervisor password to modify it:",
                    show='*', parent=self)
                if pwd is None:
                    return
                if not db.verify_password(pwd):
                    messagebox.showerror("Denied", "Incorrect password. Record unchanged.", parent=self)
                    return
            else:
                if not messagebox.askyesno(
                        "Locked Record",
                        "This month's salary is already saved and locked.\n"
                        "No supervisor password is set (set one in Settings to enforce this properly).\n\n"
                        "Override and modify anyway?", parent=self):
                    return

        emp = db.get_employee(self.emp_id)
        # Rates in effect for the month being edited, not today's rates
        emp_eff = dict(emp)
        emp_eff.update(db.get_rates_for_month(self.emp_id, self.year, self.month))
        company_state = db.get_company().get('state', 'Uttar Pradesh')
        months_remaining = calc.months_remaining_in_fy(self.month)
        ytd_gross, ytd_tds = db.get_ytd_totals(self.emp_id, self.year, self.month)
        sal = calc.compute_salary(emp_eff, wdays, dwork, company_state=company_state,
                                   ytd_gross=ytd_gross, ytd_tds=ytd_tds,
                                   months_remaining=months_remaining)
        calc.apply_extras(sal, additional_earnings=bonus, other_deductions=oth)
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
#  FULL & FINAL SETTLEMENT
# ═══════════════════════════════════════════════════════════════════════════════

class FnFDialog(tk.Toplevel):
    """Exit settlement: gratuity + pending salary days + leave encashment - deductions."""
    def __init__(self, parent, emp_id):
        super().__init__(parent)
        self.emp_id = emp_id
        self.emp = db.get_employee(emp_id)
        self.title(f"Full & Final Settlement — {self.emp['name']}")
        self.geometry("520x520")
        self.configure(bg=C_BG)
        self.grab_set()

        frame = tk.Frame(self, bg=C_BG, padx=25, pady=18)
        frame.pack(fill=tk.BOTH, expand=True)

        per_day_gross = (self.emp['basic'] + self.emp['hra'] + self.emp['da'] +
                         self.emp['special_allowance'] + self.emp['other_allowance'])
        per_day_basic_da = self.emp['basic'] + self.emp['da']

        tk.Label(frame, text=f"Date of Joining: {self.emp.get('doj') or '—'}     "
                             f"Per-day wage (Basic+DA): ₹{per_day_basic_da:,.2f}",
                 font=("Segoe UI", 9), bg=C_BG, fg=C_MUTED).grid(row=0, column=0, columnspan=2, pady=(0, 10), sticky='w')

        def row(lbl, default, row_n):
            tk.Label(frame, text=lbl, font=("Segoe UI", 10, "bold"), bg=C_BG,
                     width=26, anchor='e').grid(row=row_n, column=0, sticky='e', padx=8, pady=7)
            var = tk.StringVar(value=str(default))
            tk.Entry(frame, textvariable=var, width=16, font=("Segoe UI", 10)).grid(
                row=row_n, column=1, sticky='w', pady=7)
            return var

        self._lwd    = row("Last Working Date (YYYY-MM-DD)", datetime.now().strftime('%Y-%m-%d'), 1)
        self._pend_d = row("Unpaid Salary Days", 0, 2)
        self._leave_d = row("Leave Encashment Days", 0, 3)
        self._other  = row("Other Dues (₹)", 0, 4)
        self._deduct = row("Deductions / Recoveries (₹)", 0, 5)

        self._result = tk.Label(frame, text="", font=("Segoe UI", 10), bg=C_WHITE,
                                fg=C_DARK, justify=tk.LEFT, anchor='w', padx=12, pady=10,
                                highlightbackground=C_BORDER, highlightthickness=1)
        self._result.grid(row=6, column=0, columnspan=2, sticky='ew', pady=(12, 4))

        btns = tk.Frame(frame, bg=C_BG)
        btns.grid(row=7, column=0, columnspan=2, pady=12)
        tb.Button(btns, text="🔢 Calculate", command=self._calc, bootstyle="primary").pack(side=tk.LEFT, padx=6)
        tb.Button(btns, text="📄 Generate Settlement PDF", command=self._generate, bootstyle="success").pack(side=tk.LEFT, padx=6)

        self._calc()

    def _values(self):
        per_day_gross = (self.emp['basic'] + self.emp['hra'] + self.emp['da'] +
                         self.emp['special_allowance'] + self.emp['other_allowance'])
        per_day_basic_da = self.emp['basic'] + self.emp['da']
        try:
            lwd = self._lwd.get().strip()
            pend_d = float(self._pend_d.get() or 0)
            leave_d = float(self._leave_d.get() or 0)
            other = float(self._other.get() or 0)
            deduct = float(self._deduct.get() or 0)
        except ValueError:
            raise ValueError("Invalid numeric value.")

        eligible, years, gratuity = calc.calculate_gratuity(self.emp.get('doj', ''), lwd, per_day_basic_da)
        pending = round(per_day_gross * pend_d, 2)
        leave_enc = round(per_day_basic_da * leave_d, 2)
        total = round(gratuity + pending + leave_enc + other - deduct, 2)
        return {
            'last_working_date': lwd, 'eligible': eligible, 'years': years,
            'gratuity': gratuity, 'pending_days': pend_d, 'pending_amount': pending,
            'leave_days': leave_d, 'leave_amount': leave_enc,
            'other_dues': other, 'deductions': deduct, 'total': total,
        }

    def _calc(self):
        try:
            v = self._values()
        except ValueError as ex:
            messagebox.showerror("Error", str(ex), parent=self)
            return None
        grat_line = (f"Gratuity ({v['years']} yrs): ₹{v['gratuity']:,.2f}" if v['eligible']
                     else "Gratuity: Not eligible (under 5 years of service)")
        lines = [
            grat_line,
            f"Pending salary ({v['pending_days']:g} days): ₹{v['pending_amount']:,.2f}",
            f"Leave encashment ({v['leave_days']:g} days): ₹{v['leave_amount']:,.2f}",
            f"Other dues: ₹{v['other_dues']:,.2f}    Deductions: −₹{v['deductions']:,.2f}",
            "─────────────────────────────",
            f"NET SETTLEMENT: ₹{v['total']:,.2f}",
        ]
        self._result.config(text="\n".join(lines))
        return v

    def _generate(self):
        v = self._calc()
        if v is None:
            return
        company = db.get_company()
        path = reports.generate_fnf_statement(company, self.emp, v)
        messagebox.showinfo("Generated", "Settlement statement saved to:\n" + path, parent=self)
        os.startfile(path)


# ═══════════════════════════════════════════════════════════════════════════════
#  LOGIN GATE
# ═══════════════════════════════════════════════════════════════════════════════

class LoginWindow(tb.Window):
    """Shown before the main app if a password has been set. Max 3 attempts."""
    MAX_ATTEMPTS = 3

    def __init__(self):
        super().__init__(themename=UI_THEME)
        self.title("RKE Payroll — Login")
        self.geometry("380x220")
        self.resizable(False, False)
        self.configure(bg=C_BG)
        self.attempts = 0
        self.authenticated = False

        tk.Label(self, text="🔒 RKE Payroll", font=("Segoe UI", 16, "bold"),
                 bg=C_BG, fg=C_SIDEBAR).pack(pady=(25, 5))
        tk.Label(self, text="Enter password to continue", font=("Segoe UI", 10),
                 bg=C_BG, fg="#666").pack(pady=(0, 15))

        self._pwd_var = tk.StringVar()
        entry = tk.Entry(self, textvariable=self._pwd_var, show='*', font=("Segoe UI", 11), width=26)
        entry.pack(pady=5)
        entry.focus_set()
        entry.bind('<Return>', lambda e: self._try_login())

        self._err_label = tk.Label(self, text="", font=("Segoe UI", 9), bg=C_BG, fg=C_RED)
        self._err_label.pack(pady=(5, 0))

        tb.Button(self, text="Login", command=self._try_login, bootstyle="primary").pack(pady=15)

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
