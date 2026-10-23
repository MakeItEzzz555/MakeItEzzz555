#!/usr/bin/env python3
"""Generate the Tactical Telemetry profile panels from assets/telemetry/data.json.

Everything is a standalone SVG: embedded font subsets (OFL), SMIL motion,
no scripts, no external references. Run with --check to verify committed files.
"""
import argparse
import base64
import html
import json
import math
import random
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "assets" / "telemetry"
ICONS = ROOT / "assets" / "icons"
W = 1664
GROUND, INK, DIM, RULE, RED = "#0B0B0B", "#EAEAEA", "#8C8C8C", "#2E2E2E", "#E61919"
SVG_NS = "{http://www.w3.org/2000/svg}"

# Brand colours (Simple Icons / vendor guides); black marks use white on the dark ground.
STACK = [("typescript", "TypeScript", "#3178C6"), ("javascript", "JavaScript", "#F7DF1E"),
         ("python", "Python", "#3776AB"), ("csharp", "C#", "#9B4F96"), ("openjdk", "Java", "#FFFFFF"),
         ("cplusplus", "C++", "#00599C"), ("c", "C", "#A8B9CC"), ("php", "PHP", "#777BB4"),
         ("swift", "Swift", "#F05138"), ("gnubash", "Bash", "#4EAA25"), ("html5", "HTML5", "#E34F26"),
         ("css3", "CSS3", "#1572B6"), ("mysql", "MySQL", "#4479A1"), ("react", "React", "#61DAFB"),
         ("nextdotjs", "Next.js", "#FFFFFF"), ("nodedotjs", "Node.js", "#5FA04E"), ("vite", "Vite", "#646CFF"),
         ("tailwindcss", "Tailwind CSS", "#06B6D4"), ("flask", "Flask", "#FFFFFF"), ("dotnet", ".NET", "#512BD4"),
         ("unity", "Unity", "#FFFFFF"), ("threedotjs", "Three.js", "#FFFFFF"), ("arduino", "Arduino", "#00878F"),
         ("git", "Git", "#F05032"), ("github", "GitHub", "#FFFFFF"), ("visualstudiocode", "VS Code", "#007ACC"),
         ("onnx", "ONNX", "#005CED"), ("tensorflow", "TensorFlow", "#FF6F00")]

LOOP = 70.0        # seconds: one globe revolution and one full ripple cycle
STEP = 0.5         # sampling interval for motion paths
RIPPLES = 10       # 7 s each: 3 hops x 1 s + fade + rest
TILT = math.radians(18)


def fonts():
    css = []
    for name in ("heavy", "mono", "monob"):
        data = base64.b64encode((OUT / "fonts" / f"{name}.woff2").read_bytes()).decode()
        css.append(f"@font-face{{font-family:T{name};src:url(data:font/woff2;base64,{data}) format('woff2')}}")
    return "".join(css)


def t(x, y, value, size, face="mono", fill=INK, anchor="start", track=0, extra=""):
    ls = f' letter-spacing="{track}"' if track else ""
    return (f'<text x="{x}" y="{y}" font-family="T{face}" font-size="{size}" fill="{fill}"'
            f' text-anchor="{anchor}"{ls}{extra}>{html.escape(value)}</text>')


def rule(x1, y1, x2, y2, w=2, color=RULE):
    return f'<path d="M{x1} {y1}L{x2} {y2}" stroke="{color}" stroke-width="{w}"/>'


def cross(x, y, color=DIM):
    return f'<path d="M{x - 9} {y}h18M{x} {y - 9}v18" stroke="{color}" stroke-width="2"/>'


def svg(width, height, body, title, style=""):
    reduce = "@media (prefers-reduced-motion:reduce){*{animation:none!important}}"
    return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" '
            f'viewBox="0 0 {width} {height}" role="img" aria-label="{html.escape(title)}">'
            f'<title>{html.escape(title)}</title><style>{fonts()}{style}{reduce}</style>'
            f'<rect width="{width}" height="{height}" fill="{GROUND}"/>{body}</svg>\n')


