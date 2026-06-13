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

# ── Monkey-patch Dialog icon ───────────────────────────────────────────────────
_original_init = simpledialog.Dialog.__init__

def _custom_init(self, master, title=None):
    _original_init(self, master, title)
    try:
        icon_path = resource_path("logo.ico")
        if os.path.exists(icon_path):
            self.wm_iconbitmap(icon_path)
    except Exception:
        pass

simpledialog.Dialog.__init__ = _custom_init

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
# e.g. C:\GitHub\ORBB-Sectorfile\ORBB\Plugins\Configurator\  →  C:\GitHub\ORBB-Sectorfile\
PACK_ROOT = os.path.abspath(os.path.join(BASE_DIR, "..", "..", ".."))

# configurator_config.json lives next to the exe in the Configurator folder
OPTIONS_PATH = os.path.join(BASE_DIR, "configurator_config.json")

# structure.json lives in the same folder as the exe
DEFAULT_STRUCTURE_JSON = os.path.join(BASE_DIR, "structure.json")

# ── Structure JSON ─────────────────────────────────────────────────────────────
def get_structure_json_path():
    """Return the path to structure.json, respecting any override in the saved config."""
    saved = load_previous_options()
    override = saved.get("structure_json_path", "").strip()
    if override:
        p = override if os.path.isabs(override) else os.path.join(BASE_DIR, override)
        return p
    return DEFAULT_STRUCTURE_JSON

def load_structure():
    """
    Load the prf→folder mapping from structure.json.
    Returns a dict like {"Baghdad ACC.prf": "Baghdad ACC/", ...}
    """
    path = get_structure_json_path()
    if not os.path.exists(path):
        messagebox.showwarning(
            "structure.json missing",
            f"Could not find structure.json at:\n{path}\n\n"
            "PRF files will not be reorganised."
        )
        return {}
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

