from pathlib import Path

# Repo root (this script lives in .github/scripts/)
folder = Path(__file__).resolve().parents[2]

# Set to None to process all files
# Example: ".prf", ".txt", ".ese"
# "file_extention = None"
file_extension = ".prf"

old_text = "Plugins	Plugin1Display0	Ground Radar display\nPlugins	Plugin1Display1	Standard ES radar screen"
new_text = "Plugins	Plugin1Display0	Standard ES radar screen"

files_modified = 0

for file in folder.rglob("*"):
    if not file.is_file():
        continue

    # Skip files that don't match the selected extension
    if file_extension and file.suffix.lower() != file_extension.lower():
        continue

    # Remember which encoding worked so the file is written back the same
    # way — EuroScope .prf files are often cp1252, and re-saving them as
    # UTF-8 mangles any non-ASCII characters for EuroScope.
    for encoding in ("utf-8", "cp1252"):
        try:
            content = file.read_text(encoding=encoding)
            break
        except UnicodeDecodeError:
            continue
    else:
        print(f"Skipped (unreadable encoding): {file}")
        continue

    if old_text in content:
        content = content.replace(old_text, new_text)
        file.write_text(content, encoding=encoding)
        files_modified += 1
        print(f"Modified: {file}")

print(f"\nDone. Modified {files_modified} file(s).")