def star(x, y, size, color=INK):
    """Five-point star, drawn (not a text glyph); (x, y) is the bounding box's bottom-left."""
    r, cx, cy = size / 2, x + size / 2, y - size / 2
    pts = []
    for i in range(10):
        a = math.pi / 2 + i * math.pi / 5
        rr = r if i % 2 == 0 else r * 0.42
        pts.append(f"{cx + rr * math.cos(a):.1f},{cy - rr * math.sin(a):.1f}")
    return f'<polygon points="{" ".join(pts)}" fill="{color}"/>'


# ---------- globe ----------

def icon_symbol(slug, color):
    root = ET.parse(ICONS / f"{slug}.svg").getroot()
    inner = []
    for child in root:
        if child.tag == SVG_NS + "title":
            continue
        child.attrib.pop("fill", None)
        inner.append(ET.tostring(child, encoding="unicode").replace("ns0:", "").replace(
            ' xmlns:ns0="http://www.w3.org/2000/svg"', ""))
    return (f'<symbol id="i-{slug}" viewBox="{root.get("viewBox")}"><g fill="{color}">'
            f'{"".join(inner)}</g></symbol>')


def sphere_points(n):
    golden = math.pi * (3 - math.sqrt(5))
    pts = []
    for i in range(n):
        y = 1 - 2 * (i + 0.5) / n
        r = math.sqrt(1 - y * y)
        pts.append((math.cos(golden * i) * r, y, math.sin(golden * i) * r))
    return pts


def project(p, angle):
    x, y, z = p
    x, z = x * math.cos(angle) + z * math.sin(angle), -x * math.sin(angle) + z * math.cos(angle)
    y, z = y * math.cos(TILT) - z * math.sin(TILT), y * math.sin(TILT) + z * math.cos(TILT)
    return x, y, z  # z > 0 faces the viewer


def ripple_schedule(points, seed=555):
    """Seeded 'random' ripple starts; each ripple spreads 3 hops to nearest unvisited nodes."""
    rng = random.Random(seed)
    near = [sorted(range(len(points)), key=lambda j: math.dist(points[i], points[j]))[1:] for i in range(len(points))]
    order = list(range(len(points)))
    rng.shuffle(order)
    edges, glows = [], []
    for k in range(RIPPLES):
        t0 = k * LOOP / RIPPLES
        start = order[k % len(order)]
        visited, frontier = {start}, [start]
        glows.append((start, t0))
        for hop, fan in enumerate((3, 2, 1)):
            nxt = []
            for a in frontier:
                for b in [j for j in near[a] if j not in visited][:fan]:
                    visited.add(b)
                    nxt.append(b)
                    edges.append((a, b, t0 + hop * 1.0))
                    glows.append((b, t0 + hop * 1.0 + 0.6))
            frontier = nxt
    return edges, glows


def fmt(v):
    return f"{v:.1f}".rstrip("0").rstrip(".")


