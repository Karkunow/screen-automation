"""
app.py
Simple tkinter GUI for the screen automation project.
Provides: Calibration wizard, Automation runner, Config editor.

Usage:
    python app.py          (with console)
    pythonw app.py         (no console window — preferred)
    double-click launch.bat
"""

import json
import os
import queue
import subprocess
import sys
import threading
import tkinter as tk
from tkinter import messagebox, scrolledtext, ttk

import pyautogui

# ── Constants ─────────────────────────────────────────────────────────────────

CONFIG_FILE = "config.json"
ICON_FILE = os.path.join("img", "icon.ico")

# On Windows: suppress the console window for the automation subprocess.
# On macOS/Linux: getattr returns 0 (no-op, safe to pass).
_CREATE_NO_WINDOW = getattr(subprocess, "CREATE_NO_WINDOW", 0)

DEFAULT_DELAYS = {
    "window_switch": 0.7,
    "after_copy": 0.4,
    "after_type_ipn": 0.5,
    "tooltip_timeout": 15.0,
    "batch_confirm_wait": 3.0,
    "batch_reopen_wait": 12.0,
}

# ── Config helpers ─────────────────────────────────────────────────────────────

def _load_config() -> dict:
    try:
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


def _save_config(cfg: dict) -> None:
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(cfg, f, ensure_ascii=False, indent=2)


# ── Calibration wizard steps ───────────────────────────────────────────────────

CALIB_STEPS = [
    {
        "id": "ipn_cell",
        "title": "Крок 1 / 7",
        "subtitle": "Перша клітинка ІПН в Excel",
        "type": "coord",
        "instruction": (
            "1. Відкрий Excel з даними.\n"
            "2. Дані мають починатись з рядка 2 (рядок 1 = заголовки).\n"
            "3. Натисни «Старт відліку», переключись на Excel\n"
            "   і наведи мишу на першу клітинку ІПН."
        ),
        "config_keys": ("ipn_cell_x", "ipn_cell_y"),
        "is_xy_pair": True,
    },
    {
        "id": "row_count",
        "title": "Крок 2 / 7",
        "subtitle": "Кількість рядків",
        "type": "int",
        "instruction": "Скільки рядків з даними потрібно обробити?",
        "config_key": "row_count",
        "default": 50,
    },
    {
        "id": "mia_tl",
        "title": "Крок 3 / 7",
        "subtitle": "MIA: верхній лівий кут клітинки ІПН",
        "type": "coord",
        "instruction": (
            "1. Переключись на вікно MIA ('Обіймання посад').\n"
            "2. Знайди ПЕРШИЙ рядок з даними у стовпці 'Ідентифікатор'.\n"
            "3. Натисни «Старт відліку» і наведи мишу\n"
            "   на ВЕРХНІЙ ЛІВИЙ кут першого рядка ІПН."
        ),
        "config_keys": ("mia_ipn_cell_tl",),
        "is_list": True,
    },
    {
        "id": "mia_br",
        "title": "Крок 4 / 7",
        "subtitle": "MIA: нижній правий кут клітинки ІПН",
        "type": "coord",
        "instruction": (
            "1. Залишся у вікні MIA — той самий перший рядок.\n"
            "2. Натисни «Старт відліку» і наведи мишу\n"
            "   на НИЖНІЙ ПРАВИЙ кут тієї самої клітинки ІПН."
        ),
        "config_keys": ("mia_ipn_cell_br",),
        "is_list": True,
    },
    {
        "id": "mia_col_br",
        "title": "Крок 5 / 7",
        "subtitle": "MIA: нижній правий кут стовпця ІПН",
        "type": "coord",
        "instruction": (
            "1. Залишся у вікні MIA.\n"
            "2. Знайди ОСТАННІЙ видимий рядок у стовпці 'Ідентифікатор'.\n"
            "3. Натисни «Старт відліку» і наведи мишу\n"
            "   на НИЖНІЙ ПРАВИЙ кут останнього рядка."
        ),
        "config_keys": ("mia_ipn_col_br",),
        "is_list": True,
    },
    {
        "id": "checkbox",
        "title": "Крок 6 / 7",
        "subtitle": "MIA: позиція галочки",
        "type": "coord",
        "instruction": (
            "1. Залишся у вікні MIA — перший рядок.\n"
            "2. Натисни «Старт відліку» і наведи мишу\n"
            "   ТОЧНО на галочку зліва від першого рядка.\n"
            "   (Зберігається як зміщення відносно cell_tl.)"
        ),
        "config_keys": ("mia_checkbox_offset",),
        "is_offset": True,
    },
    {
        "id": "mia_title",
        "title": "Крок 7 / 7",
        "subtitle": "Назва вікна MIA",
        "type": "str",
        "instruction": "Введи фрагмент назви вікна MIA (частина заголовка).",
        "config_key": "mia_title_part",
        "default": "Обіймання посад",
    },
]


