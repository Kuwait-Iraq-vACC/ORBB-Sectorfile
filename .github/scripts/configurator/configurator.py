"""
ORBB GNG Configurator
Bootstraps its own dependencies, then configures EuroScope profiles.
"""

# ── Bootstrap: install Pillow if missing ──────────────────────────────────────
import importlib, subprocess, sys

def _ensure(package, import_name=None):
    import_name = import_name or package
    try:
        importlib.import_module(import_name)
    except ImportError:
        subprocess.check_call(
            [sys.executable, "-m", "pip", "install", "--quiet", package],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )

_ensure("Pillow", "PIL")

# ── Standard imports ───────────────────────────────────────────────────────────
import json
import os
import re
import shutil
import time
import winreg
import tkinter as tk
import tkinter.simpledialog as simpledialog
from ctypes import windll, c_uint
from pathlib import Path
from tkinter import messagebox, ttk

from PIL import Image, ImageTk

# ── Monkey-patch Dialog icon ───────────────────────────────────────────────────
_orig_dialog_init = simpledialog.Dialog.__init__

def _patched_dialog_init(self, master, title=None):
    _orig_dialog_init(self, master, title)
    try:
        self.wm_iconbitmap(resource_path("logo.ico"))
    except Exception:
        pass

simpledialog.Dialog.__init__ = _patched_dialog_init

# ── Runtime paths ──────────────────────────────────────────────────────────────
def resource_path(filename: str) -> str:
    """Resolve a bundled resource path (PyInstaller-aware)."""
    base = sys._MEIPASS if getattr(sys, "frozen", False) else os.path.abspath(".")
    return os.path.join(base, filename)

BASE_DIR: str = (
    os.path.dirname(sys.executable)
    if getattr(sys, "frozen", False)
    else os.path.dirname(os.path.abspath(__file__))
)

OPTIONS_PATH = os.path.join(BASE_DIR, "configurator_config.json")

# ── structure.json ─────────────────────────────────────────────────────────────
DEFAULT_STRUCTURE_JSON = os.path.join(BASE_DIR, "ORBB", "Plugins", "structure.json")

def _structure_json_path() -> str:
    override = _load_options().get("structure_json_path", "").strip()
    if override:
        return override if os.path.isabs(override) else os.path.join(BASE_DIR, override)
    return DEFAULT_STRUCTURE_JSON

def _load_structure() -> dict:
    path = _structure_json_path()
    if not os.path.exists(path):
        messagebox.showwarning(
            "structure.json missing",
            f"Could not find structure.json at:\n{path}\n\n"
            "PRF files will not be reorganised.",
        )
        return {}
    with open(path, "r", encoding="utf-8") as fh:
        return json.load(fh)

# ── Config persistence ─────────────────────────────────────────────────────────
FIELDS = ["name", "initials", "cid", "rating", "password", "cpdlc", "discord_presence"]

def _load_options() -> dict:
    if os.path.exists(OPTIONS_PATH):
        with open(OPTIONS_PATH, "r", encoding="utf-8") as fh:
            return json.load(fh)
    return {}

def _save_options(options: dict) -> None:
    with open(OPTIONS_PATH, "w", encoding="utf-8") as fh:
        json.dump(options, fh, indent=2)

# ── Theme ──────────────────────────────────────────────────────────────────────
def _windows_dark_mode() -> bool:
    try:
        reg = winreg.ConnectRegistry(None, winreg.HKEY_CURRENT_USER)
        key = winreg.OpenKey(
            reg, r"Software\Microsoft\Windows\CurrentVersion\Themes\Personalize"
        )
        val, _ = winreg.QueryValueEx(key, "AppsUseLightTheme")
        return val == 0
    except Exception:
        return False

def _apply_theme(root: tk.Tk) -> None:
    try:
        style = ttk.Style()
        theme_dir = resource_path("theme")
        if "azure-light" not in style.theme_names():
            root.tk.call("source", os.path.join(theme_dir, "light.tcl"))
        if "azure-dark" not in style.theme_names():
            root.tk.call("source", os.path.join(theme_dir, "dark.tcl"))
        style.theme_use("azure-dark" if _windows_dark_mode() else "azure-light")
    except Exception as exc:
        messagebox.showwarning("Theme", f"Could not load Azure theme:\n{exc}")