def globe(cx, cy, radius, icon=58):
    points = sphere_points(len(STACK))
    frames = int(LOOP / STEP)
    times = [i * STEP for i in range(frames + 1)]
    proj = [[project(p, 2 * math.pi * tm / LOOP) for tm in times] for p in points]

    def sx(v):
        return cx + v[0] * radius

    def sy(v):
        return cy - v[1] * radius

    parts = [icon_symbol(slug, color) for slug, _, color in STACK]
    body = [f'<defs>{"".join(parts)}</defs>']
    # wireframe: limb, latitude ellipses (static under y-rotation) and moving meridians
    body.append(f'<circle cx="{cx}" cy="{cy}" r="{radius}" fill="none" stroke="#3A3A3A" stroke-width="2"/>')
    for lat in (-60, -30, 0, 30, 60):
        r = radius * math.cos(math.radians(lat))
        y = cy - radius * math.sin(math.radians(lat)) * math.cos(TILT)
        body.append(f'<ellipse cx="{cx}" cy="{fmt(y)}" rx="{fmt(r)}" ry="{fmt(r * math.sin(TILT))}" '
                    f'fill="none" stroke="#262626" stroke-width="1.5"/>')
    meridians, seg = 8, 12
    for m in range(meridians):
        shapes = []
        for f in range(seg + 1):
            ang = 2 * math.pi * (m + f / seg) / meridians
            pts = []
            for s in range(0, 181, 15):
                lat = math.radians(s - 90)
                p = project((math.cos(lat), math.sin(lat), 0), ang)
                pts.append(f"{fmt(sx(p))} {fmt(sy(p))}")
            shapes.append("M" + "L".join(pts))
        body.append(f'<path d="{shapes[0]}" fill="none" stroke="#262626" stroke-width="1.5">'
                    f'<animate attributeName="d" dur="{fmt(LOOP / meridians)}s" repeatCount="indefinite" '
                    f'values="{";".join(shapes)}"/></path>')
    # ripple links: endpoints follow the nodes during their visible window
    edges, glows = ripple_schedule(points)
    for a, b, start in edges:
        end = start + 4.2
        samples = [round(start + i * STEP, 2) for i in range(int((end - start) / STEP) + 1)]
        keys = [0] + [s / LOOP for s in samples] + [1]

        def series(node, axis):
            vals = []
            for s in samples:
                v = proj[node][int(round(s / STEP)) % frames]
                vals.append(fmt(sx(v) if axis == "x" else sy(v)))
            return ";".join([vals[0]] + vals + [vals[-1]])
        key = ";".join(f"{k:.4f}" for k in keys)
        op_keys = ";".join(f"{k / LOOP:.4f}" for k in (0, start, start + 0.6, end - 1, end, LOOP))
        anim = "".join(f'<animate attributeName="{attr}" dur="{LOOP}s" repeatCount="indefinite" '
                       f'keyTimes="{key}" values="{series(n, ax)}"/>'
                       for attr, n, ax in (("x1", a, "x"), ("y1", a, "y"), ("x2", b, "x"), ("y2", b, "y")))
        body.append(f'<line stroke="{RED}" stroke-width="2.5" opacity="0" pathLength="1" stroke-dasharray="1" '
                    f'stroke-dashoffset="1">{anim}'
                    f'<animate attributeName="opacity" dur="{LOOP}s" repeatCount="indefinite" '
                    f'keyTimes="{op_keys}" values="0;0;.85;.85;0;0"/>'
                    f'<animate attributeName="stroke-dashoffset" dur="{LOOP}s" repeatCount="indefinite" '
                    f'keyTimes="{op_keys}" values="1;1;0;0;0;0"/></line>')
    # nodes: back-to-front order is fixed, depth carried by scale and opacity
    for i, (slug, _, color) in enumerate(STACK):
        tr = ";".join(f"{fmt(sx(v))} {fmt(sy(v))}" for v in proj[i])
        sc = ";".join(fmt((0.55 + 0.45 * (v[2] + 1) / 2) * 10) for v in proj[i])
        op = ";".join(f"{0.28 + 0.72 * max(0.0, (v[2] + 1) / 2):.2f}" for v in proj[i])
        aura_keys, aura_vals = ["0"], ["0"]
        for node, at in sorted((g for g in glows if g[0] == i), key=lambda g: g[1]):
            for dt, val in ((0, 0), (0.25, 1), (1.4, 0)):
                aura_keys.append(f"{min(1, (at + dt) / LOOP):.4f}")
                aura_vals.append(str(val))
        aura_keys.append("1")
        aura_vals.append("0")
        half = icon / 2
        body.append(
            f'<g><animateTransform attributeName="transform" type="translate" dur="{LOOP}s" '
            f'repeatCount="indefinite" values="{tr}"/>'
            f'<animate attributeName="opacity" dur="{LOOP}s" repeatCount="indefinite" values="{op}"/>'
            f'<g><animateTransform attributeName="transform" type="scale" dur="{LOOP}s" repeatCount="indefinite" '
            f'values="{";".join(fmt(float(s) / 10) for s in sc.split(";"))}"/>'
            f'<circle r="{half + 14}" fill="none" stroke="{color}" stroke-width="2" opacity="0">'
            f'<animate attributeName="opacity" dur="{LOOP}s" repeatCount="indefinite" '
            f'keyTimes="{";".join(aura_keys)}" values="{";".join(aura_vals)}"/></circle>'
            f'<use href="#i-{slug}" x="{-half}" y="{-half}" width="{icon}" height="{icon}"/></g></g>')
    return "".join(body)


# ---------- panels ----------

ROLES = ["FULL-STACK WEB", "PRODUCT DEVELOPMENT", "ML RESEARCH", "AGENTIC WORKFLOWS", "BASED IN CYPRUS"]


