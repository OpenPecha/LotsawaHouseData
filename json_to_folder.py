from pathlib import Path
import json

INPUT_DIR = "wb_prayers/json"
OUTPUT_DIR = Path("wb_prayers/folders")

def get_bo_text(data, title):
    bo_text = f"{title}\n"
    for verse in data['text']:
        if verse.get('bo', ""):
            bo_text += verse['bo'] + "\n"   
    return bo_text

def get_en_text(data, title):
    en_text = f"{title}\n"
    for verse in data['text']:
        if verse.get('en', ""):
            en_text += verse['en'] + "\n"
    return en_text

def create_folder(output_dir, bo_title, bo_text, en_text):
    folder_path = output_dir / bo_title
    folder_path.mkdir(parents=True, exist_ok=True)
    with open(folder_path / "bo.txt", "w") as f:
        f.write(bo_text)
    with open(folder_path / "en.txt", "w") as f:
        f.write(en_text)

def json_to_folder(json_file, output_dir):
    with open(json_file, "r") as f:
        data = json.load(f)
    bo_title = data['title']['bo']
    en_title = data['title']['en']
    bo_text = get_bo_text(data, bo_title)
    en_text = get_en_text(data, en_title)
    
    create_folder(output_dir, bo_title, bo_text, en_text)

def main():
    for json_file in Path(INPUT_DIR).glob("*.json"):
        json_to_folder(json_file, OUTPUT_DIR)

if __name__ == "__main__":
    main()