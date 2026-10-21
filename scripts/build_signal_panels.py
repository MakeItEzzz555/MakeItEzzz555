#!/usr/bin/env python3
"""Generate the Signal Hoist profile panels (day + night SVG pairs).

Flags follow the International Code of Signals. Type is Archivo (OFL),
subset and embedded so GitHub's image proxy renders it without web fonts.
Run with --check to verify committed files match the generator.
"""
import argparse
import base64
import html
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "assets" / "signal"
W = 1664

THEMES = {
    "day": {"ground": "#F2EFE8", "ink": "#14181F", "muted": "#555B66", "rule": "#CFC8B8", "edge": "#14181F",
            "cells": ("#E2DCCF", "#B4BEDA", "#6D82BF", "#1F3B8C")},
    "night": {"ground": "#0D1630", "ink": "#EEF0F4", "muted": "#A5ADC2", "rule": "#2A3557", "edge": "#EEF0F4",
              "cells": ("#18233F", "#2F4378", "#5873BE", "#9DB2EC")},
}
BLUE, RED, YELLOW, BLACK, WHITE = "#1F3B8C", "#C8102E", "#F2C230", "#14181F", "#FFFFFF"

# Each flag is drawn on a 90 x 60 field: list of (svg element, fill).
FLAGS = {
    "A": [("M0 0H45V60H0Z", WHITE), ("M45 0H90L67.5 30L90 60H45Z", BLUE)],
    "B": [("M0 0H90L67.5 30L90 60H0Z", RED)],
    "C": [("M0 0H90V60H0Z", BLUE), ("M0 12H90V48H0Z", WHITE), ("M0 24H90V36H0Z", RED)],
    "D": [("M0 0H90V60H0Z", YELLOW), ("M0 15H90V45H0Z", BLUE)],
    "E": [("M0 0H90V30H0Z", BLUE), ("M0 30H90V60H0Z", RED)],
    "G": [("M0 0H90V60H0Z", BLUE)] + [(f"M{i * 15} 0h15V60h-15Z", YELLOW) for i in (0, 2, 4)],
    "I": [("M0 0H90V60H0Z", YELLOW), ("circle:45,30,15", BLACK)],
    "L": [("M0 0H90V60H0Z", YELLOW), ("M45 0H90V30H45ZM0 30H45V60H0Z", BLACK)],
    "N": [("M0 0H90V60H0Z", WHITE)] + [(f"M{c * 22.5} {r * 15}h22.5v15h-22.5Z", BLUE)
                                        for r in range(4) for c in range(4) if (r + c) % 2 == 0],
    "O": [("M0 0H90V60H0Z", YELLOW), ("M0 0H90V60Z", RED)],
    "P": [("M0 0H90V60H0Z", BLUE), ("M30 20H60V40H30Z", WHITE)],
    "R": [("M0 0H90V60H0Z", RED), ("M37.5 0H52.5V60H37.5ZM0 22.5H90V37.5H0Z", YELLOW)],
    "S": [("M0 0H90V60H0Z", WHITE), ("M30 20H60V40H30Z", BLUE)],
    "T": [("M0 0H30V60H0Z", RED), ("M30 0H60V60H30Z", WHITE), ("M60 0H90V60H60Z", BLUE)],
    "U": [("M0 0H90V60H0Z", WHITE), ("M0 0H45V30H0ZM45 30H90V60H45Z", RED)],
    "V": [("M0 0H90V60H0Z", WHITE), ("M0 0L90 60M90 0L0 60", "stroke:" + RED)],
    "W": [("M0 0H90V60H0Z", BLUE), ("M12 12H78V48H12Z", WHITE), ("M30 22H60V38H30Z", RED)],
    "X": [("M0 0H90V60H0Z", WHITE), ("M37.5 0H52.5V60H37.5ZM0 22.5H90V37.5H0Z", BLUE)],
}
OUTLINE = {"A": "M0 0H90L67.5 30L90 60H0Z", "B": "M0 0H90L67.5 30L90 60H0Z"}


def font_face():
    faces = []
    for name in ("display", "text"):
        data = (OUT / "fonts" / f"archivo-{name}.woff2").read_bytes()
        faces.append(f"@font-face{{font-family:A{name};src:url(data:font/woff2;base64,"
                     f"{base64.b64encode(data).decode()}) format('woff2')}}")
    return "".join(faces)


