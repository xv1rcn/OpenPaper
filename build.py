import os

from backend.library.scanner import scan_library, infer_venue_and_year
from backend.utils import configure_stdio

PDF_DIR = "papers"
METADATA_FILE = os.path.join(PDF_DIR, "metadata.json")
QUICK_READING_CACHE_DIR = os.path.join(PDF_DIR, ".quick_reading_cache")
OUTPUT_HTML = "index.html"
TEMPLATE_HTML = "template.html"

def main() -> None:
    """Legacy UI build command. The server calls scan_library directly."""
    configure_stdio()
    metadata = scan_library(
        os.path.dirname(os.path.abspath(PDF_DIR)), pdf_dir=PDF_DIR,
        metadata_file=METADATA_FILE, cache_dir=QUICK_READING_CACHE_DIR,
    )

    if not os.path.exists(TEMPLATE_HTML):
        raise FileNotFoundError(f"{TEMPLATE_HTML} not found")

    with open(TEMPLATE_HTML, "r", encoding="utf-8") as file_obj:
        html = file_obj.read()

    if os.path.exists(OUTPUT_HTML):
        with open(OUTPUT_HTML, "r", encoding="utf-8") as file_obj:
            if file_obj.read() == html:
                print(f"refreshed metadata for {len(metadata)} papers; {OUTPUT_HTML} unchanged")
                return

    with open(OUTPUT_HTML, "w", encoding="utf-8") as file_obj:
        file_obj.write(html)

    print(f"refreshed metadata for {len(metadata)} papers and generated stable {OUTPUT_HTML}")


if __name__ == "__main__":
    main()