# ── Countdown overlay ──────────────────────────────────────────────────────────

class _CountdownOverlay(tk.Toplevel):
    """Small always-on-top countdown shown while the user positions the mouse."""

    def __init__(self, parent, seconds: int, on_done):
        super().__init__(parent)
        self.overrideredirect(True)
        self.attributes("-topmost", True)
        sw = self.winfo_screenwidth()
        self.geometry(f"90x90+{sw - 110}+20")
        self._remaining = seconds
        self._on_done = on_done
        bg = "#1e3a8a"
        self.configure(bg=bg)
        self._lbl = tk.Label(
            self, text=str(seconds),
            font=("Arial", 52, "bold"), fg="white", bg=bg, width=2,
        )
        self._lbl.pack(fill="both", expand=True)
        self._tick()

    def _tick(self):
        if self._remaining > 0:
            self._lbl.config(text=str(self._remaining))
            self._remaining -= 1
            self.after(1000, self._tick)
        else:
            self._lbl.config(text="✓")
            x, y = pyautogui.position()
            self.after(300, lambda: self._finish(x, y))

    def _finish(self, x: int, y: int):
        self.destroy()
        self._on_done(x, y)


# ── Calibration wizard ─────────────────────────────────────────────────────────

class CalibrationWizard(tk.Toplevel):
    """Step-by-step calibration dialog — no console window needed."""

    COUNTDOWN = 7

    def __init__(self, parent: tk.Tk, config: dict, on_done):
        super().__init__(parent)
        self.title("Калібрування")
        self.resizable(False, True)
        self.minsize(480, 380)
        self._config = dict(config)
        self._on_done = on_done
        self._step_idx = 0
        self._captured_this_step = False

        outer = ttk.Frame(self, padding=16)
        outer.pack(fill="both", expand=True)

        # Step header
        self._title_lbl = ttk.Label(outer, font=("Arial", 11, "bold"))
        self._title_lbl.pack(anchor="w")
        self._sub_lbl = ttk.Label(outer, font=("Arial", 9), foreground="#555")
        self._sub_lbl.pack(anchor="w", pady=(0, 8))

        # Instruction text
        self._instr = tk.Text(
            outer, width=52, height=5, wrap="word", relief="flat",
            bg=self.cget("bg"), font=("Arial", 9), state="disabled",
        )
        self._instr.pack(fill="x")

        # Current value hint
        self._cur_lbl = ttk.Label(outer, foreground="#888", font=("Arial", 9, "italic"))
        self._cur_lbl.pack(anchor="w", pady=(4, 0))

        # Entry area (for int/str steps)
        self._entry_frame = ttk.Frame(outer)
        self._entry_frame.pack(fill="x", pady=(6, 0))
        self._entry_var = tk.StringVar()

        # Capture result
        self._result_lbl = ttk.Label(outer, foreground="#16a34a", font=("Arial", 9, "bold"))
        self._result_lbl.pack(anchor="w", pady=(4, 0))

        # Buttons row
        btn_row = ttk.Frame(outer)
        btn_row.pack(fill="x", pady=(14, 0))
        self._skip_btn = ttk.Button(btn_row, text="Пропустити", command=self._skip)
        self._skip_btn.pack(side="left")
        ttk.Button(btn_row, text="◀ Назад", command=self._back).pack(side="left", padx=4)
        self._action_btn = ttk.Button(btn_row, text="Далі", command=self._action)
        self._action_btn.pack(side="right")

        self._render_step()
        self._center()

    def _center(self):
        self.update_idletasks()
        w = max(self.winfo_reqwidth(), 480)
        h = max(self.winfo_reqheight(), 380)
        sw, sh = self.winfo_screenwidth(), self.winfo_screenheight()
        self.geometry(f"{w}x{h}+{(sw - w) // 2}+{(sh - h) // 2}")

    # ── Step rendering ────────────────────────────────────────────────────────

    def _render_step(self):
        step = CALIB_STEPS[self._step_idx]
        self._captured_this_step = False

        self._title_lbl.config(text=step["title"])
        self._sub_lbl.config(text=step["subtitle"])

        self._instr.config(state="normal")
        self._instr.delete("1.0", "end")
        self._instr.insert("1.0", step["instruction"])
        self._instr.config(state="disabled")

        self._result_lbl.config(text="")

        # Current value
        cur = self._current_value(step)
        if cur is not None:
            self._cur_lbl.config(text=f"Поточне: {cur}")
            self._skip_btn.config(state="normal")
        else:
            self._cur_lbl.config(text="Ще не скалібровано")
            self._skip_btn.config(state="disabled")

        # Clear entry area
        for w in self._entry_frame.winfo_children():
            w.destroy()

        if step["type"] in ("int", "str"):
            default = str(self._config.get(step["config_key"], step.get("default", "")))
            self._entry_var.set(default)
            ttk.Entry(self._entry_frame, textvariable=self._entry_var, width=32).pack(anchor="w")
            self._action_btn.config(text="Далі ▶", command=self._action)
        else:
            self._action_btn.config(text="Старт відліку", command=self._action)

        self._action_btn.config(state="normal")

    def _current_value(self, step: dict):
        if step["type"] == "coord":
            keys = step["config_keys"]
            if step.get("is_xy_pair"):
                x = self._config.get(keys[0])
                y = self._config.get(keys[1])
                return f"({x}, {y})" if x is not None else None
            else:
                v = self._config.get(keys[0])
                return str(v) if v is not None else None
        else:
            v = self._config.get(step["config_key"])
            return str(v) if v is not None else None

    # ── Actions ───────────────────────────────────────────────────────────────

    def _action(self):
        step = CALIB_STEPS[self._step_idx]

        if step["type"] in ("int", "str"):
            raw = self._entry_var.get().strip()
            if step["type"] == "int":
                if not raw.isdigit():
                    messagebox.showerror("Помилка", "Введи ціле число.", parent=self)
                    return
                self._config[step["config_key"]] = int(raw)
            else:
                if not raw:
                    messagebox.showerror("Помилка", "Поле не може бути порожнім.", parent=self)
                    return
                self._config[step["config_key"]] = raw
            self._advance()
        else:
            # Coordinate step: start countdown
            self._action_btn.config(state="disabled")
            self._skip_btn.config(state="disabled")
            self.withdraw()
            _CountdownOverlay(self, self.COUNTDOWN, self._coord_captured)

    def _coord_captured(self, x: int, y: int):
        self.deiconify()
        step = CALIB_STEPS[self._step_idx]

        if step.get("is_offset"):
            tl = self._config.get("mia_ipn_cell_tl") or [0, 0]
            dx, dy = x - tl[0], y - tl[1]
            self._config["mia_checkbox_offset"] = [dx, dy]
            self._result_lbl.config(text=f"✓ Зафіксовано: dx={dx}, dy={dy}")
        elif step.get("is_list"):
            self._config[step["config_keys"][0]] = [x, y]
            self._result_lbl.config(text=f"✓ Зафіксовано: ({x}, {y})")
        else:  # is_xy_pair
            self._config[step["config_keys"][0]] = x
            self._config[step["config_keys"][1]] = y
            self._result_lbl.config(text=f"✓ Зафіксовано: ({x}, {y})")

        self._captured_this_step = True
        self._skip_btn.config(state="normal")
        self._action_btn.config(text="Далі ▶", command=self._advance, state="normal")

    def _advance(self):
        self._action_btn.config(command=self._action)  # reset for next step
        if self._step_idx < len(CALIB_STEPS) - 1:
            self._step_idx += 1
            self._render_step()
        else:
            self._finish()

    def _back(self):
        if self._step_idx > 0:
            self._step_idx -= 1
            self._render_step()

    def _skip(self):
        self._action_btn.config(command=self._action)
        if self._step_idx < len(CALIB_STEPS) - 1:
            self._step_idx += 1
            self._render_step()
        else:
            self._finish()

    def _finish(self):
        _save_config(self._config)
        messagebox.showinfo("Калібрування завершено",
                            "Конфіг збережено успішно!", parent=self)
        self.destroy()
        self._on_done(self._config)