def flag(letter, x, y, w, t, cls=""):
    """One flag at (x, y), w wide; height is w * 2/3."""
    s = w / 90
    parts = []
    for shape, fill in FLAGS[letter]:
        if shape.startswith("circle:"):
            cx, cy, r = shape[7:].split(",")
            parts.append(f'<circle cx="{cx}" cy="{cy}" r="{r}" fill="{fill}"/>')
        elif fill.startswith("stroke:"):
            parts.append(f'<path d="{shape}" stroke="{fill[7:]}" stroke-width="13"/>')
        else:
            parts.append(f'<path d="{shape}" fill="{fill}"/>')
    edge = OUTLINE.get(letter, "M0 0H90V60H0Z")
    parts.append(f'<path d="{edge}" fill="none" stroke="{t["edge"]}" stroke-width="{1.6 / s:.2f}"/>')
    klass = f' class="{cls}"' if cls else ""
    # CSS animation replaces a transform attribute, so motion lives on an inner group.
    return (f'<g transform="translate({x} {y}) scale({s:.4f})"><g{klass}>'
            f'<clipPath id="c{letter}{x}{y}"><path d="{edge}"/></clipPath>'
            f'<g clip-path="url(#c{letter}{x}{y})">{"".join(parts[:-1])}</g>{parts[-1]}</g></g>')


def text(x, y, value, size, t, face="text", fill=None, anchor="start", tracking=0):
    track = f' letter-spacing="{tracking}"' if tracking else ""
    return (f'<text x="{x}" y="{y}" font-family="A{face}" font-size="{size}" fill="{fill or t["ink"]}"'
            f' text-anchor="{anchor}"{track}>{html.escape(value)}</text>')


def svg(height, t, body, title, flutter=False, width=W):
    motion = ""
    if flutter:
        # shortcut: per-flag skew flutter; transform-box keeps the hoist edge fixed.
        motion = (".fl{transform-box:fill-box;transform-origin:0 50%;animation:fl 3.2s ease-in-out infinite alternate}"
                  ".fl:nth-of-type(2n){animation-delay:-1.1s}.fl:nth-of-type(3n){animation-delay:-2.3s}"
                  "@keyframes fl{from{transform:skewY(-2.2deg) scaleX(.985)}to{transform:skewY(2.2deg) scaleX(1)}}"
                  "@media (prefers-reduced-motion:reduce){.fl{animation:none}}")
    return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}"'
            f' role="img" aria-label="{html.escape(title)}"><title>{html.escape(title)}</title>'
            f'<style>{font_face()}{motion}</style>'
            f'<rect width="{width}" height="{height}" fill="{t["ground"]}"/>{body}</svg>\n')


def hero(t):
    rope = f'<path d="M150 0V720" stroke="{t["ink"]}" stroke-width="3"/>'
    flags = "".join(flag(c, 152, 40 + i * 88, 114, t, "fl") for i, c in enumerate("NICOLAS"))
    body = (rope + flags
            + text(340, 250, "Nicolas", 184, t, "display", tracking=-4)
            + text(340, 434, "Savvides", 184, t, "display", tracking=-4)
            + flag("V", 344, 540, 132, t)
            + text(508, 612, "I require assistance.", 56, t, "display", tracking=-1.5))
    return svg(720, t, body, "Nicolas Savvides, product engineer in Cyprus. His name flown as signal flags.", True)


def heading(label, t):
    return svg(200, t, text(96, 150, label, 104, t, "display", tracking=-3), label)


def plate(letters, name, t, width=W, height=200, size=96):
    fw, left = size * 1.12, 96 if width == W else 40
    flags = "".join(flag(c, left + i * (fw + 10), (height - fw * 2 / 3) / 2, fw, t) for i, c in enumerate(letters))
    x = left + len(letters) * (fw + 10) + 30
    body = flags + text(x, height / 2 + size * 0.36, name, size, t, "display", tracking=-2)
    return svg(height, t, body, f"{name}, flags {' '.join(letters)}", width=width)


def frame(letters, line, t):
    """Flag-only 16:10 frame for projects without a public screenshot."""
    fw, gap = 300, 24
    start = 600 - (len(letters) * fw + (len(letters) - 1) * gap) / 2
    flags = "".join(flag(c, start + i * (fw + gap), 170, fw, t) for i, c in enumerate(letters))
    return svg(750, t, flags + text(600, 560, line, 40, t, fill=t["muted"], anchor="middle"), line, width=1200)


def link(label, t, letter=None):
    w, h = 640, 128
    body = f'<rect x="2" y="2" width="{w - 4}" height="{h - 4}" fill="none" stroke="{t["ink"]}" stroke-width="3"/>'
    x = 44
    if letter:
        body += flag(letter, 40, 34, 90, t)
        x = 160
    body += text(x, 80, label + " →", 44, t, "display", tracking=-1)
    return svg(h, t, body, label, width=w)


