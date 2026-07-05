import os, sys, json, shutil, time
import tkinter as tk
import customtkinter as ctk
from PIL import Image, ImageTk

RED      = "#C8102E"
RED_HOV  = "#A50D26"
BLACK    = "#0D0D0D"
SURFACE  = "#161616"
INPUT_BG = "#1F1F1F"
INPUT_BOR= "#2E2E2E"
WHITE    = "#F0F0F0"
MUTED    = "#7A7A7A"
SUCCESS  = "#4CAF50"
WARN     = "#E0A500"

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

def resource_path(filename):
    if getattr(sys, "frozen", False):
        bases = [sys._MEIPASS, os.path.dirname(sys.executable)]
    else:
        bases = [os.path.dirname(os.path.abspath(__file__))]
    for base in bases:
        p = os.path.join(base, filename)
        if os.path.exists(p):
            return p
    return os.path.join(bases[0], filename)

if getattr(sys, "frozen", False):
    _EXE_DIR = os.path.dirname(sys.executable)
else:
    _EXE_DIR = os.path.dirname(os.path.abspath(__file__))

OPTIONS_PATH           = os.path.join(_EXE_DIR, "configurator_config.json")
DEFAULT_STRUCTURE_JSON = resource_path("structure.json")

def _find_pack_root():
    """
    Find the repository root where .prf files are stored.
    Configurator\ → Plugins\ → ORBB\ → repo root
    e.g. C:\GitHub\ORBB-Sectorfile\ORBB\Plugins\Configurator\ → C:\GitHub\ORBB-Sectorfile\
    """
    # Start from the executable directory
    current = _EXE_DIR

    # Go up 3 levels: Configurator\ → Plugins\ → ORBB\ → repo root
    for _ in range(3):
        parent = os.path.dirname(current)
        if parent == current:
            break
        current = parent

    # Check if this looks like the repo root (contains ORBB folder)
    if os.path.exists(os.path.join(current, "ORBB")):
        return current

    # Fallback: look for ORBB folder in parent directories
    current = _EXE_DIR
    for _ in range(5):
        if os.path.exists(os.path.join(current, "ORBB")):
            return current
        parent = os.path.dirname(current)
        if parent == current:
            break
        current = parent

    return os.path.abspath(os.path.join(_EXE_DIR, "..", "..", ".."))

PACK_ROOT = _find_pack_root()

def get_structure_json_path():
    try:
        with open(OPTIONS_PATH, encoding="utf-8") as f:
            saved = json.load(f)
        override = saved.get("structure_json_path", "").strip()
        if override and os.path.isabs(override):
            return override
    except Exception:
        pass
    return DEFAULT_STRUCTURE_JSON

def load_structure():
    path = get_structure_json_path()
    if not os.path.exists(path):
        return {}
    with open(path, encoding="utf-8") as f:
        return json.load(f)

def load_previous_options():
    try:
        with open(OPTIONS_PATH, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}

def save_options(options):
    with open(OPTIONS_PATH, "w", encoding="utf-8") as f:
        json.dump(options, f, indent=4)

def validate_cid(cid):
    if not cid:
        return "CID is required."
    if not cid.isdigit():
        return "CID must contain digits only."
    if len(cid) < 6:
        return f"CID is too short ({len(cid)} digits) - must be 6 or 7 digits."
    if len(cid) > 7:
        return f"CID is too long ({len(cid)} digits) - must be 6 or 7 digits."
    return None

# Ratings stored as EuroScope/VATSIM numeric codes
RATINGS = [
    ("Observer (OBS)",             "0"),
    ("Developing Controller (S1)", "1"),
    ("Aerodrome Controller (S2)",  "2"),
    ("Terminal Controller (S3)",   "3"),
    ("Enroute Controller (C1)",    "4"),
    ("Senior Controller (C3)",     "6"),
    ("Instructor (I1)",            "7"),
    ("Senior Instructor (I3)",     "9"),
    ("Supervisor (SUP)",           "10"),
    ("Administrator (ADM)",        "11"),
]
RATING_DISPLAY = [r[0] for r in RATINGS]
RATING_CODE    = {r[0]: r[1] for r in RATINGS}
RATING_DEFAULT = "0"

