#!/usr/bin/env python3
import datetime as dt
import html
import json
import os
import urllib.request
from pathlib import Path

USERNAME = os.getenv("PROFILE_USERNAME", "MakeItEzzz555")
TOKEN = os.environ["GITHUB_TOKEN"]
OUT = Path("assets/animated/contribution-activity.svg")

def request_json(url, payload=None):
    headers = {
        "Accept": "application/vnd.github+json",
        "Authorization": f"Bearer {TOKEN}",
        "User-Agent": "animated-profile-telemetry",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    data = None if payload is None else json.dumps(payload).encode()
    if payload is not None:
        headers["Content-Type"] = "application/json"
    req = urllib.request.Request(url, data=data, headers=headers)
    with urllib.request.urlopen(req, timeout=30) as response:
        return json.load(response)

def public_stats():
    user = request_json(f"https://api.github.com/users/{USERNAME}")
    repos = request_json(f"https://api.github.com/users/{USERNAME}/repos?per_page=100&type=owner&sort=updated")
    owned = [r for r in repos if not r.get("fork")]
    return {
        "repos": int(user.get("public_repos", len(owned))),
        "followers": int(user.get("followers", 0)),
        "stars": sum(int(r.get("stargazers_count", 0)) for r in owned),
        "forks": sum(int(r.get("forks_count", 0)) for r in owned),
    }

def contribution_calendar():
    query = """
    query($login:String!) {
      user(login:$login) {
        contributionsCollection {
          contributionCalendar {
            totalContributions
            weeks {
              contributionDays {
                contributionCount
                date
                weekday
              }
            }
          }
        }
      }
    }
    """
    result = request_json(
        "https://api.github.com/graphql",
        {"query": query, "variables": {"login": USERNAME}},
    )
    if result.get("errors"):
        raise RuntimeError(result["errors"])
    return result["data"]["user"]["contributionsCollection"]["contributionCalendar"]

def color_for(value, maximum):
    if value <= 0:
        return "#0d2d1f"
    ratio = value / max(1, maximum)
    if ratio < .25:
        return "#155239"
    if ratio < .5:
        return "#217b50"
    if ratio < .75:
        return "#31b96f"
    return "#4df394"

def render(stats, calendar):
    weeks = calendar.get("weeks", [])[-53:]
    all_days = [d for w in weeks for d in w.get("contributionDays", [])]
    maximum = max([int(d.get("contributionCount", 0)) for d in all_days] or [1])

    heat = []
    weekly_totals = []
    for wi, week in enumerate(weeks):
        weekly_total = 0
        for day in week.get("contributionDays", []):
            count = int(day.get("contributionCount", 0))
            weekly_total += count
            weekday = int(day.get("weekday", 0))
            x = 220 + wi * 23
            y = 220 + weekday * 22
            heat.append(
                f'<rect x="{x}" y="{y}" width="17" height="17" rx="3" '
                f'fill="{color_for(count, maximum)}"><title>'
                f'{html.escape(day.get("date", ""))}: {count} contributions'
                f'</title></rect>'
            )
        weekly_totals.append(weekly_total)

    peak = max(weekly_totals or [1])
    graph = []
    for i, value in enumerate(weekly_totals):
        x = 228 + i * 23
        y = 395 - (value / max(1, peak)) * 70
        graph.append(f"{x:.1f},{y:.1f}")

    total = int(calendar.get("totalContributions", 0))
    generated = dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="1664" height="936" viewBox="0 0 1664 936">
<defs>
  <pattern id="grid" width="52" height="52" patternUnits="userSpaceOnUse">
    <path d="M52 0H0V52" fill="none" stroke="#174a35" stroke-width="1.2" opacity=".34"/>
    <animateTransform attributeName="patternTransform" type="translate" from="0 0" to="52 52" dur="20s" repeatCount="indefinite"/>
  </pattern>
  <radialGradient id="halo"><stop offset="0" stop-color="#32ff91" stop-opacity=".16"/><stop offset="1" stop-color="#03110b" stop-opacity="0"/></radialGradient>
  <linearGradient id="scan" x1="0" x2="0" y1="0" y2="1"><stop stop-color="#4cff9d" stop-opacity="0"/><stop offset=".5" stop-color="#4cff9d" stop-opacity=".17"/><stop offset="1" stop-color="#4cff9d" stop-opacity="0"/></linearGradient>
  <filter id="blur"><feGaussianBlur stdDeviation="4"/></filter>
</defs>

<rect width="1664" height="936" rx="22" fill="#07100e"/>
<rect x="34" y="28" width="1596" height="880" rx="24" fill="#04140d" stroke="#1b6848" stroke-width="1.5"/>
<rect x="34" y="28" width="1596" height="880" rx="24" fill="url(#grid)"/>
<rect width="1664" height="936" fill="url(#halo)"><animate attributeName="opacity" values=".45;1;.45" dur="10s" repeatCount="indefinite"/></rect>
<rect x="36" y="-120" width="1592" height="180" fill="url(#scan)"><animate attributeName="y" values="-120;860;-120" dur="13s" repeatCount="indefinite"/></rect>

<g stroke="#45ff99" stroke-width="2.3" opacity=".58"><path d="M68 92V50h44"/><path d="M1552 50h44v42"/><path d="M68 844v42h44"/><path d="M1552 886h44v-42"/></g>

<text x="832" y="92" text-anchor="middle" fill="#56f49a" font-family="Inter,system-ui,sans-serif" font-size="56" font-weight="900">CONTRIBUTION ACTIVITY</text>
<text x="832" y="136" text-anchor="middle" fill="#5bca91" font-family="ui-monospace,monospace" font-size="19" font-weight="800" letter-spacing="5">BUILD / CONTRIBUTE / SHIP / REPEAT</text>

<rect x="170" y="170" width="1324" height="260" rx="20" fill="#071d13" stroke="#22794f" stroke-width="1.5"/>
<text x="202" y="208" fill="#61f7a1" font-family="ui-monospace,monospace" font-size="18" font-weight="800" letter-spacing="2">CONTRIBUTION TELEMETRY / 365 DAYS</text>
<text x="1460" y="208" text-anchor="end" fill="#67b78d" font-family="ui-monospace,monospace" font-size="17">{html.escape(generated)}</text>
{''.join(heat)}
<polyline points="{' '.join(graph)}" fill="none" stroke="#4bf697" stroke-width="3.2" stroke-linecap="round" stroke-linejoin="round" stroke-dasharray="1600" stroke-dashoffset="1600">
  <animate attributeName="stroke-dashoffset" values="1600;0;0;1600" keyTimes="0;.28;.78;1" dur="9s" repeatCount="indefinite"/>
</polyline>
<circle r="7" fill="#a2ffca" filter="url(#blur)"><animateMotion dur="8s" repeatCount="indefinite" path="M210 405H1450"/></circle>

<g font-family="Inter,system-ui,sans-serif">
  <g transform="translate(170 460)"><rect width="310" height="130" rx="17" fill="#08261a" stroke="#227f52"/><text x="25" y="42" fill="#60f5a0" font-family="ui-monospace,monospace" font-size="18" font-weight="800">PUBLIC REPOS</text><text x="25" y="98" fill="#effff5" font-size="44" font-weight="900">{stats["repos"]}</text></g>
  <g transform="translate(508 460)"><rect width="310" height="130" rx="17" fill="#08261a" stroke="#227f52"/><text x="25" y="42" fill="#60f5a0" font-family="ui-monospace,monospace" font-size="18" font-weight="800">FOLLOWERS</text><text x="25" y="98" fill="#effff5" font-size="44" font-weight="900">{stats["followers"]}</text></g>
  <g transform="translate(846 460)"><rect width="310" height="130" rx="17" fill="#08261a" stroke="#227f52"/><text x="25" y="42" fill="#60f5a0" font-family="ui-monospace,monospace" font-size="18" font-weight="800">TOTAL STARS</text><text x="25" y="98" fill="#effff5" font-size="44" font-weight="900">{stats["stars"]}</text></g>
  <g transform="translate(1184 460)"><rect width="310" height="130" rx="17" fill="#08261a" stroke="#227f52"/><text x="25" y="42" fill="#60f5a0" font-family="ui-monospace,monospace" font-size="18" font-weight="800">CONTRIBUTIONS</text><text x="25" y="98" fill="#effff5" font-size="44" font-weight="900">{total}</text></g>
</g>

<text x="832" y="654" text-anchor="middle" fill="#56f49a" font-family="Inter,system-ui,sans-serif" font-size="44" font-weight="900">CURRENT FOCUS</text>
<text x="832" y="690" text-anchor="middle" fill="#65c590" font-family="ui-monospace,monospace" font-size="18" font-weight="800" letter-spacing="4">ACTIVE ENGINEERING DOMAINS</text>

<g font-family="Inter,system-ui,sans-serif" text-anchor="middle">
  <g transform="translate(170 720)"><rect width="310" height="130" rx="17" fill="#08261a" stroke="#227f52"/><text x="155" y="54" fill="#effff5" font-size="23" font-weight="900">AI SYSTEMS</text><text x="155" y="92" fill="#a3d0b5" font-size="19">Gesture AI • inference</text><circle cx="278" cy="28" r="6" fill="#61ffa6"><animate attributeName="opacity" values=".2;1;.2" dur="2s" repeatCount="indefinite"/></circle></g>
  <g transform="translate(508 720)"><rect width="310" height="130" rx="17" fill="#08261a" stroke="#227f52"/><text x="155" y="54" fill="#effff5" font-size="23" font-weight="900">MODERN WEB</text><text x="155" y="92" fill="#a3d0b5" font-size="19">React • Next.js • TS</text><circle cx="278" cy="28" r="6" fill="#61ffa6"><animate attributeName="r" values="4;8;4" dur="2.5s" repeatCount="indefinite"/></circle></g>
  <g transform="translate(846 720)"><rect width="310" height="130" rx="17" fill="#08261a" stroke="#227f52"/><text x="155" y="54" fill="#effff5" font-size="23" font-weight="900">NATIVE APPS</text><text x="155" y="92" fill="#a3d0b5" font-size="19">Swift • C# • Java</text><circle cx="278" cy="28" r="6" fill="#61ffa6"><animate attributeName="opacity" values=".2;1;.2" dur="2.8s" repeatCount="indefinite"/></circle></g>
  <g transform="translate(1184 720)"><rect width="310" height="130" rx="17" fill="#08261a" stroke="#227f52"/><text x="155" y="54" fill="#effff5" font-size="23" font-weight="900">GAMES + GRAPHICS</text><text x="155" y="92" fill="#a3d0b5" font-size="19">Unity • Three.js</text><circle cx="278" cy="28" r="6" fill="#61ffa6"><animate attributeName="r" values="4;8;4" dur="3s" repeatCount="indefinite"/></circle></g>
</g>

<text x="832" y="890" text-anchor="middle" fill="#3aaa72" font-family="ui-monospace,monospace" font-size="17" font-weight="800" letter-spacing="3">PUBLIC GITHUB TELEMETRY // {stats["forks"]} FORKS // AUTO-REFRESHED DAILY</text>
</svg>'''

def main():
    stats = public_stats()
    calendar = contribution_calendar()
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(render(stats, calendar), encoding="utf-8")
    print(f"Wrote {OUT}: {stats}, contributions={calendar.get('totalContributions', 0)}")

if __name__ == "__main__":
    main()