# ── GUI utilities ──────────────────────────────────────────────────────────────
WINDOW_TITLE = "ORBB Configurator"

def _centre(win: tk.Toplevel) -> None:
    win.update_idletasks()
    w, h = win.winfo_width(), win.winfo_height()
    x = (win.winfo_screenwidth() - w) // 2
    y = (win.winfo_screenheight() - h) // 2
    win.geometry(f"{w}x{h}+{x}+{y}")

def _set_icon(win) -> None:
    try:
        win.iconbitmap(resource_path("logo.ico"))
    except Exception:
        pass

def _on_close() -> None:
    try:
        root = tk._default_root
        if root:
            root.destroy()
    except Exception:
        pass
    sys.exit()

def _make_dialog(resizable=False) -> tk.Toplevel:
    dlg = tk.Toplevel()
    _set_icon(dlg)
    dlg.title(WINDOW_TITLE)
    dlg.resizable(resizable, resizable)
    dlg.protocol("WM_DELETE_WINDOW", _on_close)
    dlg.transient()
    dlg.grab_set()
    dlg.attributes("-topmost", True)
    dlg.focus_force()
    return dlg


def ask_string(prompt: str, default: str = "") -> str | None:
    result = None

    dlg = _make_dialog()
    ttk.Label(dlg, text=prompt, wraplength=360, justify="left").pack(padx=20, pady=(15, 5))
    var = tk.StringVar(value=default)
    entry = ttk.Entry(dlg, textvariable=var, width=40)
    entry.pack(padx=20, pady=5)

    def submit(_=None):
        nonlocal result
        result = var.get()
        dlg.destroy()

    bf = ttk.Frame(dlg)
    bf.pack(pady=15)
    ttk.Button(bf, text="OK",     command=submit).pack(side="left", padx=5)
    ttk.Button(bf, text="Cancel", command=dlg.destroy).pack(side="left", padx=5)
    dlg.bind("<Return>", submit)
    dlg.bind("<Escape>", lambda _: dlg.destroy())

    _centre(dlg)
    entry.focus_set()
    dlg.wait_window()
    return result


def ask_yesno(prompt: str, title: str = WINDOW_TITLE) -> bool:
    result = False

    dlg = _make_dialog()
    dlg.title(title)
    frame = ttk.Frame(dlg, padding=20)
    frame.pack(fill="both", expand=True)
    ttk.Label(frame, text=prompt, wraplength=360, justify="left").pack(pady=(0, 15))

    def yes(_=None):
        nonlocal result
        result = True
        dlg.destroy()

    bf = ttk.Frame(frame)
    bf.pack()
    ttk.Button(bf, text="Yes", command=yes).pack(side="left", padx=10)
    ttk.Button(bf, text="No",  command=dlg.destroy).pack(side="left", padx=10)
    dlg.bind("<Return>", yes)
    dlg.bind("<Escape>", lambda _: dlg.destroy())

    _centre(dlg)
    dlg.wait_window()
    return result


def ask_rating(current: str = "") -> str:
    RATINGS = ["OBS", "S1", "S2", "S3", "C1", "C2 (not used)", "C3",
               "I1", "I2 (not used)", "I3", "SUP", "ADM"]
    try:
        idx = max(0, min(int(current), len(RATINGS) - 1))
    except (ValueError, TypeError):
        idx = 0

    selected = tk.StringVar(value=RATINGS[idx])
    done = tk.BooleanVar(value=False)

    dlg = _make_dialog()
    dlg.minsize(300, 180)
    ttk.Label(dlg, text="Select your VATSIM controller rating:").pack(padx=20, pady=(15, 5))
    ttk.Combobox(dlg, textvariable=selected, values=RATINGS, state="readonly", width=24).pack(padx=20, pady=5)

    def submit(_=None):
        done.set(True)
        dlg.destroy()

    ttk.Button(dlg, text="OK", command=submit).pack(pady=10)
    dlg.bind("<Return>", submit)
    _centre(dlg)
    dlg.wait_window()

    return str(RATINGS.index(selected.get()))

