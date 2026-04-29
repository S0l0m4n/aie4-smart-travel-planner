import httpx
import xml.etree.ElementTree as ET
from pathlib import Path

DESTINATIONS = {
    "Tbilisi", "Bali", "Rome", "Nepal", "Tokyo",
    "Cancún", "Paris", "Marrakech", "Reykjavik",
    "Bangkok", "Cape_Town", "Zurich", "Cartagena",
}

OUTPUT_DIR = Path("data/raw_wikivoyage")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

BASE_URL = "https://en.wikivoyage.org/wiki/Special:Export"

def fetch_and_save(destination: str):
    resp = httpx.get(f"{BASE_URL}/{destination}", timeout=15)
    resp.raise_for_status()

    root = ET.fromstring(resp.text)
    ns = {"mw": "http://www.mediawiki.org/xml/export-0.10/"}
    text_el = root.find(".//mw:text", ns)

    if text_el is None or not text_el.text:
        print(f"  ⚠ No content found for {destination}")
        return

    out_path = OUTPUT_DIR / f"{destination}.txt"
    out_path.write_text(text_el.text, encoding="utf-8")
    print(f"  ✓ {destination} → {out_path} ({len(text_el.text):,} chars)")

if __name__ == "__main__":
    for dest in sorted(DESTINATIONS):
        print(f"Fetching {dest}...")
        try:
            fetch_and_save(dest)
        except httpx.HTTPError as e:
            print(f"  ✗ Failed: {e}")
