from pathlib import Path

# Folder containing the files
folder = Path(r"C:\GitHub\ORBB-Sectorfile")

# Set to None to process all files
# Example: ".prf", ".txt", ".ese"
# "file_extention = None"
file_extension = ".prf"

old_text = "ORBB-Developer_20260612184253-260601-0003"
new_text = "ORBB-Install-Package_20260615160335-260601-0002"

files_modified = 0

for file in folder.rglob("*"):
    if not file.is_file():
        continue

    # Skip files that don't match the selected extension
    if file_extension and file.suffix.lower() != file_extension.lower():
        continue

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