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
        self.wm_iconbitmap(resource_path("logo.ico"))
    except Exception:
        pass

simpledialog.Dialog.__init__ = _custom_init

# ── Paths ──────────────────────────────────────────────────────────────────────
def resource_path(filename):
    """Path to a bundled resource (works frozen and unfrozen)."""
    if getattr(sys, 'frozen', False):
        return os.path.join(sys._MEIPASS, filename)
    return os.path.join(os.path.abspath("."), filename)

if getattr(sys, 'frozen', False):
    BASE_DIR = os.path.dirname(sys.executable)
else:
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))

OPTIONS_PATH = os.path.join(BASE_DIR, "controller_pack_config.json")

# ── Structure JSON ─────────────────────────────────────────────────────────────
# Default location relative to the exe.  Can be overridden by placing a
# "structure_json_path" key inside controller_pack_config.json.
DEFAULT_STRUCTURE_JSON = os.path.join(BASE_DIR, "ORBB", "Plugins", "structure.json")

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
    Returns a dict like {"Baghdad ACC.prf": "ORBB/Baghdad ACC/", ...}
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

# ── Theme ──────────────────────────────────────────────────────────────────────
def is_dark_theme_enabled():
    try:
        registry = winreg.ConnectRegistry(None, winreg.HKEY_CURRENT_USER)
        key = winreg.OpenKey(
            registry,
            r"Software\Microsoft\Windows\CurrentVersion\Themes\Personalize"
        )
        value, _ = winreg.QueryValueEx(key, "AppsUseLightTheme")
        return value == 0
    except Exception:
        return False

def apply_azure_theme(root):
    try:
        style = ttk.Style()
        theme_dir = resource_path("theme")
        if "azure-light" not in style.theme_names():
            root.tk.call("source", os.path.join(theme_dir, "light.tcl"))
        if "azure-dark" not in style.theme_names():
            root.tk.call("source", os.path.join(theme_dir, "dark.tcl"))
        theme = "azure-dark" if is_dark_theme_enabled() else "azure-light"
        style.theme_use(theme)
    except Exception as e:
        messagebox.showwarning("Theme Load Failed", f"Could not load Azure theme:\n{e}")

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
    "initials": "",
    "cid": "",
    "rating": "",
    "password": "",
    "cpdlc": "",
    "discord_presence": "n",
}

BASIC_FIELDS = ["name", "initials", "cid", "rating", "password", "cpdlc", "discord_presence"]

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
        dialog.iconbitmap(resource_path("logo.ico"))
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
        dialog.iconbitmap(resource_path("logo.ico"))
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
    ratings = ['OBS', 'S1', 'S2', 'S3', 'C1', 'C2 (not used)', 'C3',
               'I1', 'I2 (not used)', 'I3', 'SUP', 'ADM']
    try:
        index = int(current)
        if index < 0 or index >= len(ratings):
            index = 0
    except (ValueError, TypeError):
        index = 0

    selected = tk.StringVar(value=ratings[index])

    def submit():
        dialog.quit()
        dialog.destroy()

    dialog = tk.Toplevel()
    try:
        dialog.iconbitmap(resource_path("logo.ico"))
    except Exception:
        pass
    dialog.minsize(300, 200)
    dialog.title("ORBB Configurator")
    ttk.Label(dialog, text="Select your rating:").pack(pady=5)
    dropdown = ttk.Combobox(dialog, textvariable=selected, values=ratings, state="readonly")
    dropdown.pack(pady=5)
    ttk.Button(dialog, text="OK", command=submit).pack()
    dialog.protocol("WM_DELETE_WINDOW", on_close)
    dialog.transient()
    dialog.grab_set()
    dialog.attributes("-topmost", True)
    dialog.focus_force()
    center_window(dialog)
    dialog.mainloop()
    return str(ratings.index(selected.get()))

# ── Field prompts ──────────────────────────────────────────────────────────────
FIELD_DESCRIPTIONS = {
    "name":             "Enter your preferred name convention. (Code of Conduct A4(B))",
    "initials":         "Enter your observer initials (e.g. AB, JS) (Code of Conduct A4(B)).",
    "cid":              "Enter your CID.",
    "rating":           "Select your controller rating.",
    "password":         "Enter your password.",
    "cpdlc":            "Enter your ACARS logon code."
}

