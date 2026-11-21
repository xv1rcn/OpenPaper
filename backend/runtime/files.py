"""Allowlisted legacy assets and library files, never arbitrary workspace files."""
from pathlib import Path
from urllib.parse import unquote, urlsplit


def public_file(paths, url):
    relative = unquote(urlsplit(url).path).lstrip("/") or "index.html"
    if relative in ("app", "app/"):
        relative = "app/index.html"
    if "\x00" in relative or "\\" in relative:
        return None
    parts = relative.split("/")
    if any(p in ("", ".", "..") for p in parts):
        return None
    suffix = Path(relative).suffix.lower()
    if parts[0] == "app":
        # Only compiled frontend assets are public; never expose source or maps.
        base = (Path(paths.resource_root) / "frontend" / "dist").resolve()
        app_parts = parts[1:] or ["index.html"]
        allowed = app_parts == ["index.html"] or (
            len(app_parts) == 2 and app_parts[0] == "assets"
            and not app_parts[1].startswith(".")
            and suffix in (".js", ".css", ".svg", ".woff", ".woff2")
        )
        target = base.joinpath(*app_parts).resolve()
    elif parts[0] == "papers":
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
        allowed = relative in ("favicon.svg",)
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