# ── Helpers ────────────────────────────────────────────────────────────────────
def center_window(win):
    win.update_idletasks()
    w, h = win.winfo_width(), win.winfo_height()
    x = (win.winfo_screenwidth() // 2) - (w // 2)
    y = (win.winfo_screenheight() // 2) - (h // 2)
    win.geometry(f"{w}x{h}+{x}+{y}")

def on_close():
    try:
        if tk._default_root:
            for w in tk._default_root.children.values():
                w.destroy()
            tk._default_root.destroy()
    except Exception:
        pass
    sys.exit()

def is_valid_cid(cid):
    return cid.isdigit() and 6 <= len(cid) <= 7

# ── Config persistence ─────────────────────────────────────────────────────────
DEFAULT_FIELDS = {
    "name": "",
    "rating": "",
    "cid": "",
    "password": "",
    "initials": "",
    "cpdlc": "",
}

BASIC_FIELDS = ["name", "rating", "cid", "password", "initials", "cpdlc"]

def load_previous_options():
    if os.path.exists(OPTIONS_PATH):
        with open(OPTIONS_PATH, "r") as f:
            return json.load(f)
    return {}

def save_options(options):
    with open(OPTIONS_PATH, "w") as f:
        json.dump(options, f, indent=2)

# ── GUI widgets ────────────────────────────────────────────────────────────────
def ask_string(prompt, default=""):
    result = None
    dialog = tk.Toplevel()
    try:
        icon_path = resource_path("logo.ico")
        if os.path.exists(icon_path):
            dialog.iconbitmap(icon_path)
    except Exception:
        pass
    dialog.title("ORBB Configurator")
    dialog.resizable(False, False)
    dialog.protocol("WM_DELETE_WINDOW", on_close)

    ttk.Label(dialog, text=prompt, wraplength=360, justify="left").pack(padx=20, pady=(15, 5))
    entry_var = tk.StringVar(value=default)
    entry = ttk.Entry(dialog, textvariable=entry_var, width=40)
    entry.pack(padx=20, pady=5)

    def submit(event=None):
        nonlocal result
        result = entry_var.get()
        dialog.destroy()

    def cancel(event=None):
        dialog.destroy()

    bf = ttk.Frame(dialog)
    bf.pack(pady=15)
    ttk.Button(bf, text="OK", command=submit).pack(side="left", padx=5)
    ttk.Button(bf, text="Cancel", command=cancel).pack(side="left", padx=5)

    dialog.bind("<Return>", submit)
    dialog.bind("<Escape>", cancel)
    dialog.transient()
    dialog.grab_set()
    dialog.attributes("-topmost", True)
    dialog.focus_force()
    center_window(dialog)
    entry.focus_set()
    dialog.wait_window()
    return result

def ask_yesno(prompt, title="ORBB Configurator"):
    result = None
    dialog = tk.Toplevel()
    try:
        icon_path = resource_path("logo.ico")
        if os.path.exists(icon_path):
            dialog.iconbitmap(icon_path)
    except Exception:
        pass
    dialog.title(title)
    dialog.protocol("WM_DELETE_WINDOW", on_close)
    dialog.resizable(False, False)

    frame = ttk.Frame(dialog, padding=20)
    frame.pack(fill="both", expand=True)
    ttk.Label(frame, text=prompt, wraplength=350, justify="left").pack(pady=(0, 15))

    def yes():
        nonlocal result
        result = True
        dialog.destroy()

    def no():
        nonlocal result
        result = False
        dialog.destroy()

    bf = ttk.Frame(frame)
    bf.pack()
    ttk.Button(bf, text="Yes", command=yes).pack(side="left", padx=10)
    ttk.Button(bf, text="No", command=no).pack(side="left", padx=10)

    dialog.bind("<Return>", lambda e: yes())
    dialog.bind("<Escape>", lambda e: no())
    dialog.transient()
    dialog.grab_set()
    dialog.attributes("-topmost", True)
    dialog.focus_force()
    center_window(dialog)
    dialog.wait_window()
    return result

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
        'ADM'
    ]
    # Maps display index → original .prf index (skipping C2=5 and I2=8)
    prf_index_map = [0, 1, 2, 3, 4, 6, 7, 9, 10, 11]

    try:
        prf_val = int(current)
        if prf_val == 5:
            prf_val = 4
        elif prf_val == 8:
            prf_val = 7
        display_index = prf_index_map.index(prf_val) if prf_val in prf_index_map else 0
    except (ValueError, TypeError):
        display_index = 0

    selected = tk.StringVar(value=ratings_display[display_index])

    def submit():
        dialog.quit()
        dialog.destroy()

    dialog = tk.Toplevel()
    try:
        icon_path = resource_path("logo.ico")
        if os.path.exists(icon_path):
            dialog.iconbitmap(icon_path)
    except Exception:
        pass
    dialog.minsize(300, 200)
    dialog.title("ORBB Configurator")
    ttk.Label(dialog, text="Select your rating:").pack(pady=5)
    dropdown = ttk.Combobox(dialog, textvariable=selected, values=ratings_display, state="readonly")
    dropdown.pack(pady=5)
    ttk.Button(dialog, text="OK", command=submit).pack()
    dialog.protocol("WM_DELETE_WINDOW", on_close)
    dialog.transient()
    dialog.grab_set()
    dialog.attributes("-topmost", True)
    dialog.focus_force()
    center_window(dialog)
    dialog.mainloop()

    chosen_display_index = ratings_display.index(selected.get())
    return str(prf_index_map[chosen_display_index])

# ── Field prompts ──────────────────────────────────────────────────────────────
FIELD_DESCRIPTIONS = {
    "name":     "Enter your preferred name convention. (Code of Conduct A4(B))",
    "rating":   "Select your controller rating.",
    "cid":      "Enter your CID.",
    "password": "Enter your password.",
    "initials": "Enter your observer initials (e.g. AB, JS) (Code of Conduct A4(B)).",
    "cpdlc":    "Enter your ACARS logon code."
}

def prompt_for_field(key, current):
    desc = FIELD_DESCRIPTIONS.get(key, f"Enter {key.replace('_', ' ')}")
    if key == "rating":
        return ask_rating(current)
    else:
        while True:
            response = ask_string(desc, current)
            if response is None:
                sys.exit()
            if key == "cid" and not is_valid_cid(response):
                messagebox.showerror("Invalid CID", "CID must be a 6 or 7 digit number.")
                continue
            return response

# ── Config collection ──────────────────────────────────────────────────────────
def collect_basic_config():
    root = tk.Tk()
    root.title("ORBB Configurator")
    try:
        icon_path = resource_path("logo.ico")
        if os.path.exists(icon_path):
            root.iconbitmap(icon_path)
    except Exception:
        pass
    root.withdraw()
    tk._default_root = root

    previous_options = load_previous_options()
    options = {}

    if previous_options:
        if ask_yesno("Do you want to load your previous options?"):
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
    """
    Move .prf files from the repo root into the folders defined in structure.json.
    Any .prf not listed in structure.json is left alone.
    """
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
def fix_orbb_paths(lines):
    """
    For each line, if a tab-separated value starts with \ORBB\ (but not already
    \..\ORBB\), prepend ..\ to make it \..\ORBB\.
    Handles both tab-separated and space-separated .prf lines.
    """
    fixed = []
    for line in lines:
        # Match a value that starts with \ORBB\ not already preceded by ..\
        # Works on tab-delimited fields (the standard .prf format)
        fixed.append(re.sub(r'(?<!\.\.)(\\ORBB\\)', r'\\..\\\1'.replace('\\\\', '\\'), line))
    return fixed

def patch_prf_file(file_path, name, initials, cid, rating, password):
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            lines = f.readlines()
    except Exception as e:
        print(f"Failed to read {file_path}: {e}")
        return

    # Fix \ORBB\ paths → \..\ORBB\
    lines = fix_orbb_paths(lines)

    # Remove any existing LastSession credential lines (including server, so we always
    # write a clean canonical block)
    lines = [l for l in lines if not (
            l.startswith("LastSession\trealname") or
            l.startswith("LastSession\tcertificate") or
            l.startswith("LastSession\trating") or
            l.startswith("LastSession\tcallsign") or
            l.startswith("LastSession\tpassword") or
            l.startswith("LastSession\tserver")
    )]

    # Write credentials in the required order:
    # real name → rating → certificate → password → callsign → server
    new_lines = [
        f"LastSession\trealname\t{name}\n",
        f"LastSession\trating\t{rating}\n",
        f"LastSession\tcertificate\t{cid}\n",
        f"LastSession\tpassword\t{password}\n",
        f"LastSession\tcallsign\t{initials}_OBS\n",
        f"LastSession\tserver\tAUTOMATIC\n",
    ]
    lines += ["\n"] + new_lines

    try:
        with open(file_path, "w", encoding="utf-8") as f:
            f.writelines(lines)
    except Exception as e:
        print(f"Failed to write {file_path}: {e}")

def patch_profiles_file(file_path, cid):
    """
    Applies all replacements defined in the [profiles_replacements] section of
    configurator_config.json.

    Default replacement (always applied):
        "Submit feedback at PLACEHOLDER"
        → "Submit feedback at placeholder?cid=<CID>"

    You can add extra find/replace pairs to the saved config under
    "profiles_replacements", for example:
        {
          "profiles_replacements": {
            "ORBB_PLACEHOLDER": "ORBB_REAL_VALUE",
            "old string": "new string"
          }
        }
    The token {cid} in a replacement value will be substituted with the
    controller's actual CID automatically.
    """
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()
    except Exception as e:
        print(f"Failed to read {file_path}: {e}")
        return

    # Built-in default replacement
    replacements = {
        "Submit feedback at PLACEHOLDER":
            f"Submit feedback at placeholder?cid={cid}"
    }

    # Merge in any user-defined replacements from the saved config
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
    """Write the Hoppie code to all TopSky CPDLC code files."""
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
    """Walk the entire repo root and patch all relevant files."""
    for root, _, files in os.walk(PACK_ROOT):
        for file in files:
            path = os.path.join(root, file)

            if file.endswith(".prf"):
                patch_prf_file(path, name, initials, cid, rating, password)

            elif file.endswith("Bandbox.txt"):
                patch_profiles_file(path, cid)

    patch_topsky_cpdlc(cpdlc)

# ── Entry point ────────────────────────────────────────────────────────────────
def main():
    if not tk._default_root:
        root = tk.Tk()
        root.withdraw()
        tk._default_root = root

    lockfile = os.path.join(BASE_DIR, "configurator.lock")
    if os.path.exists(lockfile):
        messagebox.showerror("Already Running", "Configurator is already running.")
        sys.exit()

    with open(lockfile, "w") as f:
        f.write(str(os.getpid()))

    try:
        # 1. Collect options via GUI
        options = collect_basic_config()

        # 2. Restructure PRF files into folders defined by structure.json
        restructure_prf_files()

        # 3. Patch all files
        apply_configuration(
            name=options["name"],
            initials=options["initials"],
            cid=options["cid"],
            rating=options["rating"],
            password=options["password"],
            cpdlc=options["cpdlc"],
        )

        # 4. Persist options for next run
        save_options(options)

        messagebox.showinfo("Complete", "Profile configuration complete.")
        time.sleep(1.5)

    finally:
        if os.path.exists(lockfile):
            os.remove(lockfile)

if __name__ == "__main__":
    try:
        main()
    finally:
        try:
            if tk._default_root:
                for w in tk._default_root.children.values():
                    w.destroy()
                tk._default_root.destroy()
        except Exception:
            pass
        if getattr(sys, "frozen", False):
            os._exit(0)
        else:
            sys.exit(0)