# ── Field prompting ────────────────────────────────────────────────────────────
FIELD_PROMPTS = {
    "name":             "Enter your full name as registered on VATSIM\n(Code of Conduct A4b).",
    "initials":         "Enter your 2–3 letter observer identifier\n(e.g. LB or JSM).",
    "cid":              "Enter your VATSIM CID (6 or 7 digits).",
    "rating":           None,   # handled by ask_rating
    "password":         "Enter your VATSIM password.",
    "cpdlc":            "Enter your Hoppie CPDLC logon code.\nLeave blank if you do not have one.",
    "discord_presence": "Enable the DiscordEuroscope plugin?\nThis shows where you are controlling on your Discord profile.",
}

def _is_valid_cid(cid: str) -> bool:
    return cid.isdigit() and 6 <= len(cid) <= 7

def prompt_field(key: str, current: str = "") -> str:
    if key == "rating":
        return ask_rating(current)

    if key == "discord_presence":
        return "y" if ask_yesno(FIELD_PROMPTS[key]) else "n"

    prompt = FIELD_PROMPTS.get(key, f"Enter {key.replace('_', ' ')}.")
    while True:
        value = ask_string(prompt, current)
        if value is None:
            sys.exit()
        if key == "cid" and not _is_valid_cid(value):
            messagebox.showerror("Invalid CID", "CID must be a 6 or 7 digit number.")
            continue
        return value

# ── Config collection ──────────────────────────────────────────────────────────
def collect_config() -> dict:
    root = tk.Tk()
    _set_icon(root)
    root.title(WINDOW_TITLE)
    root.withdraw()
    tk._default_root = root
    _apply_theme(root)

    previous = _load_options()
    options: dict = {}

    if previous and ask_yesno("Load your previously saved options?"):
        options = dict(previous)

    for key in FIELDS:
        if not options.get(key):
            options[key] = prompt_field(key, options.get(key, ""))

    return options

# ── PRF restructure ────────────────────────────────────────────────────────────
def restructure_prf_files() -> None:
    """
    Move .prf files from the root folder into the sub-folders defined in
    structure.json.  Files already in a sub-folder (re-runs) are skipped.
    """
    structure = _load_structure()
    if not structure:
        return

    for prf_name, target_rel in structure.items():
        src = os.path.join(BASE_DIR, prf_name)
        if not os.path.exists(src):
            continue  # already moved or never present

        target_dir = os.path.join(BASE_DIR, target_rel)
        os.makedirs(target_dir, exist_ok=True)
        dst = os.path.join(target_dir, prf_name)
        try:
            shutil.move(src, dst)
            print(f"Moved: {prf_name} → {target_rel}")
        except Exception as exc:
            print(f"Could not move {prf_name}: {exc}")

# ── File patchers ──────────────────────────────────────────────────────────────
def _patch_prf_logon(path: str, name: str, initials: str,
                     cid: str, rating: str, password: str) -> None:
    try:
        lines = Path(path).read_text(encoding="utf-8").splitlines(keepends=True)
    except Exception as exc:
        print(f"Read failed {path}: {exc}")
        return

    drop = {"LastSession\trealname", "LastSession\tcertificate",
            "LastSession\trating",   "LastSession\tcallsign",
            "LastSession\tpassword"}
    lines = [l for l in lines if not any(l.startswith(d) for d in drop)]
    lines += [
        "\n",
        f"LastSession\trealname\t{name}\n",
        f"LastSession\tcertificate\t{cid}\n",
        f"LastSession\trating\t{rating}\n",
        f"LastSession\tcallsign\t{initials}_OBS\n",
        f"LastSession\tpassword\t{password}\n",
    ]
    try:
        Path(path).write_text("".join(lines), encoding="utf-8")
    except Exception as exc:
        print(f"Write failed {path}: {exc}")


def _discord_dll_relpath(prf_path: str) -> str:
    prf_dir = Path(prf_path).parent
    for candidate in [prf_dir, *prf_dir.parents]:
        plugin_dir = candidate / "Data" / "Plugin"
        if plugin_dir.exists():
            rel = os.path.relpath(plugin_dir / "DiscordEuroscope.dll", prf_dir)
            rel = rel.replace("/", "\\")
            return rel if rel.startswith("\\") else "\\" + rel
    return r"\..\Data\Plugin\DiscordEuroscope.dll"


