import os
import re
import shutil
from pathlib import Path
import sys
import json
import time
import winreg
import tkinter as tk
from tkinter import messagebox, ttk
import tkinter.simpledialog as simpledialog
from PIL import Image, ImageTk
from ctypes import windll, c_uint

# ── Paths ──────────────────────────────────────────────────────────────────────
def resource_path(filename):
    """Path to a bundled resource (works frozen and unfrozen)."""
    if getattr(sys, 'frozen', False):
        base_path = sys._MEIPASS
    else:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, filename)

if getattr(sys, 'frozen', False):
    BASE_DIR = os.path.dirname(sys.executable)
else:
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Configurator\ → Plugins\ → ORBB\ → repo root
PACK_ROOT = os.path.abspath(os.path.join(BASE_DIR, "..", "..", ".."))

OPTIONS_PATH = os.path.join(BASE_DIR, "configurator_config.json")
DEFAULT_STRUCTURE_JSON = os.path.join(BASE_DIR, "structure.json")

# ── Theme ──────────────────────────────────────────────────────────────────────
CLR_BG        = "#F7F8FA"   # window background
CLR_CARD      = "#FFFFFF"   # card / dialog surface
CLR_BORDER    = "#DDE1E7"   # subtle border
CLR_ACCENT    = "#1A6FBF"   # primary button / header bar
CLR_ACCENT_HV = "#155A9E"   # hover
CLR_TEXT      = "#1C2333"   # primary text
CLR_SUBTEXT   = "#5A6478"   # secondary / hint text
CLR_ERROR     = "#C0392B"   # error red
CLR_SUCCESS   = "#1E7E4A"   # success green

FONT_FAMILY   = "Segoe UI"
FONT_BODY     = (FONT_FAMILY, 10)
FONT_LABEL    = (FONT_FAMILY, 10)
FONT_BOLD     = (FONT_FAMILY, 10, "bold")
FONT_TITLE    = (FONT_FAMILY, 13, "bold")
FONT_HEADER   = (FONT_FAMILY, 11, "bold")
FONT_SMALL    = (FONT_FAMILY, 8)

def apply_theme(root):
    """Apply a clean light theme via ttk.Style."""
    style = ttk.Style(root)
    style.theme_use("clam")

    style.configure(".",
        background=CLR_BG,
        foreground=CLR_TEXT,
        font=FONT_BODY,
        borderwidth=0,
        relief="flat",
    )
    style.configure("TFrame", background=CLR_BG)
    style.configure("Card.TFrame", background=CLR_CARD,
                    relief="solid", borderwidth=1)

    style.configure("TLabel",
        background=CLR_BG,
        foreground=CLR_TEXT,
        font=FONT_LABEL,
        padding=(0, 2),
    )
    style.configure("Card.TLabel", background=CLR_CARD)
    style.configure("Sub.TLabel",
        background=CLR_CARD,
        foreground=CLR_SUBTEXT,
        font=FONT_SMALL,
    )
    style.configure("Title.TLabel",
        background=CLR_ACCENT,
        foreground="#FFFFFF",
        font=FONT_TITLE,
        padding=(16, 10),
    )
    style.configure("Heading.TLabel",
        background=CLR_CARD,
        foreground=CLR_TEXT,
        font=FONT_HEADER,
    )

    style.configure("TEntry",
        fieldbackground=CLR_CARD,
        foreground=CLR_TEXT,
        borderwidth=1,
        relief="solid",
        padding=(6, 4),
        font=FONT_BODY,
    )
    style.map("TEntry",
        bordercolor=[("focus", CLR_ACCENT), ("!focus", CLR_BORDER)],
        lightcolor=[("focus", CLR_ACCENT)],
    )

    style.configure("TCombobox",
        fieldbackground=CLR_CARD,
        background=CLR_CARD,
        foreground=CLR_TEXT,
        borderwidth=1,
        relief="solid",
        padding=(6, 4),
        font=FONT_BODY,
    )

    # Primary accent button
    style.configure("Accent.TButton",
        background=CLR_ACCENT,
        foreground="#FFFFFF",
        font=FONT_BOLD,
        padding=(14, 7),
        relief="flat",
        borderwidth=0,
    )
    style.map("Accent.TButton",
        background=[("active", CLR_ACCENT_HV), ("pressed", CLR_ACCENT_HV)],
        foreground=[("active", "#FFFFFF")],
    )

    # Ghost / secondary button
    style.configure("Ghost.TButton",
        background=CLR_BG,
        foreground=CLR_SUBTEXT,
        font=FONT_BODY,
        padding=(14, 7),
        relief="flat",
        borderwidth=1,
    )
    style.map("Ghost.TButton",
        background=[("active", CLR_BORDER)],
        foreground=[("active", CLR_TEXT)],
    )

