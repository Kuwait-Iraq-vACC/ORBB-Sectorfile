from pathlib import Path

# Folder containing the files
folder = Path(r"C:\GitHub\ORBB-Sectorfile\.data\TopSky Shared\Maps\TMA\(Extended) Centrelines")

old_text = "\nZOOM:5"
new_text = ""

files_modified = 0

for file in folder.rglob("*"):
    if file.is_file():
        try:
            content = file.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            try:
                content = file.read_text(encoding="cp1252")
            except Exception:
                continue

        if old_text in content:
            content = content.replace(old_text, new_text)
            file.write_text(content, encoding="utf-8")
            files_modified += 1
            print(f"Modified: {file}")

print(f"\nDone. Modified {files_modified} file(s).")