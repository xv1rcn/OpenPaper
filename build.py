import os

from backend.library.scanner import scan_library, infer_venue_and_year
from backend.utils import configure_stdio

PDF_DIR = "papers"
METADATA_FILE = os.path.join(PDF_DIR, "metadata.json")
QUICK_READING_CACHE_DIR = os.path.join(PDF_DIR, ".quick_reading_cache")

def main() -> None:
    """Compatibility command: refresh library metadata, never generate a UI."""
    configure_stdio()
    metadata = scan_library(
        os.path.dirname(os.path.abspath(PDF_DIR)), pdf_dir=PDF_DIR,
        metadata_file=METADATA_FILE, cache_dir=QUICK_READING_CACHE_DIR,
    )
    print(f"refreshed metadata for {len(metadata)} papers; build the UI with frontend/npm run build")

if __name__ == "__main__":
    main()
