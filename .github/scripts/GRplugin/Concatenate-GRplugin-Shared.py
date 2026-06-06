import os
import shutil

# ============================================================
# ORBB GRplugin Data File Compiler
# Compiles shared data files into the GRplugin directory
# ============================================================

OUTPUTS = [
    'ORBB/Plugins/GRplugin/',
    # 'ORBB/Plugins/GRplugin2/',  # Add more output paths here
]
SHARED   = '.data/GRplugin Shared/'
DATAFILES = '.data/DataFiles/'
INDEX    = '.Index.txt'


def main():
    copy_single_files()
    compile_aircraft_info()
    compile_cargo_callsigns()
    compile_operator_info()
    compile_maps()
    compile_settings()
    compile_settings_local()
    compile_stands()


# ============================================================
# Single-file copies (no compilation needed)
# ============================================================

def copy_single_files():
    singles = {
        DATAFILES + 'ICAO_Aircraft.json': 'ICAO_Aircraft.json',
    }
    for src, dst in singles.items():
        for output in OUTPUTS:
            copy_file(src, output + dst)


# ============================================================
# Compiled outputs
# ============================================================

def compile_aircraft_info():
    build_single(DATAFILES + 'Aircraft Info.txt', 'GRpluginAircraftInfo.txt')

def compile_cargo_callsigns():
    build_single(DATAFILES + 'Cargo Callsigns.txt', 'GRpluginCargoCallsigns.txt')

def compile_operator_info():
    build_single(DATAFILES + 'Operator Info.txt', 'GRpluginOperatorInfo.txt')

def compile_maps():
    build('Maps/', 'GRpluginMaps.txt')

def compile_settings():
    build('Settings/', 'GRpluginSettings.txt')

def compile_settings_local():
    build('Local Settings/', 'GRpluginSettingsLocal.txt')

def compile_stands():
    build('Stands/', 'GRpluginStands.txt')


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


def build_single(src, output_name):
    """
    Copies a single source file directly to all output directories.
    Used for DataFiles that are already complete (no concatenation needed).
    """
    if not os.path.exists(src):
        print(f'[WARN] Missing source: {src}')
        return

    for output in OUTPUTS:
        os.makedirs(output, exist_ok=True)
        dst = output + output_name
        shutil.copy(src, dst)
        print(f'[OK]   Copied {src} -> {dst}')


# ============================================================
# File ordering
# ============================================================

def get_file_list(folder_path, folder_label):
    """
    Returns an ordered list of relative file paths to compile.
    Priority:
      1. .Index.txt in the folder root (manual ordering)
         Supports:
           - Specific files:   SubFolder/File.txt
           - Whole subfolders: SubFolder/
         Files within a subfolder entry are discovered recursively
         and sorted alphabetically (subdirs first, then loose files).
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
                # Whole subfolder — discover all .txt files recursively, alphabetically
                sub_path = folder_path + line
                if not os.path.exists(sub_path):
                    print(f'[WARN] Subfolder not found: {sub_path}')
                    continue
                sub_files = collect_txt_recursive(sub_path, line)
                files.extend(sub_files)
                print(f'[INFO] {line} expanded to {len(sub_files)} file(s) (recursive)')

            elif '.' in line:
                # Specific file
                files.append(line)

            else:
                print(f'[WARN] Skipped index entry (no extension or /): "{line}" in {index_path}')

    print(f'[INFO] {folder_label} using index ({len(files)} entries)')
    return files


def collect_txt_recursive(abs_folder, rel_prefix):
    """
    Recursively collects all .txt files under abs_folder.
    Returns paths relative to the parent shared folder, prefixed with rel_prefix.
    Ordering: subdirectories alphabetically first (recursed), then loose
    .txt files at the current level alphabetically.
    """
    files = []

    try:
        entries = sorted(os.scandir(abs_folder), key=lambda e: e.name)
    except FileNotFoundError:
        print(f'[WARN] Folder not found: {abs_folder}')
        return files

    # Subdirectories first, recursed alphabetically
    for entry in entries:
        if entry.is_dir() and not entry.name.startswith('.'):
            sub_rel = rel_prefix + entry.name + '/'
            files.extend(collect_txt_recursive(entry.path, sub_rel))

    # Then loose .txt files at this level
    for entry in entries:
        if entry.is_file() and entry.name.endswith('.txt') and entry.name != '.Index.txt':
            files.append(rel_prefix + entry.name)

    return files


def auto_discover(folder_path):
    """
    Walks the folder structure:
      - Subdirectories first, sorted alphabetically (recursed)
      - .txt files within each subdir, sorted alphabetically
      - Then any loose .txt files at the root, sorted alphabetically
    """
    return collect_txt_recursive(folder_path, '')


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