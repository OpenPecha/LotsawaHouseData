"""Extract data from Lotsawa HTML files and convert to individual JSON files."""

import json
from pathlib import Path
from bs4 import BeautifulSoup

# Directories
INPUT_DIR = "lotsawa_prayers_extracted"
OUTPUT_DIR = "lotsawa_prayers_final_json"


def extract_footer_data(footer_path):
    """Extract source and copyright URLs from footer.html."""
    with open(footer_path, 'r', encoding='utf-8') as f:
        soup = BeautifulSoup(f.read(), 'html.parser')
    
    # Extract source URL from the "generated-txt" paragraph
    generated_para = soup.find('p', class_='generated-txt')
    source_url = ""
    if generated_para:
        source_link = generated_para.find('a', href=True)
        if source_link:
            source_url = source_link['href']
    
    # Extract copyright URL
    copyright_link = soup.find('a', rel='license')
    copyright_url = copyright_link['href'] if copyright_link else ""
    
    return source_url, copyright_url


def extract_text_data(text_path):
    """Extract title and verses from text0.html."""
    with open(text_path, 'r', encoding='utf-8') as f:
        soup = BeautifulSoup(f.read(), 'html.parser')
    
    # Extract titles - try multiple tag types and classes
    title_bo = ""
    title_en = ""
    
    # Try to find Tibetan title in heading tags only
    tib_title = (soup.find('h2', class_='tib') or 
                 soup.find('h1', class_='tib') or
                 soup.find('h3', class_='tib'))
    
    if tib_title:
        title_bo = tib_title.get_text(strip=True)
        print(f"  Found Tibetan title: {title_bo[:50]}...")
    else:
        print(f"  ⚠ No Tibetan title found")
    
    # Try to find English title in heading tags only
    eng_title = (soup.find('h2', class_='eng') or 
                 soup.find('h1', class_='eng') or
                 soup.find('h3', class_='eng'))
    
    if eng_title:
        title_en = eng_title.get_text(strip=True)
        print(f"  Found English title: {title_en}")
    else:
        print(f"  ⚠ No English title found")
    
    # Extract verses
    verses = []
    nobreak_divs = soup.find_all('div', class_='nobreak')
    
    for div in nobreak_divs:
        # Prefer verse classes; gracefully fall back to mantra classes when present
        tib_verse = div.find('p', class_='tib-verse') or div.find('p', class_='tib-mantra')
        pho_verse = div.find('p', class_='pho-verse') or div.find('p', class_='pho-mantra')
        eng_verse = div.find('p', class_='eng-verse') or div.find('p', class_='eng-mantra')
        
        # Accept any available verse fields (bo/en/en-trans)
        verse = {}
        if tib_verse:
            verse['bo'] = tib_verse.get_text(strip=True)
        if eng_verse:
            verse['en'] = eng_verse.get_text(strip=True)
        if pho_verse:
            verse['en-trans'] = pho_verse.get_text(strip=True)
        if verse:
            verses.append(verse)
    
    return title_bo, title_en, verses


def process_folder(folder_path, output_dir):
    """Process a single extracted folder and save to individual JSON file."""
    ops_path = folder_path / "OPS"
    
    if not ops_path.exists():
        print(f"⚠ No OPS folder in {folder_path.name}")
        return False
    
    text_file = ops_path / "text0.html"
    footer_file = ops_path / "footer.html"
    
    if not text_file.exists() or not footer_file.exists():
        print(f"⚠ Missing files in {folder_path.name}")
        return False
    
    try:
        # Extract data
        source_url, copyright_url = extract_footer_data(footer_file)
        title_bo, title_en, verses = extract_text_data(text_file)
        
        # Build JSON structure with new fields
        title = {}
        if title_bo:
            title["bo"] = title_bo
        if title_en:
            title["en"] = title_en
        data = {
            "source": "lotsawahouse",
            "source_url": source_url,
            "copyright": copyright_url,
        }
        if title:
            data["title"] = title
        data["text"] = verses
        
        # Save to individual JSON file, mirroring input subfolders
        rel_path = folder_path.relative_to(Path(INPUT_DIR))
        dest_dir = output_dir / rel_path.parent
        dest_dir.mkdir(parents=True, exist_ok=True)
        output_file = dest_dir / f"{folder_path.name}.json"
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        
        print(f"✓ Processed: {rel_path} → {output_file.relative_to(output_dir)} ({len(verses)} verses)")
        return True
    
    except Exception as e:
        print(f"✗ Error processing {folder_path.name}: {e}")
        return False


def main():
    input_path = Path(INPUT_DIR)
    output_path = Path(OUTPUT_DIR)
    
    if not input_path.exists():
        print(f"Directory '{INPUT_DIR}' not found")
        return
    
    # Create output directory if it doesn't exist
    output_path.mkdir(exist_ok=True)
    print(f"Output directory: {OUTPUT_DIR}")
    print("-" * 50)
    
    # Find all extracted folders recursively by locating OPS directories
    ops_dirs = sorted([p for p in input_path.rglob("OPS") if p.is_dir()])
    folders = [p.parent for p in ops_dirs]
    
    if not folders:
        print(f"No folders found in '{INPUT_DIR}'")
        return
    
    print(f"Found {len(folders)} folder(s)")
    print("-" * 50)
    
    # Process all folders
    success_count = 0
    
    for folder in folders:
        if process_folder(folder, output_path):
            success_count += 1
    
    # Summary
    print("-" * 50)
    print(f"\n✓ Successfully processed {success_count}/{len(folders)} folder(s)")
    print(f"✓ Output saved to: {OUTPUT_DIR}/")


if __name__ == "__main__":
    main()