STEPS = [
    {"key": "name",     "title": "Full name",         "hint": "Enter your preferred name convention.\n(VATSIM Code of Conduct A4(B))",         "placeholder": "e.g. John Smith",  "type": "entry"},
    {"key": "initials", "title": "Callsign initials", "hint": "Enter your callsign initials, e.g. AB or JS.\n(VATSIM Code of Conduct A4(B))",  "placeholder": "e.g. JS",          "type": "entry"},
    {"key": "rating",   "title": "Controller rating", "hint": "Select your current VATSIM controller rating.",                                   "type": "combo"},
    {"key": "cid",      "title": "VATSIM CID",        "hint": "Enter your CID - must be 6 or 7 digits.",                                        "placeholder": "e.g. 1234567",     "type": "entry"},
    {"key": "password", "title": "Network password",  "hint": "Enter your VATSIM network password.",                                            "placeholder": "........",         "type": "password"},
    {"key": "cpdlcc",   "title": "ACARS logon code",  "hint": "Enter your Hoppie ACARS logon code for CPDLC.\nLeave blank if not required.",    "placeholder": "e.g. ABCDE12345",  "type": "entry"},
]

# Business logic

def restructure_prf_files(structure):
    """
    Move .prf files from PACK_ROOT into the folders defined in structure.json.
    Using the exact same logic as your working code.
    """
    print(f"PACK_ROOT: {PACK_ROOT}")
    print(f"Structure: {structure}")

    if not structure:
        print("No structure defined, skipping reorganization.")
        return 0

    moved = []
    skipped = []
    not_found = []

    for prf_name, target_rel in structure.items():
        src = os.path.join(PACK_ROOT, prf_name)

        if not os.path.exists(src):
            print(f"❌ '{prf_name}' not found at {src}")
            not_found.append(prf_name)
            continue

        # Remove trailing slash if present and create target directory
        target_rel_clean = target_rel.rstrip('/')
        target_dir = os.path.join(PACK_ROOT, target_rel_clean)
        os.makedirs(target_dir, exist_ok=True)

        dst = os.path.join(target_dir, prf_name)

        try:
            # If the file is already in the correct location, skip it
            if os.path.abspath(src) == os.path.abspath(dst):
                print(f"✓ '{prf_name}' already in correct location: {target_rel_clean}/")
                continue

            # If target exists, remove it first (force overwrite)
            if os.path.exists(dst):
                os.remove(dst)

            shutil.move(src, dst)
            moved.append(f"  {prf_name}  →  {target_rel_clean}/")
            print(f"✓ Moved '{prf_name}' to '{target_rel_clean}/'")
        except Exception as e:
            skipped.append(f"  {prf_name}: {e}")
            print(f"❌ Error moving '{prf_name}': {e}")

    # Print summary
    if moved:
        print("\n📦 Moved PRF files:")
        print("\n".join(moved))
    if skipped:
        print("\n⚠️ Could not move:")
        print("\n".join(skipped))
    if not_found:
        print(f"\n❌ Files not found in PACK_ROOT ({PACK_ROOT}):")
        for f in not_found:
            print(f"  - {f}")

        # Show what IS in PACK_ROOT
        print(f"\n📂 Files currently in PACK_ROOT:")
        try:
            for item in os.listdir(PACK_ROOT):
                item_path = os.path.join(PACK_ROOT, item)
                if os.path.isfile(item_path) and item.endswith('.prf'):
                    print(f"  - {item}")
        except Exception as e:
            print(f"  Could not list directory: {e}")

    print(f"\n📊 Summary: Moved {len(moved)} files, {len(skipped)} errors, {len(not_found)} not found")
    return len(moved)

