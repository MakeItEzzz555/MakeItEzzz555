#!/usr/bin/env python3
"""Generate visible, looped SMIL animations for every vendored technology icon.

Static upstream shapes are preserved exactly. Animations have no CSS,
JavaScript, external resources or access to host files.
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

# Motion is geometric rather than opacity-only, so it is visible at 22-34px.
# Starts are negative: movement is active immediately, without idle lead-in.
MOTION_TYPES = ("bob", "sway", "breathe", "tilt")
OVERRIDES = {
    "react": "orbit", "unity": "tilt", "git": "tilt",
    "github": "breathe", "javascript": "breathe",
    "python": "bob", "swift": "sway", "typescript": "breathe",
    "visualstudiocode": "sway", "tailwindcss": "sway",
    "css3": "bob", "html5": "bob", "windows11": "breathe",
}

def tag(local):
    return "{" + NAMESPACE + "}" + local

def icons():
    return sorted(p.stem for p in STATIC_DIR.glob("*.svg") if p.is_file())

def catalog():
    return {name: OVERRIDES.get(name, MOTION_TYPES[index % len(MOTION_TYPES)])
            for index, name in enumerate(icons())}

def generate(name):
    names = catalog()
    if name not in names:
        raise ValueError("Unknown technology icon")
    root = ET.parse(STATIC_DIR / (name + ".svg")).getroot()
    if root.tag != tag("svg") or root.get("fill") != ACCENT:
        raise ValueError("Expected validated mint-green SVG")
    view = [float(x) for x in root.get("viewBox", "0 0 24 24").split()]
    if len(view) != 4:
        raise ValueError("Expected four SVG viewBox coordinates")
    x, y, w, h = view
    center_x, center_y = x + w/2, y + h/2
    # Keep transform movement within root image bounds, with no severe cropping.
    margin_x, margin_y = w * 0.075, h * 0.075
    out = ET.Element(tag("svg"), dict(root.attrib))
    out.set("viewBox", f"{x-margin_x:g} {y-margin_y:g} {w+2*margin_x:g} {h+2*margin_y:g}")
    out.set("role", "img")
    out.set("aria-label", name)
    for child in root:
        if child.tag == tag("title"):
            out.append(deepcopy(child))
    parent = ET.SubElement(out, tag("g"))
    motion = names[name]
    # 3.1–4.1s cycles (React orbit 11s); different positions prevent lockstep.
    idx = icons().index(name)
    duration = "11s" if motion == "orbit" else f"{3.1 + (idx % 6) * 0.2:.1f}s"
    begin = f"-{0.4 + (idx % 5) * 0.25:.2f}s"
    if motion in ("breathe",):
        parent.set("transform", f"translate({center_x:g} {center_y:g})")
        scaling = ET.SubElement(parent, tag("g"))
        ET.SubElement(scaling, tag("animateTransform"), {
            "attributeName": "transform", "type": "scale",
            "values": "1;1.14;1;0.90;1",
            "keyTimes": "0;0.25;0.5;0.75;1",
            "dur": duration, "begin": begin, "repeatCount": "indefinite",
        })
        geometry = ET.SubElement(scaling, tag("g"), {
            "transform": f"translate({-center_x:g} {-center_y:g})"
        })
    else:
        # Scale travel to the original geometry size (e.g. Devicon uses 128x128).
        dy, dx, lead = h * 1.7 / 24, w * 1.55 / 24, w * 0.6 / 24
        variants = {
            "bob": ("translate", f"0 0;0 {-dy:g};0 0;0 {dy:g};0 0"),
            "sway": ("translate", f"{-dx:g} 0;{lead:g} 0;{dx:g} 0;0 0;{-dx:g} 0"),
            "tilt": ("rotate",
                     f"0 {center_x:g} {center_y:g};6 {center_x:g} {center_y:g};"
                     f"0 {center_x:g} {center_y:g};-6 {center_x:g} {center_y:g};"
                     f"0 {center_x:g} {center_y:g}"),
            "orbit": ("rotate", f"0 {center_x:g} {center_y:g};360 {center_x:g} {center_y:g}"),
        }
        type_, values = variants[motion]
        ET.SubElement(parent, tag("animateTransform"), {
            "attributeName": "transform", "type": type_,
            "values": values, "dur": duration, "begin": begin,
            "repeatCount": "indefinite"
        })
        geometry = parent
    for child in root:
        if child.tag != tag("title"):
            geometry.append(deepcopy(child))
    return ET.tostring(out, encoding="utf-8", xml_declaration=False) + b"\n"

def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--check", action="store_true", help="Validate committed assets against generator")
    args = p.parse_args()
    available = catalog()
    if not args.check:
        OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    errors = []
    for name in available:
        content = generate(name)
        file = OUTPUT_DIR / (name + ".svg")
        if args.check:
            if not file.is_file() or file.read_bytes() != content:
                errors.append(str(file.relative_to(ROOT)) + ": not generated/mismatched")
        else:
            file.write_bytes(content)
        parsed = ET.fromstring(content)
        animations = [child for child in parsed.iter()
                      if child.tag == tag("animateTransform")]
        if len(animations) != 1 or animations[0].get("repeatCount") != "indefinite":
            errors.append(name + ": missing motion")
        if len(content) > 20000:
            errors.append(name + ": too large")
    surplus = set(p.stem for p in OUTPUT_DIR.glob("*.svg")) - set(available)
    if surplus:
        errors.append("Orphan generated icons: " + ", ".join(sorted(surplus)))
    if errors:
        for e in errors:
            print("ERROR " + e, file=sys.stderr)
        return 1
    print(f"{'Validated' if args.check else 'Generated'} {len(available)} mint-green animated technology SVGs")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
