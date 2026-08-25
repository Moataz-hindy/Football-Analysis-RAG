import os
import json
import glob
from bs4 import BeautifulSoup

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(os.path.dirname(SCRIPT_DIR))

RAW_DIR = os.path.join(PROJECT_ROOT, "data", "raw")
CLEAN_DIR = os.path.join(PROJECT_ROOT, "data", "clean")

# Class/id keywords that mark non-content widgets (live scores, odds tickers,
# cookie banners, etc.) which the basic tag removal below doesn't catch.
NOISE_KEYWORDS = ["ticker", "livescore", "live-score", "live-band", "odds", "cookie", "banner", "widget"]


def repair_mojibake(raw_html):

    if "â€" in raw_html or "Â" in raw_html or "â\x80" in raw_html:
        try:
            return raw_html.encode("latin1").decode("utf-8")
        except (UnicodeEncodeError, UnicodeDecodeError):
            return raw_html
    return raw_html


def clean_html(raw_html):
    if not raw_html:
        return ""

    raw_html = repair_mojibake(raw_html)

    soup = BeautifulSoup(raw_html, "html.parser")

    # Remove script, style, navigation, footer, and header elements
    for element in soup(["script", "style", "nav", "footer", "header", "aside"]):
        element.decompose()

    # Remove leftover widgets (live-score tickers, odds boxes, cookie
    # banners...) identified by class/id keywords, since these aren't
    # real article content and just add noise to the chunks. Collect
    # matches first, then decompose, skipping any element whose parent
    # was already removed (decomposing a still-attached parent leaves
    # its children in a broken state, so re-checking .parent avoids that).
    STRUCTURAL_TAGS = {"html", "body", "head"}  # never nuke the page skeleton

    def matches_noise_keyword(tokens):
        # tokens: the element's raw class names + id (each may itself be
        # hyphenated, e.g. "live-band" or "cookies-no"). For hyphenated
        # keywords (e.g. "live-band") require an exact token match; for
        # single-word keywords (e.g. "cookie") require it to be one of the
        # token's own hyphen/underscore-separated parts. This avoids the
        # plural "cookies-no" on <body> false-matching "cookie".
        for token in tokens:
            parts = token.replace("_", "-").split("-")
            for keyword in NOISE_KEYWORDS:
                if "-" in keyword:
                    if token == keyword:
                        return True
                elif keyword in parts:
                    return True
        return False

    noise_elements = []
    for el in soup.find_all(True):
        if el.name in STRUCTURAL_TAGS:
            continue
        tokens = [t.lower() for t in (el.get("class", []) + [el.get("id", "")]) if t]
        if matches_noise_keyword(tokens):
            noise_elements.append(el)
    for element in noise_elements:
        if element.parent is not None:
            element.decompose()

    # Extract text and collapse multiple spaces/newlines
    text = soup.get_text(separator=" ")
    
    # Basic normalization: split and rejoin to remove extra whitespace
    clean_text = " ".join(text.split())
    return clean_text

def process_files():
    # Ensure the clean directory exists
    os.makedirs(CLEAN_DIR, exist_ok=True)
    
    # Find all JSON files in the raw directory
    file_pattern = os.path.join(RAW_DIR, "*.json")
    files = glob.glob(file_pattern)
    
    if not files:
        print(f"No files found in {RAW_DIR}. Did you run collect.py first?")
        return

    print(f"Found {len(files)} raw files. Starting cleaning process...")
    
    cleaned_count = 0
    for file_path in files:
        filename = os.path.basename(file_path)
        print(f"Cleaning {filename}...")
        
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                doc = json.load(f)
            
            raw_html = doc.get("raw_html", "")

            # 1. Clean the text
            clean_text = clean_html(raw_html)

            # The title was captured separately at collection time and can
            # carry the same encoding bug as raw_html, so repair it too.
            title = repair_mojibake(doc.get("title", ""))
            
            # 2. Check if the document has useful content left
            if len(clean_text) < 100:
                print(f"  -> Skipping {filename}: Not enough content after cleaning.")
                continue
                
            # 3. Create the cleaned document object
            cleaned_doc = {
                "id": doc["id"],
                "url": doc["url"],
                "title": title,
                "collection_date": doc["collection_date"],
                "text": clean_text
                # We drop raw_html to save space in the clean version
            }
            
            # 4. Save to the clean directory
            clean_path = os.path.join(CLEAN_DIR, filename)
            with open(clean_path, "w", encoding="utf-8") as f:
                json.dump(cleaned_doc, f, indent=4)
                
            cleaned_count += 1
            
        except Exception as e:
            print(f"  -> Error processing {filename}: {e}")
            
    print(f"\nFinished cleaning! Successfully processed {cleaned_count} out of {len(files)} files.")
    print(f"Clean documents are saved in: {CLEAN_DIR}")

if __name__ == "__main__":
    process_files()