def patch_prf_file(file_path, options):
    """
    Patch a .prf file with the provided options.
    Replaces existing lines instead of adding duplicates.
    """
    print(f"Patching: {file_path}")

    with open(file_path, encoding="utf-8", errors="replace") as f:
        lines = f.readlines()

    cid         = options.get("cid", "")
    rating_code = options.get("rating", RATING_DEFAULT)
    name        = options.get("name", "")
    password    = options.get("password", "")
    initials    = options.get("initials", "").strip().upper()
    callsign    = f"{initials}_OBS" if initials else ""

    # Track which settings we've found and updated
    found_settings = {
        "realname": False,
        "certificate": False,
        "rating": False,
        "callsign": False,
        "password": False,
        "server": False
    }

    new_lines = []

    # First pass: Update existing lines
    for line in lines:
        line_updated = False

        if line.startswith("LastSession\trealname\t"):
            new_lines.append(f"LastSession\trealname\t{name}\n")
            found_settings["realname"] = True
            line_updated = True
        elif line.startswith("LastSession\tcertificate\t"):
            new_lines.append(f"LastSession\tcertificate\t{cid}\n")
            found_settings["certificate"] = True
            line_updated = True
        elif line.startswith("LastSession\trating\t"):
            new_lines.append(f"LastSession\trating\t{rating_code}\n")
            found_settings["rating"] = True
            line_updated = True
        elif line.startswith("LastSession\tcallsign\t"):
            new_lines.append(f"LastSession\tcallsign\t{callsign}\n")
            found_settings["callsign"] = True
            line_updated = True
        elif line.startswith("LastSession\tpassword\t"):
            new_lines.append(f"LastSession\tpassword\t{password}\n")
            found_settings["password"] = True
            line_updated = True
        elif line.startswith("LastSession\tserver\t"):
            new_lines.append("LastSession\tserver\tAUTOMATIC\n")
            found_settings["server"] = True
            line_updated = True

        # Keep line if it wasn't updated
        if not line_updated:
            new_lines.append(line)

    # Find where to insert missing settings (after server line, or at the end)
    insert_pos = len(new_lines)
    for i, line in enumerate(new_lines):
        if line.startswith("LastSession\tserver\t"):
            insert_pos = i + 1
            found_settings["server"] = True
            break

    # Prepare missing settings to insert
    missing_settings = []
    if not found_settings["realname"] and name:
        missing_settings.append(f"LastSession\trealname\t{name}\n")
    if not found_settings["certificate"] and cid:
        missing_settings.append(f"LastSession\tcertificate\t{cid}\n")
    if not found_settings["rating"] and rating_code:
        missing_settings.append(f"LastSession\trating\t{rating_code}\n")
    if not found_settings["callsign"] and callsign:
        missing_settings.append(f"LastSession\tcallsign\t{callsign}\n")
    if not found_settings["password"] and password:
        missing_settings.append(f"LastSession\tpassword\t{password}\n")
    if not found_settings["server"]:
        missing_settings.insert(0, "LastSession\tserver\tAUTOMATIC\n")

    # Insert missing settings
    if missing_settings:
        new_lines = new_lines[:insert_pos] + missing_settings + new_lines[insert_pos:]
        print(f"Added {len(missing_settings)} missing settings to {os.path.basename(file_path)}")

    with open(file_path, "w", encoding="utf-8", errors="replace") as f:
        f.writelines(new_lines)

    print(f"✓ Successfully patched {os.path.basename(file_path)}")

def patch_profiles_file(file_path, options):
    try:
        with open(file_path, encoding="utf-8", errors="replace") as f:
            content = f.read()
    except Exception:
        return
    cid = options.get("cid", "")
    content = content.replace("Submit feedback at PLACEHOLDER", f"Submit feedback at placeholder?cid={cid}")
    for find, replace in load_previous_options().get("profiles_replacements", {}).items():
        content = content.replace(find, replace.replace("{cid}", cid))
    try:
        with open(file_path, "w", encoding="utf-8", errors="replace") as f:
            f.write(content)
    except Exception:
        pass

def patch_topsky_cpdlc(options):
    code = options.get("cpdlcc", "").strip()
    if not code:
        return 0
    updated = 0
    for root, dirs, files in os.walk(PACK_ROOT):
        for f in files:
            if f == "TopSkyCPDLChoppieCode.txt":
                try:
                    with open(os.path.join(root, f), "w", encoding="utf-8") as fh:
                        fh.write(code)
                    updated += 1
                except Exception:
                    pass
    return updated

def apply_configuration(options):
    if not os.path.isdir(PACK_ROOT):
        raise ValueError(
            f"Could not find the package root.\n"
            f"Looked at: {PACK_ROOT}\n"
            f"Exe directory: {_EXE_DIR}\n\n"
            f"Make sure Configurator.exe is in the correct location."
        )

    print(f"PACK_ROOT: {PACK_ROOT}")
    print(f"Options: {options}")

    # Load structure and restructure
    structure = load_structure()
    print(f"Loaded structure with {len(structure)} entries")

    # Restructure .prf files
    restructure_prf_files(structure)

    patched_files = []
    errors = []
    prf_seen = False

    # Now patch all .prf files - search everywhere in PACK_ROOT
    for root, dirs, files in os.walk(PACK_ROOT):
        for file in files:
            fp = os.path.join(root, file)
            if file.endswith(".prf"):
                prf_seen = True
                try:
                    print(f"Patching profile: {file} at {fp}")
                    patch_prf_file(fp, options)
                    patch_profiles_file(fp, options)
                    patched_files.append(os.path.basename(fp))
                except Exception as e:
                    print(f"Error patching {file}: {e}")
                    errors.append((os.path.basename(fp), str(e)))
            elif file == "Bandbox.txt":
                try:
                    patch_profiles_file(fp, options)
                except Exception as e:
                    errors.append((file, str(e)))

    if not prf_seen:
        raise ValueError(
            f"No .prf files were found under:\n{PACK_ROOT}\n\n"
            f"Exe directory: {_EXE_DIR}\n"
            f"Make sure the .prf files are in the package root folder."
        )

    cpdlc_updated = patch_topsky_cpdlc(options)
    return patched_files, cpdlc_updated, errors

# [Rest of the UI code remains the same...]

# Main window class Configurator (keep the same as before)
# ...

def main():
    # [Keep the same main function]
    pass

if __name__ == "__main__":
    main()