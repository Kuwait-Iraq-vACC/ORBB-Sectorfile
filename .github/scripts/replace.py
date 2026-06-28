from pathlib import Path

# Folder containing the files
folder = Path(r"C:\GitHub\ORBB-Sectorfile")

# Set to None to process all files
# Example: ".prf", ".txt", ".ese"
# "file_extention = None"
file_extension = ".prf"

old_text = "Plugins	Plugin2	\ORBB\Plugins\TopSky\TopSky.dll\nPlugins	Plugin2Display0	Standard ES radar screen"
new_text = "Plugins	Plugin2	\ORBB\Plugins\TopSky\TopSky.dll\nPlugins	Plugin2Display0	Ground Radar display\nPlugins	Plugin2Display1	Standard ES radar screen"

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