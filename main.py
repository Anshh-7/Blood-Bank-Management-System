import json
import math
import tkinter as tk
from dataclasses import asdict, dataclass
from functools import reduce, wraps
from pathlib import Path
from tkinter import messagebox, ttk


APP_TITLE = "LifeFlow Blood Bank"
DATA_FILE = Path(__file__).with_name("bbms_data.json")

PALETTE = {
    "bg": "#F3F6FA",
    "panel": "#FFFFFF",
    "soft": "#F8FAFD",
    "ink": "#182230",
    "muted": "#667085",
    "line": "#D9E2EC",
    "nav": "#111827",
    "red": "#D92D20",
    "red_dark": "#B42318",
    "blue": "#2563EB",
    "green": "#039855",
    "amber": "#DC8A00",
    "purple": "#7C3AED",
}

BLOOD_GROUPS = ["A+", "A-", "B+", "B-", "AB+", "AB-", "O+", "O-"]

COMPATIBILITY = {
    "A+": ["A+", "A-", "O+", "O-"],
    "A-": ["A-", "O-"],
    "B+": ["B+", "B-", "O+", "O-"],
    "B-": ["B-", "O-"],
    "AB+": ["A+", "A-", "B+", "B-", "AB+", "AB-", "O+", "O-"],
    "AB-": ["A-", "B-", "AB-", "O-"],
    "O+": ["O+", "O-"],
    "O-": ["O-"],
}

DEFAULT_DATA = {
    "donors": [
        {"name": "Aarav Mehta", "age": 28, "phone": "9876543210", "blood_group": "O+", "city": "Delhi", "last_donation": "2026-05-02"},
        {"name": "Kabir Khan", "age": 32, "phone": "9900011122", "blood_group": "B+", "city": "Mumbai", "last_donation": "2026-03-10"},
    ],
    "recipients": [
        {"name": "Neha Verma", "age": 19, "phone": "9000012345", "blood_group": "A+", "city": "Delhi", "hospital": "City Care Hospital"},
        {"name": "Rohan Das", "age": 41, "phone": "9888800000", "blood_group": "O-", "city": "Kolkata", "hospital": "Metro Health"},
    ],
    "inventory": {"A+": 6, "A-": 3, "B+": 5, "B-": 2, "AB+": 4, "AB-": 1, "O+": 8, "O-": 2},
    "requests": [
        {"patient": "Neha Verma", "blood_group": "A+", "units": 2, "hospital": "City Care Hospital", "status": "Approved"},
        {"patient": "Rohan Das", "blood_group": "O-", "units": 1, "hospital": "Metro Health", "status": "Pending"},
    ],
}


def safe_action(action):
    """Decorator: catches GUI errors and shows them cleanly."""

    @wraps(action)
    def wrapper(*args, **kwargs):
        try:
            return action(*args, **kwargs)
        except Exception as exc:
            messagebox.showerror("Action failed", str(exc))
            return None

    return wrapper


def required_validator(*fields):
    """Closure: returns a validator that remembers required field names."""

    def validate(values):
        missing = [field for field in fields if not str(values.get(field, "")).strip()]
        if missing:
            raise ValueError(f"Please fill: {', '.join(missing)}")

    return validate


def stock_alerts(inventory):
    """Generator: yields low-stock blood groups one by one."""
    for group, units in inventory.items():
        if units <= 2:
            yield f"{group} has only {units} unit(s)"


@dataclass
class Person:
    name: str
    age: int
    phone: str
    blood_group: str
    city: str


@dataclass
class Donor(Person):
    last_donation: str

    def summary(self):
        return f"{self.name} can donate {self.blood_group} blood"


@dataclass
class Recipient(Person):
    hospital: str

    def summary(self):
        return f"{self.name} needs {self.blood_group} at {self.hospital}"


@dataclass
class BloodRequest:
    patient: str
    blood_group: str
    units: int
    hospital: str
    status: str = "Pending"