def studio(t):
    rows = [("Web products", "Sites and platforms for businesses"),
            ("Native macOS", "Swift, SwiftUI and AppKit apps"),
            ("AI-agent tooling", "Skills, plugins, live widgets"),
            ("Games", "Unity, Three.js, creative coding")]
    body = text(96, 130, "Exodia Studios", 104, t, "display", tracking=-3)
    body += text(100, 196, "Independent studio. Design and engineering under one roof.", 36, t, fill=t["muted"])
    for i, (name, line) in enumerate(rows):
        y = 280 + i * 120
        body += f'<path d="M96 {y - 52}H{W - 96}" stroke="{t["rule"]}" stroke-width="2"/>'
        body += text(96, y + 10, name, 48, t, "display", tracking=-1)
        body += text(W - 96, y + 8, line, 32, t, fill=t["muted"], anchor="end")
    return svg(760, t, body, "Exodia Studios: web products, native macOS, AI-agent tooling, games.")


def sponsor(t):
    perks = ["Every sponsor: your name in this README.",
             "Companies: your logo in the TuckBit and widget-kit READMEs.",
             "Sponsors’ issues are looked at first."]
    body = flag("V", 96, 70, 240, t)
    body += text(400, 150, "I require assistance.", 88, t, "display", tracking=-3)
    body += text(404, 214, "Flag V. Sponsorship keeps the tools free, maintained and fast.", 34, t, fill=t["muted"])
    for i, p in enumerate(perks):
        y = 330 + i * 76
        body += f'<path d="M96 {y - 46}H{W - 96}" stroke="{t["rule"]}" stroke-width="2"/>'
        body += text(96, y, p, 40, t)
    return svg(560, t, body, "Sponsor: name in README, company logos in project READMEs, priority issues.")


def close(t):
    body = f'<path d="M0 96H{W}" stroke="{t["ink"]}" stroke-width="3"/>'
    body += flag("U", 96, 98, 150, t, "fl") + flag("W", 262, 98, 150, t, "fl")
    body += text(470, 168, "Thank you for your cooperation.", 52, t, "display", tracking=-1.5)
    body += text(470, 236, "I wish you a pleasant voyage.", 52, t, "display", tracking=-1.5)
    return svg(320, t, body, "Signal UW: thank you for your cooperation, I wish you a pleasant voyage.", True)


SECOND_TIER = {"predictx": ("PX", "Prediction market · TypeScript · tRPC · Stripe"),
               "dynamicisland": ("DI", "Native macOS notch workspace · in development")}
PLATES = {"tuckbit": ("TB", "TuckBit"), "claude-kit": ("CW", "Claude Widget Kit"),
          "codex-kit": ("XW", "Codex Widget Kit")}
SMALL = {"signai": ("SA", "SignAI"), "dungeon": ("DE", "Dungeon Escape"), "predictx": ("PX", "PredictX"),
         "airptt": ("AB", "AirPTTBridge"), "dynamicisland": ("DI", "DynamicIsland"),
         "grapharium": ("GR", "Grapharium")}


def outputs():
    files = {}
    for mode, t in THEMES.items():
        d = f"{mode}/"
        files[d + "hero.svg"] = hero(t)
        files[d + "close.svg"] = close(t)
        files[d + "studio.svg"] = studio(t)
        files[d + "sponsor.svg"] = sponsor(t)
        files[d + "work.svg"] = heading("Work", t)
        for key, (letters, name) in PLATES.items():
            files[d + f"plate-{key}.svg"] = plate(letters, name, t)
        for key, (letters, name) in SMALL.items():
            files[d + f"tag-{key}.svg"] = plate(letters, name, t, width=800, height=140, size=50)
        for key, (letters, line) in SECOND_TIER.items():
            files[d + f"frame-{key}.svg"] = frame(letters, line, t)
        files[d + "link-sponsor.svg"] = link("Sponsor", t, "V")
        files[d + "link-follow.svg"] = link("Follow", t)
        files[d + "link-studio.svg"] = link("exodiastudios.com", t)
    return files


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    stale = []
    for rel, content in outputs().items():
        path = OUT / rel
        if args.check:
            if not path.is_file() or path.read_text(encoding="utf-8") != content:
                stale.append(rel)
        else:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content, encoding="utf-8")
    if stale:
        print("Stale signal panels: " + ", ".join(stale), file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
