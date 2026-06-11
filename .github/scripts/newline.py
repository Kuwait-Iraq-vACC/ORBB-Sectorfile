from pathlib import Path

# Folder containing the map files
folder = Path(r"C:\GitHub\ORBB-Sectorfile\.data\TopSky Shared\Maps\Combined\(Extended) Centrelines")

for file_path in folder.glob("*"):
    if not file_path.is_file():
        continue

    try:
        content = file_path.read_text(encoding="utf-8")

        # Normalize line endings and remove trailing whitespace/newlines
        content = content.rstrip()

        # Skip files that already end with FILTER_ASR_OFF
        if content.endswith("FILTER_ASR_OFF"):
            print(f"Skipped (already present): {file_path.name}")
            continue

        # Add a blank line and FILTER_ASR_OFF
        content += "\n\nFILTER_ASR_OFF"

        file_path.write_text(content, encoding="utf-8")
        print(f"Updated: {file_path.name}")

    except Exception as e:
        print(f"Error processing {file_path.name}: {e}")

print("Done.")