# ── Main App ───────────────────────────────────────────────────────────────────

class App(tk.Tk):

    def __init__(self):
        super().__init__()
        self.title("Автоматизація MIA")
        self.minsize(900, 580)
        self._set_icon()

        self._config: dict = _load_config()
        self._proc: subprocess.Popen | None = None
        self._out_queue: queue.Queue = queue.Queue()
        self._polling = False

        self._form_vars: dict[str, tk.StringVar] = {}
        self._coord_labels: dict[str, ttk.Label] = {}

        self._build_ui()
        self._populate_form()
        self._update_coord_labels()
        self._set_status("Готово")

    def _set_icon(self):
        if os.path.exists(ICON_FILE):
            try:
                self.iconbitmap(ICON_FILE)
            except Exception:
                pass

    # ── UI construction ────────────────────────────────────────────────────────

    def _build_ui(self):
        # Top title bar
        top = ttk.Frame(self, padding=(10, 8, 10, 4))
        top.pack(fill="x")
        ttk.Label(top, text="Автоматизація MIA",
                  font=("Arial", 13, "bold")).pack(side="left")

        # Main paned area
        paned = tk.PanedWindow(self, orient="horizontal",
                               sashrelief="raised", sashwidth=5,
                               bg="#d1d5db")
        paned.pack(fill="both", expand=True, padx=8, pady=(0, 4))

        left = ttk.Frame(paned, padding=(0, 4, 8, 4))
        right = ttk.Frame(paned, padding=(8, 4, 0, 4))
        paned.add(left, minsize=280, width=310)
        paned.add(right, minsize=420)

        self._build_left(left)
        self._build_right(right)

        # Status bar
        self._status_var = tk.StringVar(value="")
        ttk.Label(self, textvariable=self._status_var,
                  relief="sunken", anchor="w",
                  padding=(8, 2)).pack(fill="x", side="bottom")

    def _build_left(self, parent):
        # ── Action buttons ────────────────────────────────────────────────────
        act = ttk.LabelFrame(parent, text="Дії", padding=8)
        act.pack(fill="x", pady=(0, 8))

        ttk.Button(act, text="Калібрація",
                   command=self._open_wizard).pack(side="left")
        self._run_btn = ttk.Button(act, text="▶  Запустити",
                                   command=self._start_automation)
        self._run_btn.pack(side="left", padx=6)
        self._stop_btn = ttk.Button(act, text="■  Зупинити",
                                    command=self._stop_automation,
                                    state="disabled")
        self._stop_btn.pack(side="left")

        # ── Settings form ─────────────────────────────────────────────────────
        sf = ttk.LabelFrame(parent, text="Налаштування", padding=8)
        sf.pack(fill="x", pady=(0, 8))

        def _field(label: str, key: str, row: int, width: int = 10):
            ttk.Label(sf, text=label).grid(row=row, column=0, sticky="w", pady=2)
            var = tk.StringVar()
            ttk.Entry(sf, textvariable=var, width=width).grid(
                row=row, column=1, sticky="w", padx=(8, 0), pady=2)
            self._form_vars[key] = var

        _field("Рядків:", "row_count", 0)
        _field("Батч:", "batch_size", 1)

        ttk.Label(sf, text="Назва MIA:").grid(row=2, column=0, sticky="w", pady=2)
        mia_var = tk.StringVar()
        ttk.Entry(sf, textvariable=mia_var, width=22).grid(
            row=2, column=1, sticky="w", padx=(8, 0), pady=2)
        self._form_vars["mia_title_part"] = mia_var

        ttk.Separator(sf, orient="horizontal").grid(
            row=3, column=0, columnspan=2, sticky="ew", pady=6)
        ttk.Label(sf, text="Затримки (с):",
                  font=("Arial", 8, "bold")).grid(
            row=4, column=0, columnspan=2, sticky="w")

        delays_rows = [
            ("Перемикання вікна:", "window_switch"),
            ("Після копіювання:", "after_copy"),
            ("Після вводу ІПН:", "after_type_ipn"),
            ("Очікування tooltip:", "tooltip_timeout"),
            ("Підтвердження батчу:", "batch_confirm_wait"),
            ("Перевідкриття батчу:", "batch_reopen_wait"),
        ]
        for i, (lbl, key) in enumerate(delays_rows):
            ttk.Label(sf, text=lbl).grid(row=5 + i, column=0, sticky="w", pady=1)
            var = tk.StringVar()
            ttk.Entry(sf, textvariable=var, width=8).grid(
                row=5 + i, column=1, sticky="w", padx=(8, 0), pady=1)
            self._form_vars[f"delay_{key}"] = var

        # ── Coordinates (read-only) ───────────────────────────────────────────
        cf = ttk.LabelFrame(parent, text="Координати (тільки калібрація)", padding=8)
        cf.pack(fill="x", pady=(0, 8))
        cf.columnconfigure(1, weight=1)

        coord_rows = [
            ("IPN клітинка:", "ipn_cell"),
            ("MIA TL:", "mia_ipn_cell_tl"),
            ("MIA BR:", "mia_ipn_cell_br"),
            ("MIA col BR:", "mia_ipn_col_br"),
            ("Checkbox Δ:", "mia_checkbox_offset"),
        ]
        for i, (lbl, key) in enumerate(coord_rows):
            ttk.Label(cf, text=lbl).grid(row=i, column=0, sticky="w", pady=1)
            val_lbl = ttk.Label(cf, text="—", foreground="#888",
                                font=("Consolas", 8))
            val_lbl.grid(row=i, column=1, sticky="w", padx=(8, 0), pady=1)
            self._coord_labels[key] = val_lbl

        # Save button
        ttk.Button(parent, text="Зберегти конфіг",
                   command=self._save_form).pack(fill="x")

    def _build_right(self, parent):
        hdr = ttk.Frame(parent)
        hdr.pack(fill="x", pady=(0, 4))
        ttk.Label(hdr, text="Консоль", font=("Arial", 9, "bold")).pack(side="left")
        ttk.Button(hdr, text="Очистити",
                   command=self._clear_console).pack(side="right")

        self._console = scrolledtext.ScrolledText(
            parent,
            state="disabled",
            wrap="word",
            font=("Consolas", 9),
            bg="#0f172a",
            fg="#e2e8f0",
            insertbackground="white",
            selectbackground="#334155",
        )
        self._console.pack(fill="both", expand=True)

    # ── Form helpers ───────────────────────────────────────────────────────────

    def _populate_form(self):
        cfg = self._config
        delays = cfg.get("delays", {})

        def _set(key: str, val):
            if key in self._form_vars:
                self._form_vars[key].set("" if val is None else str(val))

        _set("row_count", cfg.get("row_count", 50))
        _set("batch_size", cfg.get("batch_size", 20))
        _set("mia_title_part", cfg.get("mia_title_part", "Обіймання посад"))
        for key in DEFAULT_DELAYS:
            _set(f"delay_{key}", delays.get(key, DEFAULT_DELAYS[key]))

    def _update_coord_labels(self):
        cfg = self._config

        x, y = cfg.get("ipn_cell_x"), cfg.get("ipn_cell_y")
        self._coord_labels["ipn_cell"].config(
            text=f"({x}, {y})" if x is not None else "—",
            foreground="#16a34a" if x is not None else "#888",
        )
        for key in ("mia_ipn_cell_tl", "mia_ipn_cell_br",
                    "mia_ipn_col_br", "mia_checkbox_offset"):
            v = cfg.get(key)
            self._coord_labels[key].config(
                text=str(v) if v is not None else "—",
                foreground="#16a34a" if v is not None else "#888",
            )

    def _save_form(self):
        try:
            cfg = dict(self._config)
            rc = self._form_vars["row_count"].get().strip()
            bs = self._form_vars["batch_size"].get().strip()
            if not rc.isdigit() or not bs.isdigit():
                raise ValueError("Рядків і Батч мають бути цілими числами")
            cfg["row_count"] = int(rc)
            cfg["batch_size"] = int(bs)
            mia = self._form_vars["mia_title_part"].get().strip()
            if not mia:
                raise ValueError("Назва MIA не може бути порожньою")
            cfg["mia_title_part"] = mia

            delays = dict(cfg.get("delays", {}))
            for key in DEFAULT_DELAYS:
                raw = self._form_vars[f"delay_{key}"].get().strip()
                delays[key] = float(raw)
            cfg["delays"] = delays

            self._config = cfg
            _save_config(cfg)
            self._set_status("Конфіг збережено ✓")
        except ValueError as exc:
            messagebox.showerror("Помилка збереження",
                                 f"Невірне значення: {exc}", parent=self)

    # ── Calibration ────────────────────────────────────────────────────────────

    def _open_wizard(self):
        CalibrationWizard(self, self._config, self._on_calib_done)

    def _on_calib_done(self, new_cfg: dict):
        self._config = new_cfg
        self._populate_form()
        self._update_coord_labels()
        self._set_status("Калібрування завершено ✓")

    # ── Automation ─────────────────────────────────────────────────────────────

    def _automation_cmd(self) -> list:
        """Return Popen command list to launch automation.
        Frozen exe: call automation.exe sitting next to app.exe.
        Dev mode:   call python automation.py using the current interpreter.
        """
        if getattr(sys, 'frozen', False):
            return [os.path.join(os.path.dirname(sys.executable), 'automation.exe')]
        exe = sys.executable
        if os.path.basename(exe).lower() == 'pythonw.exe':
            candidate = os.path.join(os.path.dirname(exe), 'python.exe')
            if os.path.exists(candidate):
                exe = candidate
        return [exe, 'automation.py']

    def _start_automation(self):
        if self._proc is not None:
            return
        env = {**os.environ, "PYTHONIOENCODING": "utf-8", "PYTHONUTF8": "1"}
        try:
            self._proc = subprocess.Popen(
                self._automation_cmd(),
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                encoding="utf-8",
                errors="replace",
                creationflags=_CREATE_NO_WINDOW,
                env=env,
            )
        except Exception as exc:
            messagebox.showerror("Помилка запуску", str(exc), parent=self)
            return

        self._run_btn.config(state="disabled")
        self._stop_btn.config(state="normal")
        self._set_status("Автоматизація запущена…")
        self._console_write("─" * 52 + "\n")

        threading.Thread(target=self._reader_thread, daemon=True).start()
        self._polling = True
        self._poll_output()

    def _reader_thread(self):
        assert self._proc and self._proc.stdout
        for line in self._proc.stdout:
            self._out_queue.put(line)
        self._out_queue.put(None)  # sentinel — process finished

    def _poll_output(self):
        try:
            while True:
                line = self._out_queue.get_nowait()
                if line is None:
                    self._on_automation_done()
                    return
                self._console_write(line)
        except queue.Empty:
            pass
        if self._polling:
            self.after(100, self._poll_output)

    def _on_automation_done(self):
        self._polling = False
        self._proc = None
        self._run_btn.config(state="normal")
        self._stop_btn.config(state="disabled")
        self._console_write("─" * 52 + "\n")
        self._set_status("Автоматизацію завершено")

    def _stop_automation(self):
        if self._proc:
            self._proc.terminate()
            self._proc = None
        self._polling = False
        self._run_btn.config(state="normal")
        self._stop_btn.config(state="disabled")
        self._console_write("\n[ЗУПИНЕНО ВРУЧНУ]\n")
        self._set_status("Автоматизацію зупинено")

    # ── Console ────────────────────────────────────────────────────────────────

    def _console_write(self, text: str):
        self._console.config(state="normal")
        self._console.insert("end", text)
        self._console.see("end")
        self._console.config(state="disabled")

    def _clear_console(self):
        self._console.config(state="normal")
        self._console.delete("1.0", "end")
        self._console.config(state="disabled")

    # ── Status bar ─────────────────────────────────────────────────────────────

    def _set_status(self, msg: str):
        self._status_var.set(msg)


if __name__ == "__main__":
    app = App()
    app.mainloop()
