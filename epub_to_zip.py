"""Convert EPUB files to ZIP files."""

import shutil
from pathlib import Path

# Directory containing EPUB files
INPUT_DIR = "wb_prayers/epubs"
OUTPUT_DIR = "wb_prayers/zips"

def main():
    input_dir = Path(INPUT_DIR)
    
    if not input_dir.exists():
        print(f"Directory '{INPUT_DIR}' not found")
        return
    
    # Find all EPUB files recursively
    epub_files = list(input_dir.rglob("*.epub"))
    
    if not epub_files:
        print(f"No EPUB files found in '{INPUT_DIR}'")
        return
    
    print(f"Found {len(epub_files)} EPUB file(s)")
    in_place = (OUTPUT_DIR == "" or OUTPUT_DIR == INPUT_DIR)
    output_dir = input_dir if in_place else Path(OUTPUT_DIR)
    if not in_place:
        output_dir.mkdir(parents=True, exist_ok=True)
    
    # Convert each EPUB to ZIP
    for epub_file in epub_files:
        # Mirror subfolder structure from input to output
        rel_path = epub_file.relative_to(input_dir)
        dest_dir = output_dir / rel_path.parent
        dest_dir.mkdir(parents=True, exist_ok=True)
        zip_file = dest_dir / (epub_file.stem + ".zip")
        shutil.copy2(epub_file, zip_file)
        print(f"✓ {rel_path} → {zip_file.relative_to(output_dir)}")
    
    print(f"\nConverted {len(epub_files)} file(s)")

if __name__ == "__main__":
    main()