def _patch_prf_discord(path: str, enable: bool) -> None:
    try:
        raw = Path(path).read_text(encoding="utf-8")
    except Exception as exc:
        print(f"Read failed {path}: {exc}")
        return

    lines = raw.replace("\r\n", "\n").replace("\r", "\n").split("\n")

    if not enable:
        cleaned = [l for l in lines if "DiscordEuroscope.dll" not in l]
        if cleaned != lines:
            Path(path).write_text("\n".join(cleaned).rstrip("\n") + "\n",
                                  encoding="utf-8", newline="\n" if hasattr(Path(path), 'write_text') else None)
        return

    if any("DiscordEuroscope.dll" in l for l in lines):
        return  # already present

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

    new_entry = f"Plugins\tPlugin{max_num + 1}\t{_discord_dll_relpath(path)}"
    if last_idx >= 0:
        lines.insert(last_idx + 1, new_entry)
    else:
        lines.extend(["", new_entry])

    try:
        with open(path, "w", encoding="utf-8", newline="\n") as fh:
            fh.write("\n".join(lines).rstrip("\n") + "\n")
    except Exception as exc:
        print(f"Write failed {path}: {exc}")


def _patch_profiles(path: str, cid: str) -> None:
    """
    Apply the default CID replacement plus any user-defined replacements from
    the saved config under "profiles_replacements": {"old": "new"}.
    Use {cid} in a replacement value to insert the actual CID.
    """
    try:
        content = Path(path).read_text(encoding="utf-8")
    except Exception as exc:
        print(f"Read failed {path}: {exc}")
        return

    replacements = {
        "Submit feedback at vats.im/atcfb":
            f"Submit feedback at vatsim.uk/atcfb?cid={cid}",
    }
    for find, replace in _load_options().get("profiles_replacements", {}).items():
        replacements[find] = replace.replace("{cid}", cid)

    for find, replace in replacements.items():
        content = content.replace(find, replace)

    try:
        Path(path).write_text(content, encoding="utf-8")
    except Exception as exc:
        print(f"Write failed {path}: {exc}")


def _patch_topsky_cpdlc(cpdlc: str) -> None:
    for rel in [
        "Data/Plugin/TopSky_iTEC/TopSkyCPDLChoppieCode.txt",
        "Data/Plugin/TopSky_NERC/TopSkyCPDLChoppieCode.txt",
        "Data/Plugin/TopSky_NODE/TopSkyCPDLChoppieCode.txt",
        "Data/Plugin/TopSky_NOVA/TopSkyCPDLChoppieCode.txt",
    ]:
        full = os.path.join(BASE_DIR, rel)
        os.makedirs(os.path.dirname(full), exist_ok=True)
        try:
            Path(full).write_text(cpdlc, encoding="utf-8")
        except Exception as exc:
            print(f"Write failed {full}: {exc}")

# ── Apply all patches ──────────────────────────────────────────────────────────
def apply_configuration(options: dict) -> None:
    name     = options["name"]
    initials = options["initials"]
    cid      = options["cid"]
    rating   = options["rating"]
    password = options["password"]
    cpdlc    = options["cpdlc"]
    discord  = options.get("discord_presence", "n") == "y"

    for dirpath, _, filenames in os.walk(BASE_DIR):
        for filename in filenames:
            path = os.path.join(dirpath, filename)

            if filename.endswith(".prf"):
                _patch_prf_logon(path, name, initials, cid, rating, password)
                _patch_prf_discord(path, discord)

            elif filename == "Profiles.txt":
                _patch_profiles(path, cid)

    _patch_topsky_cpdlc(cpdlc)

# ── Entry point ────────────────────────────────────────────────────────────────
def main() -> None:
    lockfile = os.path.join(BASE_DIR, "configurator.lock")
    if os.path.exists(lockfile):
        # Ensure a root window exists for messagebox
        _tmp = tk.Tk(); _tmp.withdraw()
        messagebox.showerror("Already Running", "The configurator is already running.")
        _tmp.destroy()
        sys.exit(1)

    Path(lockfile).write_text(str(os.getpid()))

    try:
        options = collect_config()
        restructure_prf_files()
        apply_configuration(options)
        _save_options(options)
        messagebox.showinfo("Complete", "Profile configuration complete.")
        time.sleep(1)
    finally:
        if os.path.exists(lockfile):
            os.remove(lockfile)


if __name__ == "__main__":
    try:
        main()
    finally:
        try:
            root = tk._default_root
            if root:
                root.destroy()
        except Exception:
            pass
        os._exit(0) if getattr(sys, "frozen", False) else sys.exit(0)