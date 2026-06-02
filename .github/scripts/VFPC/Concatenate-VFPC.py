import os
import json

# ============================================================
# ORBB VFPC Data File Compiler
# Merges individual airport VFPC JSON files into a single
# combined output for the VFPC plugin.
# ============================================================

VFPC_SOURCE = '.data/VFPC/'
OUTPUT_FILE = 'ORBB/Plugins/VFPC/VFPC.json'
INDEX       = '.Index.txt'


def main():
    compile_vfpc()


# ============================================================
# Core compile logic
# ============================================================

def compile_vfpc():
    """
    Merges all airport VFPC JSON files from VFPC_SOURCE into a single
    JSON array and writes it to OUTPUT_FILE.
    Uses .Index.txt for ordering if present; otherwise discovers
    all .json files alphabetically (excluding dot-files).
    """
    files = get_file_list(VFPC_SOURCE)

    if not files:
        print(f'[SKIP] No VFPC JSON files found in {VFPC_SOURCE}')
        return

    merged = []
    loaded = 0
    skipped = 0

    for relative_path in files:
        full_path = VFPC_SOURCE + relative_path
        if not os.path.exists(full_path):
            print(f'[WARN] Missing: {full_path}')
            skipped += 1
            continue

        try:
            with open(full_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
        except json.JSONDecodeError as e:
            print(f'[ERROR] Invalid JSON in {full_path}: {e}')
            skipped += 1
            continue

        # Each file may be a single airport object or a list of them
        if isinstance(data, list):
            merged.extend(data)
            loaded += len(data)
        elif isinstance(data, dict):
            merged.append(data)
            loaded += 1
        else:
            print(f'[WARN] Unexpected JSON structure in {full_path} — skipped')
            skipped += 1
            continue

        print(f'[OK]   Loaded {full_path}')

    if not merged:
        print('[SKIP] No valid entries to write.')
        return

    # Sanity check — warn on duplicate ICAOs
    check_duplicates(merged)

    os.makedirs(os.path.dirname(OUTPUT_FILE), exist_ok=True)
    with open(OUTPUT_FILE, 'w', encoding='utf-8') as out:
        json.dump(merged, out, indent=3, ensure_ascii=False)
        out.write('\n')

    print(f'[OK]   Compiled {loaded} airport(s) -> {OUTPUT_FILE}'
          + (f' ({skipped} skipped)' if skipped else ''))


# ============================================================
# Duplicate ICAO detection
# ============================================================

def check_duplicates(entries):
    seen = {}
    for entry in entries:
        icao = entry.get('icao', '<unknown>')
        if icao in seen:
            print(f'[WARN] Duplicate ICAO "{icao}" — check source files')
        else:
            seen[icao] = True


# ============================================================
# File ordering
# ============================================================

def get_file_list(folder_path):
    """
    Returns an ordered list of relative .json file paths to compile.
    Priority:
      1. .Index.txt in the folder root (manual ordering)
         Supports:
           - Specific files:   ORMM.json
           - Whole subfolders: Subdir/
      2. Auto-discovery: all .json files alphabetically
         (excludes dot-files and the index itself)
    """
    index_path = folder_path + INDEX

    if os.path.exists(index_path):
        return read_index(index_path, folder_path)

    return auto_discover(folder_path)


def read_index(index_path, folder_path):
    files = []
    with open(index_path, 'r', encoding='utf-8') as f:
        for raw_line in f:
            line = raw_line.split('//')[0].strip()
            if not line:
                continue

            if line.endswith('/'):
                # Whole subfolder — discover all .json files alphabetically
                sub_path = folder_path + line
                if not os.path.exists(sub_path):
                    print(f'[WARN] Subfolder not found: {sub_path}')
                    continue
                sub_files = sorted(
                    e.name for e in os.scandir(sub_path)
                    if e.is_file() and e.name.endswith('.json')
                    and not e.name.startswith('.')
                )
                for f_name in sub_files:
                    files.append(line + f_name)
                print(f'[INFO] {line} expanded to {len(sub_files)} file(s)')

            elif line.endswith('.json'):
                files.append(line)

            else:
                print(f'[WARN] Skipped index entry (not .json or /): "{line}" in {index_path}')

    print(f'[INFO] Using index ({len(files)} entries)')
    return files


def auto_discover(folder_path):
    """
    Returns all .json files in the folder, sorted alphabetically.
    Excludes dot-files and subdirectories (flat discovery only at root).
    For subdirectory support, use .Index.txt.
    """
    files = []

    try:
        entries = sorted(os.scandir(folder_path), key=lambda e: e.name)
    except FileNotFoundError:
        print(f'[WARN] Folder not found: {folder_path}')
        return files

    for entry in entries:
        if entry.is_file() and entry.name.endswith('.json') and not entry.name.startswith('.'):
            files.append(entry.name)

    print(f'[INFO] Auto-discovered {len(files)} file(s) in {folder_path}')
    return files


if __name__ == '__main__':
    main()