def prompt_for_field(key, current):
    desc = FIELD_DESCRIPTIONS.get(key, f"Enter {key.replace('_', ' ')}")
    if key == "rating":
        return ask_rating(current)
    elif key == "discord_presence":
        return "y" if ask_yesno(desc) else "n"
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
        root.iconbitmap(resource_path("logo.ico"))
    except Exception:
        pass
    root.withdraw()
    tk._default_root = root
    apply_azure_theme(root)

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
    Move .prf files from the root (next to the exe) into the folders defined
    in structure.json.  Any .prf not listed in structure.json is left alone.
    """
    structure = load_structure()
    if not structure:
        return

    moved = []
    skipped = []

    for prf_name, target_rel in structure.items():
        src = os.path.join(BASE_DIR, prf_name)
        if not os.path.exists(src):
            # Already moved, or never existed — skip silently
            continue

        target_dir = os.path.join(BASE_DIR, target_rel)
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


def _resolve_discord_relpath(file_path: str) -> str:
    prf_dir = Path(file_path).parent
    for root in [prf_dir] + list(prf_dir.parents):
        plugin_dir = root / "Data" / "Plugin"
        if plugin_dir.exists():
            dll_abs = plugin_dir / "DiscordEuroscope.dll"
            rel = os.path.relpath(dll_abs, start=prf_dir).replace("/", "\\")
            if not rel.startswith("\\"):
                rel = "\\" + rel
            return rel
    return r"\..\Data\Plugin\DiscordEuroscope.dll"


def patch_discord_plugin(file_path: str, state: str = "present"):
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            raw = f.read()
    except Exception as e:
        print(f"Failed to read {file_path}: {e}")
        return

    text = raw.replace("\r\n", "\n").replace("\r", "\n")
    lines = text.split("\n")

    if state == "absent":
        new_lines = [l for l in lines if "DiscordEuroscope.dll" not in l]
        if new_lines != lines:
            with open(file_path, "w", encoding="utf-8", newline="\n") as f:
                f.write("\n".join(new_lines).rstrip("\n") + "\n")
        return

    if any("DiscordEuroscope.dll" in l for l in lines):
        return

    plugin_rx = re.compile(r"^Plugins\tPlugin(\d+)\t")
    last_idx, max_num = -1, 0
    for i, line in enumerate(lines):
        m = plugin_rx.match(line)
        if m:
            last_idx = i
            try:
                max_num = max(max_num, int(m.group(1)))
            except ValueError:
                pass

    next_num = max_num + 1 if max_num else 1
    dll_rel = _resolve_discord_relpath(file_path)
    new_line = f"Plugins\tPlugin{next_num}\t{dll_rel}"

    if last_idx >= 0:
        lines.insert(last_idx + 1, new_line)
    else:
        if lines and lines[-1] != "":
            lines.append("")
        lines.append(new_line)

    try:
        with open(file_path, "w", encoding="utf-8", newline="\n") as f:
            f.write("\n".join(lines).rstrip("\n") + "\n")
    except Exception as e:
        print(f"Failed to write {file_path}: {e}")


def patch_profiles_file(file_path, cid):
    """
    Applies all replacements defined in the [profiles_replacements] section of
    controller_pack_config.json.

    Default replacement (always applied):
        "Submit feedback at vats.im/atcfb"
        → "Submit feedback at vatsim.uk/atcfb?cid=<CID>"

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
        "Submit feedback at vats.im/atcfb":
            f"Submit feedback at vatsim.uk/atcfb?cid={cid}"
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
    """Write the Hoppie code to all four TopSky CPDLC code files."""
    topsky_paths = [
        "Data/Plugin/TopSky_iTEC/TopSkyCPDLChoppieCode.txt",
        "Data/Plugin/TopSky_NERC/TopSkyCPDLChoppieCode.txt",
        "Data/Plugin/TopSky_NODE/TopSkyCPDLChoppieCode.txt",
        "Data/Plugin/TopSky_NOVA/TopSkyCPDLChoppieCode.txt",
    ]
    for rel_path in topsky_paths:
        full_path = os.path.join(BASE_DIR, rel_path)
        os.makedirs(os.path.dirname(full_path), exist_ok=True)
        try:
            with open(full_path, "w") as f:
                f.write(cpdlc_code)
        except Exception as e:
            print(f"Failed to write {full_path}: {e}")


# ── Main apply ─────────────────────────────────────────────────────────────────
def apply_configuration(name, initials, cid, rating, password, cpdlc, discord_presence):
    """Walk every subdirectory and patch all relevant files."""
    for root, _, files in os.walk(BASE_DIR):
        for file in files:
            path = os.path.join(root, file)

            if file.endswith(".prf"):
                patch_prf_file(path, name, initials, cid, rating, password)
                if discord_presence == "y":
                    patch_discord_plugin(path, state="present")
                else:
                    patch_discord_plugin(path, state="absent")

            elif file.endswith("Profiles.txt"):
                patch_profiles_file(path, cid)

    # TopSky CPDLC files (written to fixed locations)
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
            discord_presence=options.get("discord_presence", "n"),
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