def role_readout(x, y):
    """Cycle the secondary roles in a mono readout, one at a time."""
    period = 3.5 * len(ROLES)
    out = [t(x, y, ">", 28, "monob", RED)]
    for i, role in enumerate(ROLES):
        k0, k1 = i / len(ROLES), (i + 1) / len(ROLES)
        keys = sorted({0, k0, k1, 1})
        vals = ["1" if k0 <= k < k1 else "0" for k in keys]
        out.append(t(x + 36, y, role, 28, "monob", INK, track=2,
                     extra=f' opacity="{1 if i == 0 else 0}"').replace(
            "</text>", f'<animate attributeName="opacity" dur="{period}s" repeatCount="indefinite" '
                       f'calcMode="discrete" keyTimes="{";".join(f"{k:.4f}" for k in keys)}" '
                       f'values="{";".join(vals)}"/></text>'))
    return "".join(out)


def name_block(x, y):
    return (t(x, y, "[ GITHUB / MAKEITEZZZ555 ]", 22, "mono", DIM, track=3)
            + t(x - 6, y + 160, "NICOLAS", 168, "heavy", INK, track=-6)
            + t(x - 6, y + 310, "SAVVIDES", 168, "heavy", INK, track=-6)
            + t(x, y + 390, "FULL-STACK PRODUCT ENGINEER", 46, "heavy", RED, track=-1)
            + role_readout(x, y + 452))


def facts(x, y, width):
    rows = [("BASE", "CYPRUS"), ("STUDIO", "EXODIA STUDIOS"), ("OPEN TO", "SPONSORS / PROJECTS")]
    out = []
    for i, (k, v) in enumerate(rows):
        yy = y + i * 54
        out.append(rule(x, yy - 38, x + width, yy - 38))
        out.append(t(x, yy, k, 22, "mono", DIM, track=3) + t(x + 200, yy, v, 24, "monob", INK, track=2))
    out.append(rule(x, y + 3 * 54 - 38, x + width, y + 3 * 54 - 38))
    return "".join(out)


def hero_right():
    h = 900
    body = [rule(1000, 0, 1000, h, 2, RULE), rule(0, 2, W, 2, 4, INK), rule(0, h - 2, W, h - 2, 4, INK)]
    body.append(name_block(80, 110))
    body.append(facts(80, 700, 860))
    body.append(globe(1332, 420, 270))
    body.append(t(1332, 800, "[ STACK / 28 TECHNOLOGIES ]", 22, "mono", DIM, "middle", track=3))
    body += [cross(1000, 60), cross(1000, h - 60)]
    return svg(W, h, "".join(body), "Nicolas Savvides, full-stack product engineer. Rotating globe of 28 technologies.")


def link(label, accent=False):
    w, h = 640, 120
    color = RED if accent else INK
    body = (f'<rect x="2" y="2" width="{w - 4}" height="{h - 4}" fill="none" stroke="{color}" stroke-width="4"/>'
            + t(40, 74, f"[ {label} ]", 34, "monob", color, track=2) + t(w - 40, 74, ">>>", 34, "monob", color, "end"))
    return svg(w, h, body, label.title())


def heading(label, note):
    body = (rule(0, 2, W, 2, 4, INK) + t(80, 150, label, 120, "heavy", INK, track=-4)
            + t(W - 80, 150, note, 22, "mono", DIM, "end", track=3))
    return svg(W, 200, body, label.title())


def project_sheet(repo, name, line, stack, data, h=300):
    info = data["repos"].get(repo, {})
    spec = [("STACK", stack), ("STARS", str(info.get("stars", "—"))),
            ("LAST PUSH", info.get("pushed", "—")), ("LICENSE", info.get("license") or "—")]
    body = [rule(0, 2, W, 2, 4, INK), rule(1040, 30, 1040, h - 30)]
    size = min(96, int(900 / (len(name) * 0.74)))  # heavy caps run ~0.74em wide; keep clear of the spec column
    body.append(t(80, 130, name.upper(), size, "heavy", INK, track=-3))
    body.append(t(82, 200, line, 25, "mono", DIM))
    for i, (k, v) in enumerate(spec):
        y = 80 + i * 56
        x = 1290
        if k == "STARS":
            body.append(star(x, y + 1, 24))
            x += 36
        body.append(t(1090, y, k, 22, "mono", DIM, track=3) + t(x, y, v, 26, "monob", INK, track=1))
    return svg(W, h, "".join(body), f"{name}: {line}")


