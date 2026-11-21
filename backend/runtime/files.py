"""Allowlisted legacy assets and library files, never arbitrary workspace files."""
from pathlib import Path
from urllib.parse import unquote, urlsplit


def public_file(paths, url):
    relative = unquote(urlsplit(url).path).lstrip("/") or "index.html"
    if "\x00" in relative or "\\" in relative:
        return None
    parts = relative.split("/")
    if any(p in ("", ".", "..") for p in parts):
        return None
    suffix = Path(relative).suffix.lower()
    if parts[0] == "papers":
        allowed = relative in ("papers/metadata.json", "papers/stats.data.json")
        if len(parts) > 2 and parts[1] == ".quick_reading_cache":
            allowed = (
                not any(p.startswith(".") for p in parts[2:])
                and (suffix in (".png", ".jpg", ".jpeg", ".webp")
                     or parts[-1] in ("index.json", "speed_read.json"))
            )
        elif suffix == ".pdf" and not any(p.startswith(".") for p in parts[1:]):
            allowed = True
        base = Path(paths.papers).resolve()
        target = base.joinpath(*parts[1:]).resolve()
    else:
        allowed = relative in ("index.html", "quick-reading.html", "stats.html", "favicon.svg")
        if parts[0] == "assets" and len(parts) > 1:
            allowed = not any(p.startswith(".") for p in parts) and suffix in (
                ".js", ".css", ".png", ".jpg", ".svg", ".woff", ".woff2",
            )
            base = (Path(paths.resource_root) / "assets").resolve()
            target = base.joinpath(*parts[1:]).resolve()
        else:
            base = Path(paths.resource_root).resolve()
            target = base.joinpath(*parts).resolve()
    if not allowed:
        return None
    try:
        target.relative_to(base)
    except ValueError:
        return None
    return str(target)