# ── Structure JSON ─────────────────────────────────────────────────────────────
def get_structure_json_path():
    saved = load_previous_options()
    override = saved.get("structure_json_path", "").strip()
    if override:
        p = override if os.path.isabs(override) else os.path.join(BASE_DIR, override)
        return p
    return DEFAULT_STRUCTURE_JSON

def load_structure():
    path = get_structure_json_path()
    if not os.path.exists(path):
        show_error(
            "structure.json missing",
            f"Could not find structure.json at:\n{path}\n\nPRF files will not be reorganised."
        )
        return {}
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

# ── Helpers ────────────────────────────────────────────────────────────────────
def set_icon(win):
    try:
        icon_path = resource_path("logo.ico")
        if os.path.exists(icon_path):
            win.iconbitmap(icon_path)
    except Exception:
        pass

def center_window(win, w=None, h=None):
    win.update_idletasks()
    w = w or win.winfo_width()
    h = h or win.winfo_height()
    x = (win.winfo_screenwidth() // 2) - (w // 2)
    y = (win.winfo_screenheight() // 2) - (h // 2)
    win.geometry(f"{w}x{h}+{x}+{y}")

def on_close():
    try:
        if tk._default_root:
            for w in list(tk._default_root.children.values()):
                w.destroy()
            tk._default_root.destroy()
    except Exception:
        pass
    sys.exit()

def is_valid_cid(cid):
    return cid.isdigit() and 6 <= len(cid) <= 7

def _make_dialog(title_text, subtitle=None, width=440):
    """Create a styled top-level dialog with a header bar."""
    dlg = tk.Toplevel()
    dlg.configure(bg=CLR_BG)
    dlg.resizable(False, False)
    dlg.protocol("WM_DELETE_WINDOW", on_close)
    set_icon(dlg)

    # Header bar
    hdr = tk.Frame(dlg, bg=CLR_ACCENT)
    hdr.pack(fill="x")
    tk.Label(hdr, text="Kuwait & Iraq vACC  ·  ORBB Sectorfile",
             bg=CLR_ACCENT, fg="#FFFFFF", font=(FONT_FAMILY, 8),
             padx=16, pady=6).pack(anchor="w")

    # Card body
    card = tk.Frame(dlg, bg=CLR_CARD,
                    highlightbackground=CLR_BORDER, highlightthickness=1)
    card.pack(fill="both", expand=True, padx=16, pady=16)

    # Dialog title inside card
    tk.Label(card, text=title_text,
             bg=CLR_CARD, fg=CLR_TEXT,
             font=FONT_HEADER, anchor="w",
             padx=20, pady=(14, 0)).pack(fill="x")

    if subtitle:
        tk.Label(card, text=subtitle,
                 bg=CLR_CARD, fg=CLR_SUBTEXT,
                 font=(FONT_FAMILY, 9),
                 wraplength=width - 60, justify="left",
                 padx=20, pady=0).pack(fill="x")

    # Thin divider
    tk.Frame(card, bg=CLR_BORDER, height=1).pack(fill="x", padx=20, pady=(8, 0))

    dlg.transient()
    dlg.grab_set()
    dlg.attributes("-topmost", True)
    dlg.focus_force()

    return dlg, card

# ── Config persistence ─────────────────────────────────────────────────────────
BASIC_FIELDS = ["name", "initials", "cid", "rating", "password", "cpdlc"]

def load_previous_options():
    if os.path.exists(OPTIONS_PATH):
        with open(OPTIONS_PATH, "r") as f:
            return json.load(f)
    return {}

def save_options(options):
    with open(OPTIONS_PATH, "w") as f:
        json.dump(options, f, indent=2)

# ── Styled message helpers ─────────────────────────────────────────────────────
def show_error(title, message):
    dlg, card = _make_dialog(title, width=400)
    tk.Label(card, text=message,
             bg=CLR_CARD, fg=CLR_TEXT,
             font=FONT_BODY, wraplength=360,
             justify="left", padx=20, pady=14).pack(fill="x")
    bf = tk.Frame(card, bg=CLR_CARD)
    bf.pack(pady=(0, 16))
    btn = tk.Button(bf, text="OK", command=dlg.destroy,
                    bg=CLR_ACCENT, fg="#FFFFFF",
                    font=FONT_BOLD, relief="flat",
                    padx=24, pady=6, cursor="hand2",
                    activebackground=CLR_ACCENT_HV, activeforeground="#FFFFFF",
                    bd=0)
    btn.pack()
    dlg.bind("<Return>", lambda e: dlg.destroy())
    center_window(dlg, 420)
    dlg.wait_window()

def show_info(title, message):
    dlg, card = _make_dialog(title, width=400)
    tk.Label(card, text=message,
             bg=CLR_CARD, fg=CLR_TEXT,
             font=FONT_BODY, wraplength=360,
             justify="left", padx=20, pady=14).pack(fill="x")
    bf = tk.Frame(card, bg=CLR_CARD)
    bf.pack(pady=(0, 16))
    btn = tk.Button(bf, text="OK", command=dlg.destroy,
                    bg=CLR_SUCCESS, fg="#FFFFFF",
                    font=FONT_BOLD, relief="flat",
                    padx=24, pady=6, cursor="hand2",
                    activebackground="#196640", activeforeground="#FFFFFF",
                    bd=0)
    btn.pack()
    dlg.bind("<Return>", lambda e: dlg.destroy())
    center_window(dlg, 420)
    dlg.wait_window()

# ── GUI widgets ────────────────────────────────────────────────────────────────
def ask_string(field_label, prompt, default="", is_password=False):
    result = [None]

    dlg, card = _make_dialog(field_label, subtitle=prompt, width=440)

    inner = tk.Frame(card, bg=CLR_CARD)
    inner.pack(fill="x", padx=20, pady=14)

    entry_var = tk.StringVar(value=default)
    show_char = "" if is_password else None
    entry = tk.Entry(inner, textvariable=entry_var,
                     font=FONT_BODY, width=38,
                     bg=CLR_CARD, fg=CLR_TEXT,
                     relief="solid", bd=1,
                     highlightthickness=2,
                     highlightcolor=CLR_ACCENT,
                     highlightbackground=CLR_BORDER,
                     insertbackground=CLR_TEXT,
                     show=show_char if show_char is not None else "")
    entry.pack(fill="x", ipady=5)

    err_lbl = tk.Label(inner, text="", bg=CLR_CARD, fg=CLR_ERROR,
                       font=(FONT_FAMILY, 9))
    err_lbl.pack(anchor="w", pady=(3, 0))

    # Button row
    tk.Frame(card, bg=CLR_BORDER, height=1).pack(fill="x", padx=0)
    bf = tk.Frame(dlg, bg=CLR_BG)
    bf.pack(fill="x", padx=16, pady=12)

    def submit(event=None):
        result[0] = entry_var.get()
        dlg.destroy()

    def cancel(event=None):
        dlg.destroy()

    ok_btn = tk.Button(bf, text="Continue →", command=submit,
                       bg=CLR_ACCENT, fg="#FFFFFF",
                       font=FONT_BOLD, relief="flat",
                       padx=18, pady=6, cursor="hand2",
                       activebackground=CLR_ACCENT_HV, activeforeground="#FFFFFF",
                       bd=0)
    ok_btn.pack(side="right", padx=(6, 0))

    cancel_btn = tk.Button(bf, text="Cancel", command=cancel,
                           bg=CLR_BG, fg=CLR_SUBTEXT,
                           font=FONT_BODY, relief="flat",
                           padx=18, pady=6, cursor="hand2",
                           activebackground=CLR_BORDER, activeforeground=CLR_TEXT,
                           bd=0)
    cancel_btn.pack(side="right")

    dlg.bind("<Return>", submit)
    dlg.bind("<Escape>", cancel)
    center_window(dlg, 460)
    entry.focus_set()
    if default:
        entry.select_range(0, "end")
    dlg.wait_window()
    return result[0]

def ask_yesno(prompt, subtitle=None):
    result = [False]

    dlg, card = _make_dialog("Previous Configuration Found", subtitle=subtitle, width=420)

    tk.Label(card, text=prompt,
             bg=CLR_CARD, fg=CLR_TEXT,
             font=FONT_BODY, wraplength=380,
             justify="left", padx=20, pady=16).pack(fill="x")

    tk.Frame(card, bg=CLR_BORDER, height=1).pack(fill="x", padx=0)
    bf = tk.Frame(dlg, bg=CLR_BG)
    bf.pack(fill="x", padx=16, pady=12)

    def yes(event=None):
        result[0] = True
        dlg.destroy()

    def no(event=None):
        result[0] = False
        dlg.destroy()

    yes_btn = tk.Button(bf, text="Yes, load previous", command=yes,
                        bg=CLR_ACCENT, fg="#FFFFFF",
                        font=FONT_BOLD, relief="flat",
                        padx=18, pady=6, cursor="hand2",
                        activebackground=CLR_ACCENT_HV, activeforeground="#FFFFFF",
                        bd=0)
    yes_btn.pack(side="right", padx=(6, 0))

    no_btn = tk.Button(bf, text="Start fresh", command=no,
                       bg=CLR_BG, fg=CLR_SUBTEXT,
                       font=FONT_BODY, relief="flat",
                       padx=18, pady=6, cursor="hand2",
                       activebackground=CLR_BORDER, activeforeground=CLR_TEXT,
                       bd=0)
    no_btn.pack(side="right")

    dlg.bind("<Return>", yes)
    dlg.bind("<Escape>", no)
    center_window(dlg, 460)
    dlg.wait_window()
    return result[0]

def ask_rating(current=None):
    ratings_display = [
        'Observer (OBS)',
        'Developing Controller (S1)',
        'Aerodrome Controller (S2)',
        'Terminal Controller (S3)',
        'Enroute Controller (C1)',
        'Senior Controller (C3)',
        'Instructor (I1)',
        'Senior Instructor (I3)',
        'SUP',
        'ADM',
    ]
    prf_index_map = [0, 1, 2, 3, 4, 6, 7, 9, 10, 11]

    try:
        prf_val = int(current)
        if prf_val == 5: prf_val = 4
        elif prf_val == 8: prf_val = 7
        display_index = prf_index_map.index(prf_val) if prf_val in prf_index_map else 0
    except (ValueError, TypeError):
        display_index = 0

    selected = tk.StringVar(value=ratings_display[display_index])
    result = [None]

    dlg, card = _make_dialog("Controller Rating",
                             subtitle="Select your current VATSIM controller rating.",
                             width=440)

    inner = tk.Frame(card, bg=CLR_CARD)
    inner.pack(fill="x", padx=20, pady=14)

    combo = ttk.Combobox(inner, textvariable=selected,
                         values=ratings_display,
                         state="readonly", font=FONT_BODY, width=36)
    combo.pack(fill="x", ipady=4)

    tk.Frame(card, bg=CLR_BORDER, height=1).pack(fill="x", padx=0)
    bf = tk.Frame(dlg, bg=CLR_BG)
    bf.pack(fill="x", padx=16, pady=12)

    def submit(event=None):
        result[0] = selected.get()
        dlg.destroy()

    ok_btn = tk.Button(bf, text="Continue →", command=submit,
                       bg=CLR_ACCENT, fg="#FFFFFF",
                       font=FONT_BOLD, relief="flat",
                       padx=18, pady=6, cursor="hand2",
                       activebackground=CLR_ACCENT_HV, activeforeground="#FFFFFF",
                       bd=0)
    ok_btn.pack(side="right")

    dlg.bind("<Return>", submit)
    dlg.protocol("WM_DELETE_WINDOW", on_close)
    center_window(dlg, 460)
    combo.focus_set()
    dlg.wait_window()

    if result[0] is None:
        on_close()
    chosen_display_index = ratings_display.index(result[0])
    return str(prf_index_map[chosen_display_index])

# ── Field prompts ──────────────────────────────────────────────────────────────
FIELD_LABELS = {
    "name":     "Display Name",
    "initials": "Observer Initials",
    "cid":      "VATSIM CID",
    "rating":   "Controller Rating",
    "password": "VATSIM Password",
    "cpdlc":    "ACARS / Hoppie Code",
}

FIELD_DESCRIPTIONS = {
    "name":     "Your preferred name as it appears on the network. (CoC A4(B))",
    "initials": "Your observer initials, e.g. AB or JS. (CoC A4(B))",
    "cid":      "Your 6 or 7 digit VATSIM CID.",
    "rating":   "Select your current VATSIM controller rating.",
    "password": "Your VATSIM account password.",
    "cpdlc":    "Your Hoppie ACARS logon code for CPDLC.",
}

def prompt_for_field(key, current):
    label = FIELD_LABELS.get(key, key.replace("_", " ").title())
    desc  = FIELD_DESCRIPTIONS.get(key, "")
    if key == "rating":
        return ask_rating(current)
    else:
        while True:
            response = ask_string(label, desc, current,
                                  is_password=(key == "password"))
            if response is None:
                sys.exit()
            if key == "cid" and not is_valid_cid(response):
                show_error("Invalid CID", "Your CID must be a 6 or 7 digit number.\nPlease try again.")
                continue
            return response

# ── Config collection ──────────────────────────────────────────────────────────
def collect_basic_config():
    root = tk.Tk()
    root.configure(bg=CLR_BG)
    root.title("ORBB Configurator")
    set_icon(root)
    root.withdraw()
    apply_theme(root)
    tk._default_root = root

    previous_options = load_previous_options()
    options = {}

    if previous_options:
        if ask_yesno(
            "A saved configuration was found. Would you like to load it?",
            subtitle="You can update individual fields after loading."
        ):
            options.update(previous_options)
            for key in BASIC_FIELDS:
                if key not in options:
                    options[key] = prompt_for_field(key, "")
        # else: start fresh

    for key in BASIC_FIELDS:
        if key not in options or not options[key]:
            options[key] = prompt_for_field(key, "")

    return options

# ── PRF restructure ────────────────────────────────────────────────────────────
def restructure_prf_files():
    structure = load_structure()
    if not structure:
        return

    moved = []
    skipped = []

    for prf_name, target_rel in structure.items():
        src = os.path.join(PACK_ROOT, prf_name)
        if not os.path.exists(src):
            continue
        target_dir = os.path.join(PACK_ROOT, target_rel)
        os.makedirs(target_dir, exist_ok=True)
        dst = os.path.join(target_dir, prf_name)
        try:
            shutil.move(src, dst)
            moved.append(f"  {prf_name}  →  {target_rel}")
        except Exception as e:
            skipped.append(f"  {prf_name}: {e}")

    if moved:
        print("Moved PRF files:\n" + "\n".join(moved))
    if skipped:
        print("Could not move:\n" + "\n".join(skipped))

# ── File patchers ──────────────────────────────────────────────────────────────
def patch_prf_file(file_path, name, initials, cid, rating, password):
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            lines = f.readlines()
    except Exception as e:
        print(f"Failed to read {file_path}: {e}")
        return

    lines = [l for l in lines if not (
        l.startswith("LastSession\trealname") or
        l.startswith("LastSession\tcertificate") or
        l.startswith("LastSession\trating") or
        l.startswith("LastSession\tcallsign") or
        l.startswith("LastSession\tpassword")
    )]

    new_lines = [
        f"LastSession\trealname\t{name}\n",
        f"LastSession\tcertificate\t{cid}\n",
        f"LastSession\trating\t{rating}\n",
        f"LastSession\tcallsign\t{initials}_OBS\n",
        f"LastSession\tpassword\t{password}\n",
    ]
    lines += ["\n"] + new_lines

    try:
        with open(file_path, "w", encoding="utf-8") as f:
            f.writelines(lines)
    except Exception as e:
        print(f"Failed to write {file_path}: {e}")

def patch_profiles_file(file_path, cid):
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()
    except Exception as e:
        print(f"Failed to read {file_path}: {e}")
        return

    replacements = {
        "Submit feedback at PLACEHOLDER":
            f"Submit feedback at placeholder?cid={cid}"
    }

    saved = load_previous_options()
    user_replacements = saved.get("profiles_replacements", {})
    for find, replace in user_replacements.items():
        replacements[find] = replace.replace("{cid}", cid)

    for find, replace in replacements.items():
        content = content.replace(find, replace)

    try:
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(content)
    except Exception as e:
        print(f"Failed to write {file_path}: {e}")

def patch_topsky_cpdlc(cpdlc_code):
    topsky_paths = [
        "Data/Plugin/TopSky/TopSkyCPDLChoppieCode.txt",
        "Data/Plugin/TopSkyGRP/TopSkyCPDLChoppieCode.txt",
    ]
    for rel_path in topsky_paths:
        full_path = os.path.join(PACK_ROOT, rel_path)
        os.makedirs(os.path.dirname(full_path), exist_ok=True)
        try:
            with open(full_path, "w") as f:
                f.write(cpdlc_code)
        except Exception as e:
            print(f"Failed to write {full_path}: {e}")

# ── Main apply ─────────────────────────────────────────────────────────────────
def apply_configuration(name, initials, cid, rating, password, cpdlc):
    for root, _, files in os.walk(PACK_ROOT):
        for file in files:
            path = os.path.join(root, file)
            if file.endswith(".prf"):
                patch_prf_file(path, name, initials, cid, rating, password)
            elif file.endswith("Profiles.txt"):
                patch_profiles_file(path, cid)
    patch_topsky_cpdlc(cpdlc)

# ── Entry point ────────────────────────────────────────────────────────────────
def main():
    if not tk._default_root:
        root = tk.Tk()
        root.configure(bg=CLR_BG)
        root.withdraw()
        apply_theme(root)
        tk._default_root = root

    lockfile = os.path.join(BASE_DIR, "configurator.lock")
    if os.path.exists(lockfile):
        show_error("Already Running", "The configurator is already running.")
        sys.exit()

    with open(lockfile, "w") as f:
        f.write(str(os.getpid()))

    try:
        options = collect_basic_config()
        restructure_prf_files()
        apply_configuration(
            name=options["name"],
            initials=options["initials"],
            cid=options["cid"],
            rating=options["rating"],
            password=options["password"],
            cpdlc=options["cpdlc"],
        )
        save_options(options)
        show_info("Configuration Complete",
                  "Your ORBB controller pack has been configured successfully.\n\nYou can now launch EuroScope.")
        time.sleep(0.5)

    finally:
        if os.path.exists(lockfile):
            os.remove(lockfile)

if __name__ == "__main__":
    try:
        main()
    finally:
        try:
            if tk._default_root:
                for w in list(tk._default_root.children.values()):
                    w.destroy()
                tk._default_root.destroy()
        except Exception:
            pass
        if getattr(sys, "frozen", False):
            os._exit(0)
        else:
            sys.exit(0)