def tag(repo, name, stack, data):
    info = data["repos"].get(repo, {})
    w, h = 800, 160
    stars = info.get("stars")
    body = (rule(0, 2, w, 2, 3, INK) + t(32, 80, name.upper(), 52, "heavy", INK, track=-2)
            + t(34, 130, stack, 22, "mono", DIM, track=1)
            + (star(w - 32 - 22 - 12 * len(str(stars)) - 10, 132, 22) + t(w - 32, 130, str(stars), 22, "monob", INK, "end")
               if stars is not None else
               t(w - 32, 130, "PRIVATE", 22, "monob", DIM, "end", track=3)))
    return svg(w, h, body, f"{name}: {stack}")


def studio():
    services = [("WEB PRODUCTS", "Sites and platforms for businesses"),
                ("NATIVE MACOS", "Swift, SwiftUI and AppKit apps"),
                ("AI-AGENT TOOLING", "Skills, plugins, live widgets"),
                ("GAMES", "Unity, Three.js, creative coding")]
    h = 620
    body = [rule(0, 2, W, 2, 4, INK), t(80, 150, "EXODIA STUDIOS", 120, "heavy", INK, track=-4),
            t(82, 212, "Independent studio. Design and engineering under one roof.", 28, "mono", DIM)]
    for i, (k, v) in enumerate(services):
        x, y = 80 + (i % 2) * 760, 290 + (i // 2) * 150
        body.append(f'<rect x="{x}" y="{y}" width="744" height="134" fill="none" stroke="{RULE}" stroke-width="2"/>')
        body.append(t(x + 32, y + 64, k, 44, "heavy", INK, track=-1) + t(x + 32, y + 106, v, 24, "mono", DIM))
    return svg(W, h, "".join(body), "Exodia Studios: web products, native macOS, AI-agent tooling, games.")


def span(a, b=None):
    fmt_ = lambda d: f"{int(d[8:])} {MONTHS[int(d[5:7]) - 1]}" if d else "—"
    return f"{fmt_(a)} – {fmt_(b)}" if b else f"SINCE {fmt_(a)}"


MONTHS = ["JAN", "FEB", "MAR", "APR", "MAY", "JUN", "JUL", "AUG", "SEP", "OCT", "NOV", "DEC"]


def contributions(data):
    s, cal = data["summary"], data["calendar"]
    peak = max([c for _, c, _ in cal] or [1])
    body = [rule(0, 2, W, 2, 4, INK), t(80, 150, "CONTRIBUTIONS", 120, "heavy", INK, track=-4),
            t(W - 80, 58, f"[ UPDATED {data['updated']} / DAILY ]", 22, "mono", DIM, "end", track=3)]
    for i, (date, count, weekday) in enumerate(cal):
        x, y = 80 + (i // 7) * 28, 220 + weekday * 28
        fill = "#1A1A1A" if count == 0 else ("#4A4A4A", "#8C8C8C", INK)[min(2, int(3 * count / (peak + 1)))]
        if i == len(cal) - 1:
            fill = RED
        body.append(f'<rect x="{x}" y="{y}" width="22" height="22" fill="{fill}"><title>{date}: {count}</title></rect>')
    # three compartments: total stars, current streak, longest streak
    boxes = [("TOTAL GITHUB STARS", str(data["stars"]), f"ACROSS {data['public_repos']} PUBLIC REPOS", True),
             ("CURRENT STREAK", f"{s['current']} DAYS", span(s["current_from"]) if s["current"] else "—", False),
             ("LONGEST STREAK / 365D", f"{s['longest']} DAYS", span(s["longest_from"], s["longest_to"]), False)]
    for i, (label, value, note, icon) in enumerate(boxes):
        x, y = 80 + i * 512, 450
        body.append(f'<rect x="{x}" y="{y}" width="496" height="200" fill="none" stroke="{RULE}" stroke-width="2"/>')
        body.append(t(x + 32, y + 52, label, 22, "mono", DIM, track=3))
        vx = x + 32
        if icon:
            body.append(star(vx, y + 132, 56, RED))
            vx += 76
        body.append(t(vx, y + 132, value, 72, "heavy", INK, track=-2))
        body.append(t(x + 32, y + 174, note, 22, "monob", DIM, track=2))
    rows = [("TODAY", s["today"]), ("THIS MONTH", s["month"]), ("THIS YEAR", s["year"]),
            ("LAST 365 DAYS", s["window"]), ("FOLLOWERS", data["followers"]), ("PUBLIC REPOS", data["public_repos"])]
    for i, (k, v) in enumerate(rows):
        x, y = 80 + (i % 3) * 512, 740 + (i // 3) * 70
        body.append(rule(x, y - 46, x + 448, y - 46))
        body.append(t(x, y, k, 22, "mono", DIM, track=3) + t(x + 448, y, str(v), 40, "heavy", INK, "end"))
    return svg(W, 860, "".join(body),
               f"Contributions: {s['year']} this year, current streak {s['current']} days, {data['stars']} total stars.")


def sponsor():
    perks = ["EVERY SPONSOR  /  NAME IN THIS README",
             "COMPANIES      /  LOGO IN TUCKBIT + WIDGET-KIT READMES",
             "ALL SPONSORS   /  ISSUES LOOKED AT FIRST"]
    body = [rule(0, 2, W, 2, 4, RED), t(80, 150, "SPONSOR", 120, "heavy", RED, track=-4),
            t(82, 214, "Sponsorship keeps the tools free, maintained and fast.", 30, "mono", INK)]
    for i, p in enumerate(perks):
        y = 310 + i * 70
        body.append(rule(80, y - 46, W - 80, y - 46))
        body.append(t(80, y, p, 26, "monob", INK, track=1))
    return svg(W, 520, "".join(body), "Sponsor: name in README, company logos, issues looked at first.")


def footer():
    body = (rule(0, 2, W, 2, 4, INK) + t(80, 84, "EOF", 40, "heavy", INK)
            + t(W - 80, 84, "[ NICOLAS SAVVIDES / CYPRUS / 2026 ]", 22, "mono", DIM, "end", track=3))
    return svg(W, 130, body, "End of profile.")


FLAGSHIPS = [("tuck-bit", "TuckBit", "Right tools, scoped context and adaptive workflows on cue.", "PYTHON / MCP / SKILLS"),
             ("Gridline", "Gridline", "AI skills for architecture, CAD and BIM.", "PYTHON / CAD / BIM"),
             ("claude-widget-kit", "Claude Widget Kit", "Live usage rings and agent cards inside Claude Code.", "TYPESCRIPT / MODS")]
SECOND = [("signai-asl-gesture-demo", "SignAI", "MEDIAPIPE / ONNX / REACT"),
          ("grapharium", "Grapharium", "THREE.JS / PYTHON"),
          ("Dungeon_Escape_Project", "Dungeon Escape", "UNITY 6 / C#"),
          ("AirPTTBridge", "AirPTTBridge", "C# / .NET / WASAPI"),
          ("predictx", "PredictX", "TYPESCRIPT / TRPC / STRIPE"),
          ("DynamicIsland", "DynamicIsland", "SWIFT / SWIFTUI / APPKIT")]


def outputs():
    data = json.loads((OUT / "data.json").read_text(encoding="utf-8"))
    files = {"hero.svg": hero_right(),
             "link-sponsor.svg": link("SPONSOR", True), "link-follow.svg": link("FOLLOW"),
             "link-studio.svg": link("EXODIASTUDIOS.COM"),
             "work.svg": heading("WORK", "[ FLAGSHIPS / THEN THE REST ]"),
             "studio.svg": studio(), "contributions.svg": contributions(data), "sponsor.svg": sponsor(), "footer.svg": footer()}
    for repo, name, line, stack in FLAGSHIPS:
        files[f"sheet-{repo}.svg"] = project_sheet(repo, name, line, stack, data)
    for repo, name, stack in SECOND:
        files[f"tag-{repo}.svg"] = tag(repo, name, stack, data)
    return files


def main_write():
    for rel, content in outputs().items():
        (OUT / rel).write_text(content, encoding="utf-8")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    if not args.check:
        main_write()
        return 0
    stale = [rel for rel, content in outputs().items()
             if not (OUT / rel).is_file() or (OUT / rel).read_text(encoding="utf-8") != content]
    if stale:
        print("Stale telemetry panels: " + ", ".join(stale), file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
