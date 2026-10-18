#!/usr/bin/env python3
"""Build small SMIL-animated, CSS-free derivatives of vendored technology SVGs.

Animation is opt-in per icon. Static upstream assets remain unchanged, and
GitHub README <picture> elements provide still images for reduced motion.
No network calls, JavaScript, external SVG references or third-party packages.
"""
import argparse
from copy import deepcopy
from pathlib import Path
import sys
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
STATIC_DIR = ROOT / "assets" / "icons"
OUTPUT_DIR = STATIC_DIR / "animated"
NAMESPACE = "http://www.w3.org/2000/svg"
ET.register_namespace("", NAMESPACE)
ACCENT = "#7DFFB4"

# name: (motion, duration, stagger)
MOTIONS = {
    "react": ("orbit", "26s", "0.01s"),
    "python": ("rise", "6.8s", "1.2s"),
    "swift": ("rise", "7.6s", "2.4s"),
    "tailwindcss": ("drift", "7.2s", "0.6s"),
    "git": ("pulse", "7.8s", "2.3s"),
    "unity": ("tilt", "9.4s", "3.6s"),
    "javascript": ("pulse", "6.7s", "4.5s"),
    "visualstudiocode": ("pulse", "8.6s", "1.6s"),
}

def tag(local):
    return "{" + NAMESPACE + "}" + local

def generate(name):
    if name not in MOTIONS:
        raise ValueError("Unknown icon")
    path = STATIC_DIR / (name + ".svg")
    root = ET.parse(path).getroot()
    if root.tag != tag("svg") or root.get("fill") != ACCENT:
        raise ValueError("Expected validated green SVG source")
    if root.find(tag("path")) is None:
        raise ValueError("Missing logo geometry")

    motion, duration, begin = MOTIONS[name]
    out = ET.Element(tag("svg"), dict(root.attrib))
    out.set("role", "img")
    out.set("aria-label", name.replace("visualstudiocode", "Visual Studio Code"))
    if motion in ("rise", "drift", "tilt"):
        # Small amount of padding for unclipped motion; core geometry unchanged.
        out.set("viewBox", "-0.7 -0.7 25.4 25.4")
    for child in root:
        if child.tag == tag("title"):
            out.append(deepcopy(child))
    group = ET.SubElement(out, tag("g"))
    for child in root:
        if child.tag != tag("title"):
            group.append(deepcopy(child))

    if motion == "pulse":
        ET.SubElement(group, tag("animate"), {
            "attributeName": "opacity",
            "values": "1;0.78;1",
            "keyTimes": "0;0.5;1",
            "dur": duration, "begin": begin,
            "repeatCount": "indefinite"
        })
    else:
        options = {
            "orbit": ("rotate", "0 12 12;360 12 12"),
            "rise": ("translate", "0 0;0 -0.6;0 0"),
            "drift": ("translate", "0 0;0.5 0;0 0"),
            "tilt": ("rotate", "0 12 12;3 12 12;0 12 12;-3 12 12;0 12 12"),
        }
        type_, values = options[motion]
        ET.SubElement(group, tag("animateTransform"), {
            "attributeName": "transform",
            "type": type_, "values": values,
            "dur": duration, "begin": begin,
            "repeatCount": "indefinite",
        })
    return ET.tostring(out, encoding="utf-8", xml_declaration=False) + b"\n"

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="Verify generated SVGs match committed files")
    args = parser.parse_args()
    if not args.check:
        OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    errors = []
    for name in MOTIONS:
        expected = generate(name)
        target = OUTPUT_DIR / (name + ".svg")
        if args.check:
            if not target.is_file() or target.read_bytes() != expected:
                errors.append(str(target.relative_to(ROOT)))
        else:
            target.write_bytes(expected)
        if len(expected) > 20000:
            errors.append("Oversize generated SVG: " + name)
        parsed = ET.fromstring(expected)
        if parsed.find(".//" + tag("animate")) is None and parsed.find(".//" + tag("animateTransform")) is None:
            errors.append("Motion missing: " + name)
    if args.check and errors:
        for error in errors:
            print("ERROR: " + error, file=sys.stderr)
        return 1
    print(f"{'Validated' if args.check else 'Generated'} {len(MOTIONS)} green SMIL icon animations")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
