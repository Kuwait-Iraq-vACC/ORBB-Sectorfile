#!/usr/bin/env python3
"""
VFPC JSON Data File Compiler
Combines multiple JSON files from a folder into a single JSON array output
"""

import os
import json
import shutil
from typing import List, Dict, Any

# ============================================================
# Configuration
# ============================================================

OUTPUTS = [
    'ORBB/Plugins/VFPC/',  # Primary output directory
    # Add more output paths here if needed
]

SHARED_DIR = '.data/VFPC/'
OUTPUT_FILENAME = 'Sid.json'
INDEX_FILENAME = '.Index.txt'

# ============================================================
# Main execution
# ============================================================

def main():
    """Main entry point for the compiler"""
    combined_data = combine_json_files()
    
    if combined_data is None:
        print('[ERROR] No data to compile, aborting')
        return
    
    write_output_file(combined_data)
    print('[DONE] JSON compilation complete')


def combine_json_files() -> List[Dict[str, Any]]:
    """
    Combine multiple JSON files from the shared directory into a single list
    
    Returns:
        List containing all combined JSON data from all files
    """
    if not os.path.exists(SHARED_DIR):
        print(f'[ERROR] Shared directory not found: {SHARED_DIR}')
        return None
    
    # Get ordered list of JSON files
    json_files = get_json_file_list()
    
    if not json_files:
        print(f'[WARN] No JSON files found in {SHARED_DIR}')
        return None
    
    combined_data = []
    files_processed = 0
    
    for filename in json_files:
        file_path = os.path.join(SHARED_DIR, filename)
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # Handle both array and object formats
            if isinstance(data, list):
                # If it's a list, extend our combined list
                combined_data.extend(data)
                print(f'[OK]   Loaded {filename} ({len(data)} items)')
                files_processed += 1
            elif isinstance(data, dict):
                # If it's a dict, append it as a single item
                combined_data.append(data)
                print(f'[OK]   Loaded {filename} (1 object)')
                files_processed += 1
            else:
                print(f'[WARN] Skipped {filename}: Unexpected JSON type {type(data).__name__}')
                
        except json.JSONDecodeError as e:
            print(f'[ERROR] Invalid JSON in {filename}: {e}')
        except Exception as e:
            print(f'[ERROR] Failed to read {filename}: {e}')
    
    if files_processed == 0:
        print('[ERROR] No valid JSON files were processed')
        return None
    
    print(f'[INFO] Total items in combined data: {len(combined_data)}')
    return combined_data


def get_json_file_list() -> List[str]:
    """
    Returns an ordered list of JSON files to compile.
    Priority:
      1. .Index.txt in the folder root (manual ordering)
      2. Auto-discovery: all .json files alphabetically
    """
    index_path = os.path.join(SHARED_DIR, INDEX_FILENAME)
    
    if os.path.exists(index_path):
        return read_index(index_path)
    
    return auto_discover()


def read_index(index_path: str) -> List[str]:
    """
    Read the .Index.txt file to get ordered list of JSON files
    
    .Index.txt format:
        ORER.json     // Comments are supported
        ORBI.json
        // This is a comment line
        AnotherFile.json
    
    Returns:
        List of filenames in the order they should be processed
    """
    files = []
    
    with open(index_path, 'r', encoding='utf-8') as f:
        for line_num, raw_line in enumerate(f, 1):
            # Strip comments and whitespace
            line = raw_line.split('//')[0].strip()
            
            if not line:
                continue
            
            # Check if it's a JSON file
            if line.endswith('.json'):
                file_path = os.path.join(SHARED_DIR, line)
                if os.path.exists(file_path):
                    files.append(line)
                    print(f'[INFO] Index includes: {line}')
                else:
                    print(f'[WARN] Index line {line_num}: File not found - {line}')
            else:
                print(f'[WARN] Index line {line_num}: Skipped non-JSON entry - {line}')
    
    print(f'[INFO] Using .Index.txt with {len(files)} file(s)')
    return files


def auto_discover() -> List[str]:
    """
    Auto-discover all JSON files in the shared directory, sorted alphabetically
    
    Returns:
        Sorted list of JSON filenames
    """
    files = []
    
    try:
        for entry in sorted(os.scandir(SHARED_DIR), key=lambda e: e.name):
            if entry.is_file() and entry.name.endswith('.json') and not entry.name.startswith('.'):
                files.append(entry.name)
    except FileNotFoundError:
        print(f'[ERROR] Directory not found: {SHARED_DIR}')
        return files
    
    print(f'[INFO] Auto-discovered {len(files)} JSON file(s)')
    for f in files:
        print(f'[INFO]   - {f}')
    
    return files


def write_output_file(data: List[Dict[str, Any]]):
    """
    Write the combined JSON data to output directories
    
    Args:
        data: List containing the combined JSON data
    """
    # Create primary output directory if needed
    primary_output = OUTPUTS[0]
    os.makedirs(primary_output, exist_ok=True)
    
    output_path = os.path.join(primary_output, OUTPUT_FILENAME)
    
    # Write the combined JSON file
    try:
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=3, ensure_ascii=False)
        
        file_size = os.path.getsize(output_path)
        print(f'[OK]   Written {output_path} ({file_size:,} bytes)')
        
        # Pretty print first few items for verification
        if data:
            print(f'[INFO] Output contains {len(data)} airport entries')
            for i, item in enumerate(data[:3]):
                if 'icao' in item:
                    print(f'[INFO]   Entry {i+1}: {item["icao"]}')
        
    except Exception as e:
        print(f'[ERROR] Failed to write {output_path}: {e}')
        return
    
    # Copy to additional output directories if specified
    for output_dir in OUTPUTS[1:]:
        os.makedirs(output_dir, exist_ok=True)
        copy_path = os.path.join(output_dir, OUTPUT_FILENAME)
        shutil.copy(output_path, copy_path)
        print(f'[OK]   Copied to {copy_path}')


# ============================================================
# Advanced: Deep merge mode (if you want to merge objects instead)
# ============================================================

def deep_merge_json_files() -> Dict[str, Any]:
    """
    Alternative: Deep merge JSON objects instead of concatenating arrays
    
    Useful if your JSON files are objects that need to be merged
    """
    json_files = get_json_file_list()
    
    if not json_files:
        print(f'[WARN] No JSON files found in {SHARED_DIR}')
        return None
    
    merged_data = {}
    
    for filename in json_files:
        file_path = os.path.join(SHARED_DIR, filename)
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            if isinstance(data, dict):
                # Deep merge dictionaries
                for key, value in data.items():
                    if key in merged_data:
                        # Handle conflicts - you might want custom logic here
                        print(f'[WARN] Key "{key}" already exists, overwriting from {filename}')
                    merged_data[key] = value
                print(f'[OK]   Merged {filename}')
            else:
                print(f'[WARN] Skipped {filename}: Expected dict for deep merge, got {type(data).__name__}')
                
        except json.JSONDecodeError as e:
            print(f'[ERROR] Invalid JSON in {filename}: {e}')
        except Exception as e:
            print(f'[ERROR] Failed to read {filename}: {e}')
    
    return merged_data if merged_data else None


if __name__ == '__main__':
    main()