#!/usr/bin/env python3
"""Validate profile README images and local SVGs before publication.

Offline mode (default) checks local references and XML safety with no network.
Use --check-remote for a best-effort one-time audit of external badges/images.
"""
import argparse
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urlsplit, unquote
from urllib.request import Request, urlopen
import sys
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
SVG_TAGS_DENIED = {"script", "foreignObject", "iframe", "image"}
ATTRS_URL = {"href", "src"}

class Images(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.images = []
    def handle_starttag(self, tag, attrs):
        if tag.lower() == "img":
            attributes = dict(attrs)
            self.images.append((attributes.get("src"), attributes.get("alt")))

def check_svg(path):
    tree = ET.parse(path)
    root = tree.getroot()
    if root.tag.rsplit("}", 1)[-1] != "svg":
        raise ValueError("Not an SVG root")
    for node in tree.iter():
        if node.tag.rsplit("}", 1)[-1] in SVG_TAGS_DENIED:
            raise ValueError("Disallowed SVG content")
        for name, value in node.attrib.items():
            attribute = name.rsplit("}", 1)[-1].lower()
            if attribute.startswith("on"):
                raise ValueError("Scriptable SVG attribute")
            if attribute in ATTRS_URL and (value.startswith(("http:", "https:", "javascript:", "data:", "//"))):
                raise ValueError("External or executable SVG reference")
    # Github image context requires standalone SVGs, not executable HTML.
    return True

def validate(root, check_remote=False):
    readme = (root / "README.md").read_text(encoding="utf-8")
    parser = Images()
    parser.feed(readme)
    errors = []
    local = []
    remote = []
    for src, alt in parser.images:
        if not src:
            errors.append("Image has no src")
            continue
        address = urlsplit(src)
        if address.scheme in ("http", "https"):
            remote.append(src)
            continue
        if address.scheme or address.netloc:
            errors.append("Unexpected image scheme")
            continue
        relative = unquote(address.path)
        if not relative or relative.startswith("/") or ".." in Path(relative).parts:
            errors.append(f"Unsafe image path: {relative}")
            continue
        path = root / relative
        if not path.is_file() or path.is_symlink():
            errors.append(f"Missing image: {relative}")
            continue
        local.append(path)
        if not alt:
            errors.append(f"Missing image accessibility alt text: {relative}")
    svg_files = sorted(set(root.glob("assets/**/*.svg")))
    for path in svg_files:
        try:
            check_svg(path)
        except (ET.ParseError, ValueError) as exc:
            errors.append(f"Invalid SVG: {path.relative_to(root)} ({exc})")
    if "cdn.simpleicons.org" in readme:
        errors.append("Unvendored Simple Icons CDN image detected")
    if check_remote:
        for link in sorted(set(remote)):
            try:
                request = Request(link, headers={"User-Agent": "TuckBit-Profile-README-Image-Check/1.0"})
                with urlopen(request, timeout=16) as response:
                    ctype = response.headers.get("Content-Type", "")
                    first = response.read(512)
                    if response.status != 200 or not ctype.startswith("image/") or not first:
                        errors.append("Remote URL did not return an image: " + urlsplit(link).netloc)
            except Exception as exc:
                errors.append("Remote image unreachable: " + urlsplit(link).netloc + " (" + type(exc).__name__ + ")")
    return len(parser.images), len(local), len(remote), len(svg_files), errors

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check-remote", action="store_true", help="Check third-party image URLs (network required)")
    args = parser.parse_args()
    try:
        count, local, remote, svgs, issues = validate(ROOT, args.check_remote)
    except (OSError, UnicodeError) as exc:
        print("Profile image validation failed: " + type(exc).__name__, file=sys.stderr)
        return 2
    print(f"README images: {count}; local: {local}; external: {remote}; validatable SVG files: {svgs}")
    for issue in issues:
        print("FAIL: " + issue, file=sys.stderr)
    return 1 if issues else 0

if __name__ == "__main__":
    raise SystemExit(main())