class BloodBankStore:
    def __init__(self, path):
        self.path = path
        self.data = self.load()

    def load(self):
        if not self.path.exists():
            return json.loads(json.dumps(DEFAULT_DATA))
        try:
            return json.loads(self.path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            messagebox.showwarning("Data warning", "Saved data was unreadable. Starting with demo data.")
            return json.loads(json.dumps(DEFAULT_DATA))

    def save(self):
        self.path.write_text(json.dumps(self.data, indent=2), encoding="utf-8")

    def donors(self):
        return [Donor(**record) for record in self.data["donors"]]

    def recipients(self):
        return [Recipient(**record) for record in self.data["recipients"]]

    def requests(self):
        return [BloodRequest(**record) for record in self.data["requests"]]

    def add_donor(self, donor):
        self.data["donors"].append(asdict(donor))
        self.data["inventory"][donor.blood_group] += 1
        self.save()

    def add_recipient(self, recipient):
        self.data["recipients"].append(asdict(recipient))
        self.save()

    def add_request(self, request):
        available = self.data["inventory"][request.blood_group]
        if available >= request.units:
            self.data["inventory"][request.blood_group] -= request.units
            request.status = "Approved"
        self.data["requests"].append(asdict(request))
        self.save()

    def update_stock(self, group, units):
        self.data["inventory"][group] = max(0, units)
        self.save()


class LifeFlowApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title(APP_TITLE)
        self.geometry("1180x740")
        self.minsize(980, 640)
        self.configure(bg=PALETTE["bg"])
        self.store = BloodBankStore(DATA_FILE)
        self.current_user = None
        self.style = ttk.Style(self)
        self.configure_styles()
        self.show_login()

    def configure_styles(self):
        self.style.theme_use("clam")
        self.style.configure("Treeview", rowheight=30, font=("Segoe UI", 10), background=PALETTE["panel"], fieldbackground=PALETTE["panel"])
        self.style.configure("Treeview.Heading", font=("Segoe UI", 10, "bold"), background="#EEF2F7", foreground=PALETTE["ink"])
        self.style.map("Treeview", background=[("selected", "#FEE4E2")], foreground=[("selected", PALETTE["ink"])])
        self.style.configure("TCombobox", padding=6)

    def clear(self):
        for widget in self.winfo_children():
            widget.destroy()

    # def logo(self, parent, size=92, background=PALETTE["panel"]):
    #     canvas = tk.Canvas(parent, width=size, height=size, bg=background, highlightthickness=0)
    #     c = size / 2
    #     canvas.create_oval(c - 34, c - 34, c + 34, c + 34, fill="#FEE4E2", outline="")
    #     canvas.create_polygon(c, 12, c - 22, c + 18, c, c + 42, c + 22, c + 18, fill=PALETTE["red"], outline="")
    #     canvas.create_oval(c - 22, c + 4, c + 22, c + 48, fill=PALETTE["red"], outline="")
    #     for index, color in enumerate([PALETTE["blue"], PALETTE["green"], PALETTE["amber"]]):
    #         angle = math.radians(25 + index * 120)
    #         x = c + math.cos(angle) * 37
    #         y = c + math.sin(angle) * 37
    #         canvas.create_line(c, c + 18, x, y, fill="#CBD5E1", width=2)
    #         canvas.create_oval(x - 6, y - 6, x + 6, y + 6, fill=color, outline="")
    #     canvas.create_text(c, c + 16, text="BB", fill="white", font=("Segoe UI", int(size * 0.18), "bold"))
    #     return canvas

    def button(self, parent, text, command, color=PALETTE["red"], width=16):
        return tk.Button(
            parent,
            text=text,
            command=command,
            bg=color,
            fg="white",
            activebackground=color,
            activeforeground="white",
            relief="flat",
            cursor="hand2",
            font=("Segoe UI", 10, "bold"),
            padx=12,
            pady=9,
            width=width,
        )

    def label_entry(self, parent, label, row, column, values=None):
        tk.Label(parent, text=label, bg=PALETTE["panel"], fg=PALETTE["ink"], font=("Segoe UI", 9, "bold")).grid(row=row, column=column, sticky="w", padx=8, pady=(8, 2))
        if values:
            field = ttk.Combobox(parent, values=values, state="readonly", font=("Segoe UI", 10))
            field.current(0)
        else:
            field = tk.Entry(parent, font=("Segoe UI", 10), relief="solid", bd=1)
        field.grid(row=row + 1, column=column, sticky="ew", padx=8, pady=(0, 8), ipady=5)
        return field

    def show_login(self):
        self.clear()
        self.rowconfigure(0, weight=1)
        self.columnconfigure(0, weight=1)

        shell = tk.Frame(self, bg=PALETTE["bg"])
        shell.grid(sticky="nsew")
        shell.rowconfigure(0, weight=1)
        shell.columnconfigure((0, 1), weight=1)

        hero = tk.Frame(shell, bg=PALETTE["nav"])
        hero.grid(row=0, column=0, sticky="nsew")
        hero.rowconfigure(0, weight=1)
        hero.columnconfigure(0, weight=1)
        hero_inner = tk.Frame(hero, bg=PALETTE["nav"])
        hero_inner.grid(row=0, column=0)
        # self.logo(hero_inner, 132, PALETTE["nav"]).pack(pady=(0, 22))
        tk.Label(hero_inner, text=APP_TITLE, bg=PALETTE["nav"], fg="white", font=("Segoe UI", 31, "bold")).pack()
        tk.Label(
            hero_inner,
            text="Professional donor, recipient, stock, and request management",
            bg=PALETTE["nav"],
            fg="#CBD5E1",
            font=("Segoe UI", 12),
            wraplength=420,
            justify="center",
        ).pack(pady=(10, 0))

        panel = tk.Frame(shell, bg=PALETTE["panel"])
        panel.grid(row=0, column=1, sticky="nsew")
        panel.rowconfigure(0, weight=1)
        panel.columnconfigure(0, weight=1)
        form = tk.Frame(panel, bg=PALETTE["panel"])
        form.grid(row=0, column=0, padx=72)
        tk.Label(form, text="Secure Login", bg=PALETTE["panel"], fg=PALETTE["ink"], font=("Segoe UI", 27, "bold")).pack(anchor="w")
        tk.Label(form, text="Use admin / admin123 or student / blood123", bg=PALETTE["panel"], fg=PALETTE["muted"], font=("Segoe UI", 11)).pack(anchor="w", pady=(8, 26))

        tk.Label(form, text="Username", bg=PALETTE["panel"], fg=PALETTE["ink"], font=("Segoe UI", 10, "bold")).pack(anchor="w")
        self.username = tk.Entry(form, font=("Segoe UI", 13), relief="solid", bd=1)
        self.username.pack(fill="x", ipady=8, pady=(6, 16))
        tk.Label(form, text="Password", bg=PALETTE["panel"], fg=PALETTE["ink"], font=("Segoe UI", 10, "bold")).pack(anchor="w")
        self.password = tk.Entry(form, font=("Segoe UI", 13), relief="solid", bd=1, show="*")
        self.password.pack(fill="x", ipady=8, pady=(6, 20))
        self.password.bind("<Return>", lambda _event: self.login())
        self.button(form, "Login", self.login, width=32).pack(fill="x")
        self.username.focus_set()

    @safe_action
    def login(self):
        users = {"admin": "admin123", "student": "blood123"}
        username = self.username.get().strip().lower()
        password = self.password.get().strip()
        if users.get(username) != password:
            raise ValueError("Invalid username or password.")
        self.current_user = username.title()
        self.show_shell("dashboard")

    def show_shell(self, page):
        self.clear()
        self.rowconfigure(0, weight=1)
        self.columnconfigure(0, weight=0)
        self.columnconfigure(1, weight=1)

        nav = tk.Frame(self, bg=PALETTE["nav"], width=238)
        nav.grid(row=0, column=0, sticky="nsew")
        nav.grid_propagate(False)

        brand = tk.Frame(nav, bg=PALETTE["nav"])
        brand.pack(fill="x", padx=18, pady=(18, 14))
        # self.logo(brand, 58, PALETTE["nav"]).pack(side="left")
        tk.Label(brand, text="LifeFlow\nBBMS", bg=PALETTE["nav"], fg="white", justify="left", font=("Segoe UI", 14, "bold")).pack(side="left", padx=10)

        pages = [
            ("Dashboard", "dashboard"),
            ("Donors", "donors"),
            ("Recipients", "recipients"),
            ("Blood Stock", "inventory"),
            ("Requests", "requests"),
            ("Reports", "reports"),
        ]
        for label, target in pages:
            active = page == target
            tk.Button(
                nav,
                text=label,
                command=lambda selected=target: self.show_shell(selected),
                anchor="w",
                bg=PALETTE["red"] if active else PALETTE["nav"],
                fg="white",
                activebackground=PALETTE["red_dark"],
                activeforeground="white",
                relief="flat",
                cursor="hand2",
                font=("Segoe UI", 11, "bold" if active else "normal"),
                padx=24,
                pady=13,
            ).pack(fill="x")

        tk.Button(
            nav,
            text="Logout",
            command=self.show_login,
            anchor="w",
            bg=PALETTE["nav"],
            fg="#FECACA",
            activebackground=PALETTE["red_dark"],
            activeforeground="white",
            relief="flat",
            cursor="hand2",
            font=("Segoe UI", 11, "bold"),
            padx=24,
            pady=13,
        ).pack(side="bottom", fill="x", pady=(0, 18))

        content = tk.Frame(self, bg=PALETTE["bg"])
        content.grid(row=0, column=1, sticky="nsew")
        content.rowconfigure(1, weight=1)
        content.columnconfigure(0, weight=1)

        title_map = {
            "dashboard": "Dashboard",
            "donors": "Donor Management",
            "recipients": "Recipient Management",
            "inventory": "Blood Stock",
            "requests": "Blood Requests",
            "reports": "Reports & Python Concepts",
        }
        header = tk.Frame(content, bg=PALETTE["bg"])
        header.grid(row=0, column=0, sticky="ew", padx=28, pady=(22, 8))
        header.columnconfigure(0, weight=1)
        tk.Label(header, text=title_map[page], bg=PALETTE["bg"], fg=PALETTE["ink"], font=("Segoe UI", 25, "bold")).grid(row=0, column=0, sticky="w")
        tk.Label(header, text=f"Logged in as {self.current_user}", bg=PALETTE["bg"], fg=PALETTE["muted"], font=("Segoe UI", 10, "bold")).grid(row=0, column=1, sticky="e")

        page_functions = {
            "dashboard": self.dashboard_page,
            "donors": self.donors_page,
            "recipients": self.recipients_page,
            "inventory": self.inventory_page,
            "requests": self.requests_page,
            "reports": self.reports_page,
        }
        page_functions[page](content)

    def card(self, parent, title=None):
        frame = tk.Frame(parent, bg=PALETTE["panel"], highlightthickness=1, highlightbackground=PALETTE["line"])
        if title:
            frame.title_text = title
        return frame

    def card_title(self, parent, title):
        tk.Label(parent, text=title, bg=PALETTE["panel"], fg=PALETTE["ink"], font=("Segoe UI", 15, "bold")).pack(anchor="w", padx=18, pady=(15, 8))

    def grid_card_title(self, parent, title, columns):
        tk.Label(parent, text=title, bg=PALETTE["panel"], fg=PALETTE["ink"], font=("Segoe UI", 15, "bold")).grid(row=0, column=0, columnspan=columns, sticky="w", padx=18, pady=(15, 8))

    def dashboard_page(self, parent):
        body = tk.Frame(parent, bg=PALETTE["bg"])
        body.grid(row=1, column=0, sticky="nsew", padx=28, pady=12)
        body.columnconfigure((0, 1, 2, 3), weight=1)

        total_units = reduce(lambda total, units: total + units, self.store.data["inventory"].values(), 0)
        approved = len(list(filter(lambda req: req.status == "Approved", self.store.requests())))
        stats = [
            ("Donors", len(self.store.donors()), PALETTE["red"]),
            ("Recipients", len(self.store.recipients()), PALETTE["blue"]),
            ("Available Units", total_units, PALETTE["green"]),
            ("Approved Requests", approved, PALETTE["amber"]),
        ]
        for column, (label, value, color) in enumerate(stats):
            box = self.card(body)
            box.grid(row=0, column=column, sticky="ew", padx=7, ipady=12)
            tk.Label(box, text=label, bg=PALETTE["panel"], fg=PALETTE["muted"], font=("Segoe UI", 10, "bold")).pack(anchor="w", padx=16, pady=(14, 2))
            tk.Label(box, text=value, bg=PALETTE["panel"], fg=color, font=("Segoe UI", 25, "bold")).pack(anchor="w", padx=16, pady=(0, 14))

        quick = self.card(body, "Open Interface")
        quick.grid(row=1, column=0, columnspan=4, sticky="nsew", padx=7, pady=18)
        quick.columnconfigure((0, 1, 2, 3), weight=1)
        self.grid_card_title(quick, "Open Interface", 4)
        actions = [
            ("Register Donor", "Add blood donor data", "donors", PALETTE["red"]),
            ("Add Recipient", "Record patient details", "recipients", PALETTE["blue"]),
            ("Manage Stock", "Update blood inventory", "inventory", PALETTE["green"]),
            ("New Request", "Approve if stock allows", "requests", PALETTE["purple"]),
        ]
        for column, (title, subtitle, page, color) in enumerate(actions):
            tile = tk.Frame(quick, bg=PALETTE["soft"], highlightthickness=1, highlightbackground=PALETTE["line"])
            tile.grid(row=1, column=column, sticky="nsew", padx=12, pady=14)
            tk.Label(tile, text=title, bg=PALETTE["soft"], fg=PALETTE["ink"], font=("Segoe UI", 13, "bold")).pack(anchor="w", padx=14, pady=(14, 3))
            tk.Label(tile, text=subtitle, bg=PALETTE["soft"], fg=PALETTE["muted"], font=("Segoe UI", 9), wraplength=160).pack(anchor="w", padx=14)
            self.button(tile, "Open", lambda selected=page: self.show_shell(selected), color=color, width=10).pack(anchor="w", padx=14, pady=14)

        alerts = list(stock_alerts(self.store.data["inventory"]))
        alert_text = "\n".join(alerts) if alerts else "All blood groups have healthy stock."
        panel = self.card(body, "Stock Alerts")
        panel.grid(row=2, column=0, columnspan=4, sticky="ew", padx=7)
        self.card_title(panel, "Stock Alerts")
        tk.Label(panel, text=alert_text, bg=PALETTE["soft"], fg=PALETTE["ink"], justify="left", font=("Segoe UI", 11)).pack(fill="x", padx=18, pady=(4, 18))

    def donors_page(self, parent):
        body = tk.Frame(parent, bg=PALETTE["bg"])
        body.grid(row=1, column=0, sticky="nsew", padx=28, pady=12)
        body.columnconfigure(0, weight=1)

        form = self.card(body, "Register New Donor")
        form.grid(row=0, column=0, sticky="ew")
        form.columnconfigure((0, 1, 2), weight=1)
        self.grid_card_title(form, "Register New Donor", 3)
        name = self.label_entry(form, "Name", 1, 0)
        age = self.label_entry(form, "Age", 1, 1)
        phone = self.label_entry(form, "Phone", 1, 2)
        group = self.label_entry(form, "Blood Group", 3, 0, BLOOD_GROUPS)
        city = self.label_entry(form, "City", 3, 1)
        date = self.label_entry(form, "Last Donation", 3, 2)
        self.button(form, "Save Donor", lambda: self.save_donor(name, age, phone, group, city, date), width=18).grid(row=5, column=0, sticky="w", padx=8, pady=(8, 16))

        self.people_table(body, "Donor Records", ["Name", "Age", "Phone", "Blood", "City", "Last Donation"], [
            (d.name, d.age, d.phone, d.blood_group, d.city, d.last_donation) for d in self.store.donors()
        ], row=1)

    @safe_action
    def save_donor(self, name, age, phone, group, city, date):
        values = {"name": name.get(), "age": age.get(), "phone": phone.get(), "city": city.get(), "last donation": date.get()}
        required_validator("name", "age", "phone", "city", "last donation")(values)
        donor = Donor(values["name"], int(values["age"]), values["phone"], group.get(), values["city"], values["last donation"])
        self.store.add_donor(donor)
        self.show_shell("donors")

    def recipients_page(self, parent):
        body = tk.Frame(parent, bg=PALETTE["bg"])
        body.grid(row=1, column=0, sticky="nsew", padx=28, pady=12)
        body.columnconfigure(0, weight=1)

        form = self.card(body, "Register New Recipient")
        form.grid(row=0, column=0, sticky="ew")
        form.columnconfigure((0, 1, 2), weight=1)
        self.grid_card_title(form, "Register New Recipient", 3)
        name = self.label_entry(form, "Name", 1, 0)
        age = self.label_entry(form, "Age", 1, 1)
        phone = self.label_entry(form, "Phone", 1, 2)
        group = self.label_entry(form, "Required Blood Group", 3, 0, BLOOD_GROUPS)
        city = self.label_entry(form, "City", 3, 1)
        hospital = self.label_entry(form, "Hospital", 3, 2)
        self.button(form, "Save Recipient", lambda: self.save_recipient(name, age, phone, group, city, hospital), color=PALETTE["blue"], width=18).grid(row=5, column=0, sticky="w", padx=8, pady=(8, 16))

        self.people_table(body, "Recipient Records", ["Name", "Age", "Phone", "Blood", "City", "Hospital"], [
            (r.name, r.age, r.phone, r.blood_group, r.city, r.hospital) for r in self.store.recipients()
        ], row=1)

    @safe_action
    def save_recipient(self, name, age, phone, group, city, hospital):
        values = {"name": name.get(), "age": age.get(), "phone": phone.get(), "city": city.get(), "hospital": hospital.get()}
        required_validator("name", "age", "phone", "city", "hospital")(values)
        recipient = Recipient(values["name"], int(values["age"]), values["phone"], group.get(), values["city"], values["hospital"])
        self.store.add_recipient(recipient)
        self.show_shell("recipients")

    def inventory_page(self, parent):
        body = tk.Frame(parent, bg=PALETTE["bg"])
        body.grid(row=1, column=0, sticky="nsew", padx=28, pady=12)
        body.columnconfigure((0, 1, 2, 3), weight=1)

        for index, group in enumerate(BLOOD_GROUPS):
            row, column = divmod(index, 4)
            card = self.card(body)
            card.grid(row=row, column=column, sticky="ew", padx=7, pady=7)
            units = self.store.data["inventory"][group]
            color = PALETTE["red"] if units <= 2 else PALETTE["green"]
            tk.Label(card, text=group, bg=PALETTE["panel"], fg=PALETTE["ink"], font=("Segoe UI", 18, "bold")).pack(anchor="w", padx=16, pady=(14, 0))
            tk.Label(card, text=f"{units} units", bg=PALETTE["panel"], fg=color, font=("Segoe UI", 22, "bold")).pack(anchor="w", padx=16, pady=(0, 12))
            controls = tk.Frame(card, bg=PALETTE["panel"])
            controls.pack(anchor="w", padx=16, pady=(0, 14))
            self.button(controls, "-1", lambda g=group: self.adjust_stock(g, -1), color=PALETTE["muted"], width=4).pack(side="left", padx=(0, 6))
            self.button(controls, "+1", lambda g=group: self.adjust_stock(g, 1), color=PALETTE["green"], width=4).pack(side="left")

    def adjust_stock(self, group, delta):
        self.store.update_stock(group, self.store.data["inventory"][group] + delta)
        self.show_shell("inventory")

    def requests_page(self, parent):
        body = tk.Frame(parent, bg=PALETTE["bg"])
        body.grid(row=1, column=0, sticky="nsew", padx=28, pady=12)
        body.columnconfigure(0, weight=1)

        form = self.card(body, "Create Blood Request")
        form.grid(row=0, column=0, sticky="ew")
        form.columnconfigure((0, 1, 2, 3), weight=1)
        self.grid_card_title(form, "Create Blood Request", 4)
        patient = self.label_entry(form, "Patient", 1, 0)
        group = self.label_entry(form, "Blood Group", 1, 1, BLOOD_GROUPS)
        units = self.label_entry(form, "Units", 1, 2)
        hospital = self.label_entry(form, "Hospital", 1, 3)
        self.button(form, "Submit Request", lambda: self.save_request(patient, group, units, hospital), color=PALETTE["purple"], width=18).grid(row=3, column=0, sticky="w", padx=8, pady=(8, 16))

        self.people_table(body, "Request History", ["Patient", "Blood", "Units", "Hospital", "Status"], [
            (r.patient, r.blood_group, r.units, r.hospital, r.status) for r in self.store.requests()
        ], row=1)

    @safe_action
    def save_request(self, patient, group, units, hospital):
        values = {"patient": patient.get(), "units": units.get(), "hospital": hospital.get()}
        required_validator("patient", "units", "hospital")(values)
        request = BloodRequest(values["patient"], group.get(), int(values["units"]), values["hospital"])
        self.store.add_request(request)
        messagebox.showinfo("Request saved", f"Request status: {request.status}")
        self.show_shell("requests")

    def reports_page(self, parent):
        body = tk.Frame(parent, bg=PALETTE["bg"])
        body.grid(row=1, column=0, sticky="nsew", padx=28, pady=12)
        body.columnconfigure((0, 1), weight=1)

        compatible = self.card(body, "Compatible Donors Finder")
        compatible.grid(row=0, column=0, sticky="nsew", padx=(0, 9))
        self.card_title(compatible, "Compatible Donors Finder")
        group = ttk.Combobox(compatible, values=BLOOD_GROUPS, state="readonly", font=("Segoe UI", 11))
        group.current(0)
        group.pack(anchor="w", padx=18, pady=(0, 12))
        output = tk.Text(compatible, height=10, font=("Consolas", 10), bg=PALETTE["soft"], relief="flat", wrap="word")
        output.pack(fill="both", expand=True, padx=18, pady=(0, 18))

        def find_matches():
            accepted = COMPATIBILITY[group.get()]
            matches = list(filter(lambda donor: donor.blood_group in accepted, self.store.donors()))
            lines = list(map(lambda donor: donor.summary(), matches))
            output.delete("1.0", "end")
            output.insert("end", "\n".join(lines) if lines else "No compatible donors found.")

        self.button(compatible, "Find Matches", find_matches, color=PALETTE["blue"], width=16).pack(anchor="w", padx=18, pady=(0, 18))

        concepts = self.card(body, "Concepts Used")
        concepts.grid(row=0, column=1, sticky="nsew", padx=(9, 0))
        self.card_title(concepts, "Concepts Used")
        bullets = [
            "Data structures: lists and dictionaries for records and stock",
            "Conditions and loops: validations, navigation, and table loading",
            "Functions: reusable UI builders and save actions",
            "Lambda/map/filter/reduce: reports and dashboard totals",
            "Generators: low-stock alerts",
            "Decorators and closures: safe_action and required_validator",
            "File handling and exceptions: JSON save/load",
            "OOP and advanced OOP: Person, Donor, Recipient, BloodRequest, Store, App",
            "Modules and packages: json, pathlib, dataclasses, functools, tkinter",
        ]
        tk.Label(concepts, text="\n".join(f"- {item}" for item in bullets), bg=PALETTE["soft"], fg=PALETTE["ink"], justify="left", font=("Segoe UI", 10), wraplength=420).pack(fill="both", expand=True, padx=18, pady=(0, 18))

    def people_table(self, parent, title, columns, rows, row):
        panel = self.card(parent, title)
        panel.grid(row=row, column=0, sticky="nsew", pady=18)
        self.card_title(panel, title)
        table = ttk.Treeview(panel, columns=columns, show="headings", height=8)
        for column in columns:
            table.heading(column, text=column)
            table.column(column, anchor="w", width=130)
        for item in rows:
            table.insert("", "end", values=item)
        table.pack(fill="both", expand=True, padx=18, pady=(0, 18))



if __name__ == "__main__":
    app = LifeFlowApp()
    app.mainloop()
