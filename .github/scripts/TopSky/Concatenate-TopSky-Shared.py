import os
import shutil

# ============================================================
# ORBB TopSky Data File Compiler
# Compiles shared data files into the TopSky plugin directory
# ============================================================

OUTPUTS = [
    'ORBB/Plugins/TopSky/',
    # 'ORBB/Plugins/TopSky2/',  # Add more output paths here
]
SHARED = '.data/TopSky Shared/'
INDEX  = '.Index.txt'


def main():
    copy_single_files()
    compile_areas()
    compile_airspace()
    compile_cpdlc()
    compile_maps()
    compile_msaw()
    compile_radars()
    compile_ssr_codes()
    compile_settings()


# ============================================================
# Single-file copies (no compilation needed)
# ============================================================

def copy_single_files():
    singles = {
        'ICAO/ICAO_Aircraft.json':  'ICAO_Aircraft.json',
        'ICAO/ICAO_Aircraft.txt':   'ICAO_Aircraft.txt',
        'ICAO/ICAO_Airlines.txt':   'ICAO_Airlines.txt',
        'ICAO/ICAO_Airports.txt':   'ICAO_Airports.txt',
    }
    for src, dst in singles.items():
        for output in OUTPUTS:
            copy_file(SHARED + src, output + dst)


# ============================================================
# Compiled outputs
# ============================================================

def compile_areas():
    build('Areas/', 'TopSkyAreas.txt')

def compile_airspace():
    build('Airspace/', 'TopSkyAirspace.txt')

def compile_cpdlc():
    build('CPDLC/', 'TopSkyCPDLC.txt')

def compile_maps():
    build('Maps/', 'TopSkyMaps.txt')

def compile_msaw():
    build('MSAW/', 'TopSkyMSAW.txt')

def compile_radars():
    build('Radars/', 'TopSkyRadars.txt')

def compile_ssr_codes():
    build('SSRcodes/', 'TopSkySSRcodes.txt')

def compile_settings():
    build('Settings/', 'TopSkySettings.txt')


# ============================================================
# Core build logic
# ============================================================

def build(folder, output_name):
    """
    Compiles all .txt files in a shared folder into a single output file,
    then copies the result to all output directories.
    Uses .Index.txt for ordering if present; otherwise recurses
    subdirectories and loose files alphabetically.
    """
    src_folder = SHARED + folder

    files = get_file_list(src_folder, folder)
    if not files:
        print(f'[SKIP] No files found for {output_name}')
        return

    # Build into the first output, then copy to the rest
    primary = OUTPUTS[0] + output_name
    os.makedirs(OUTPUTS[0], exist_ok=True)

    with open(primary, 'wb') as out:
        for relative_path in files:
            full_path = src_folder + relative_path
            if not os.path.exists(full_path):
                print(f'[WARN] Missing: {full_path}')
                continue
            with open(full_path, 'rb') as f:
                shutil.copyfileobj(f, out)
                out.write(b'\n\n')

    print(f'[OK]   Built {primary} from {len(files)} file(s)')

    for output in OUTPUTS[1:]:
        os.makedirs(output, exist_ok=True)
        dst = output + output_name
        shutil.copy(primary, dst)
        print(f'[OK]   Copied to {dst}')


# ============================================================
# File ordering
# ============================================================

def get_file_list(folder_path, folder_label):
    """
    Returns an ordered list of relative file paths to compile.
    Priority:
      1. .Index.txt in the folder root (manual ordering)
         Supports:
           - Specific files:   CategoryDefinitions/CategoryDefs.txt
           - Whole subfolders: Prohibited/
         Files within a subfolder entry are sorted alphabetically.
      2. Auto-discovery: subdirs alphabetically, then loose root .txt files
    """
    index_path = folder_path + INDEX

    if os.path.exists(index_path):
        return read_index(index_path, folder_label, folder_path)

    return auto_discover(folder_path)


def read_index(index_path, folder_label, folder_path):
    files = []
    with open(index_path, 'r') as f:
        for raw_line in f:
            line = raw_line.split('//')[0].strip()  # strip comments
            if not line:
                continue

            if line.endswith('/'):
                # Whole subfolder — discover all .txt files alphabetically
                sub_path = folder_path + line
                if not os.path.exists(sub_path):
                    print(f'[WARN] Subfolder not found: {sub_path}')
                    continue
                sub_files = sorted(
                    e.name for e in os.scandir(sub_path)
                    if e.is_file() and e.name.endswith('.txt')
                )
                for f_name in sub_files:
                    files.append(line + f_name)
                print(f'[INFO] {line} expanded to {len(sub_files)} file(s)')

            elif '.' in line:
                # Specific file
                files.append(line)

            else:
                print(f'[WARN] Skipped index entry (no extension or /): "{line}" in {index_path}')

    print(f'[INFO] {folder_label} using index ({len(files)} entries)')
    return files


def auto_discover(folder_path):
    """
    Walks the folder structure recursively:
      - All subdirectories (depth-first, sorted alphabetically at each level)
      - .txt files within each subdir, sorted alphabetically
      - Then any loose .txt files at the root, sorted alphabetically
    """
    files = []

    try:
        entries = sorted(os.scandir(folder_path), key=lambda e: e.name)
    except FileNotFoundError:
        print(f'[WARN] Folder not found: {folder_path}')
        return files

    for entry in entries:
        if entry.is_dir() and not entry.name.startswith('.'):
            # Recurse and prefix relative paths with the subdir name
            sub_files = auto_discover(entry.path)
            for f in sub_files:
                files.append(os.path.join(entry.name, f))

    for entry in entries:
        if entry.is_file() and entry.name.endswith('.txt'):
            files.append(entry.name)

    return files


# ============================================================
# File utilities
# ============================================================

def copy_file(src, dst):
    if not os.path.exists(src):
        print(f'[WARN] Missing source: {src}')
        return
    parent = os.path.dirname(dst)
    if parent:
        os.makedirs(parent, exist_ok=True)
    shutil.copy(src, dst)
    print(f'[OK]   Copied {src} -> {dst}')


if __name__ == '__main__':
    main()