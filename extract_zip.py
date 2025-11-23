"""Extract ZIP files to folders."""

import zipfile
from pathlib import Path

# Directories
INPUT_DIR = "wb_prayers/zips"
OUTPUT_DIR = "wb_prayers/extracted"

def main():
    input_path = Path(INPUT_DIR)
    output_path = Path(OUTPUT_DIR)
    
    if not input_path.exists():
        print(f"Directory '{INPUT_DIR}' not found")
        return
    
    # Create output directory
    output_path.mkdir(exist_ok=True)
    
    # Find all ZIP files recursively
    zip_files = list(input_path.rglob("*.zip"))
    
    if not zip_files:
        print(f"No ZIP files found in '{INPUT_DIR}'")
        return
    
    print(f"Found {len(zip_files)} ZIP file(s)")
    
    # Extract each ZIP to a folder, mirroring subfolders
    for zip_file in zip_files:
        rel_path = zip_file.relative_to(input_path)
        extract_to = output_path / rel_path.parent / zip_file.stem
        
        with zipfile.ZipFile(zip_file, 'r') as zip_ref:
            zip_ref.extractall(extract_to)
        
        print(f"✓ {rel_path} → {extract_to.relative_to(output_path)}/")
    
    print(f"\nExtracted {len(zip_files)} file(s) to '{OUTPUT_DIR}'")

if __name__ == "__main__":
    main()