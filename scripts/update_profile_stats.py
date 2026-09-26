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
    stars = sum(int(r.get("stargazers_count", 0)) for r in repos if not r.get("fork"))
    forks = sum(int(r.get("forks_count", 0)) for r in repos if not r.get("fork"))
    return {
        "repos": int(user.get("public_repos", len(repos))),
        "followers": int(user.get("followers", 0)),
        "stars": stars,
        "forks": forks,
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
    result = request_json("https://api.github.com/graphql", {"query": query, "variables": {"login": USERNAME}})
    if result.get("errors"):
        raise RuntimeError(result["errors"])
    return result["data"]["user"]["contributionsCollection"]["contributionCalendar"]

def color_for(value, maximum):
    if value <= 0:
        return "#0d2d1f"
    ratio = value / max(1, maximum)
    if ratio < .25:
        return "#145137"
    if ratio < .5:
        return "#20784d"
    if ratio < .75:
        return "#31b66d"
    return "#4df394"

def render(stats, calendar):
    weeks = calendar.get("weeks", [])[-53:]
    days = [d for w in weeks for d in w.get("contributionDays", [])]
    maximum = max([int(d.get("contributionCount", 0)) for d in days] or [1])
    heat = []
    weekly = []
    for wi, week in enumerate(weeks):
        total = 0
        for day in week.get("contributionDays", []):
            count = int(day.get("contributionCount", 0))
            total += count
            weekday = int(day.get("weekday", 0))
            x = 212 + wi * 23
            y = 215 + weekday * 23
            heat.append(f'<rect x="{x}" y="{y}" width="17" height="17" rx="3" fill="{color_for(count, maximum)}"><title>{html.escape(day.get("date",""))}: {count} contributions</title></rect>')
        weekly.append(total)

    graph_points = []
    weekly_max = max(weekly or [1])
    for i, value in enumerate(weekly):
        x = 212 + i * 23 + 8
        y = 364 - (value / max(1, weekly_max)) * 62
        graph_points.append(f"{x:.1f},{y:.1f}")
    polyline = " ".join(graph_points)

    generated = dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    total = int(calendar.get("totalContributions", 0))

    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="1664" height="936" viewBox="0 0 1664 936">
<defs>
 <pattern id="grid" width="42" height="42" patternUnits="userSpaceOnUse"><path d="M42 0H0V42" fill="none" stroke="#123c2d" stroke-width="1" opacity=".42"/></pattern>
 <filter id="b"><feGaussianBlur stdDeviation="4"/></filter>
</defs>
<rect width="1664" height="936" rx="18" fill="#08100f"/><rect x="34" y="28" width="1596" height="880" rx="22" fill="#04140d" stroke="#165d3d"/><rect x="34" y="28" width="1596" height="880" rx="22" fill="url(#grid)"/>
<text x="832" y="88" text-anchor="middle" fill="#55f497" font-family="Inter,system-ui,sans-serif" font-size="48" font-weight="900">CONTRIBUTION ACTIVITY</text>
<text x="832" y="128" text-anchor="middle" fill="#58c78d" font-family="ui-monospace,monospace" font-size="13" font-weight="800" letter-spacing="6">BUILD / CONTRIBUTE / SHIP / REPEAT</text>
<rect x="180" y="165" width="1304" height="235" rx="18" fill="#071c13" stroke="#1d754b"/>
<text x="205" y="198" fill="#65f8a1" font-family="ui-monospace,monospace" font-size="12" font-weight="800" letter-spacing="3">CONTRIBUTION TELEMETRY / 365 DAYS</text>
<text x="1458" y="198" text-anchor="end" fill="#4ca277" font-family="ui-monospace,monospace" font-size="11">{html.escape(generated)}</text>
{''.join(heat)}
<polyline points="{polyline}" fill="none" stroke="#3be888" stroke-width="2.5" opacity=".72"/>
<circle cx="220" cy="365" r="7" fill="#98ffc2" filter="url(#b)"><animate attributeName="cx" values="220;1420;220" dur="7s" repeatCount="indefinite"/></circle>

<g font-family="Inter,system-ui,sans-serif">
<g transform="translate(180 430)"><rect width="300" height="120" rx="16" fill="#08251a" stroke="#1f7c50"/><text x="24" y="38" fill="#58ee99" font-family="ui-monospace,monospace" font-size="11" font-weight="800">PUBLIC REPOS</text><text x="24" y="88" fill="#effff5" font-size="34" font-weight="900">{stats["repos"]}</text></g>
<g transform="translate(515 430)"><rect width="300" height="120" rx="16" fill="#08251a" stroke="#1f7c50"/><text x="24" y="38" fill="#58ee99" font-family="ui-monospace,monospace" font-size="11" font-weight="800">FOLLOWERS</text><text x="24" y="88" fill="#effff5" font-size="34" font-weight="900">{stats["followers"]}</text></g>
<g transform="translate(850 430)"><rect width="300" height="120" rx="16" fill="#08251a" stroke="#1f7c50"/><text x="24" y="38" fill="#58ee99" font-family="ui-monospace,monospace" font-size="11" font-weight="800">TOTAL STARS</text><text x="24" y="88" fill="#effff5" font-size="34" font-weight="900">{stats["stars"]}</text></g>
<g transform="translate(1185 430)"><rect width="300" height="120" rx="16" fill="#08251a" stroke="#1f7c50"/><text x="24" y="38" fill="#58ee99" font-family="ui-monospace,monospace" font-size="11" font-weight="800">365-DAY CONTRIBUTIONS</text><text x="24" y="88" fill="#effff5" font-size="34" font-weight="900">{total}</text></g>
</g>

<text x="832" y="620" text-anchor="middle" fill="#55f497" font-family="Inter,system-ui,sans-serif" font-size="40" font-weight="900">CURRENT FOCUS</text>
<text x="832" y="650" text-anchor="middle" fill="#58bd89" font-family="ui-monospace,monospace" font-size="12" font-weight="800" letter-spacing="5">ACTIVE ENGINEERING DOMAINS</text>
<g font-family="Inter,system-ui,sans-serif" text-anchor="middle">
<g transform="translate(180 680)"><rect width="300" height="150" rx="16" fill="#08251a" stroke="#1f7c50"/><text x="150" y="55" fill="#effff5" font-size="21" font-weight="900">AI SYSTEMS</text><text x="150" y="92" fill="#92cba9" font-size="14">Gesture AI • inference</text><text x="150" y="117" fill="#92cba9" font-size="14">automation</text><circle cx="268" cy="28" r="5" fill="#55ffa0"><animate attributeName="opacity" values=".2;1;.2" dur="2s" repeatCount="indefinite"/></circle></g>
<g transform="translate(515 680)"><rect width="300" height="150" rx="16" fill="#08251a" stroke="#1f7c50"/><text x="150" y="55" fill="#effff5" font-size="21" font-weight="900">MODERN WEB</text><text x="150" y="92" fill="#92cba9" font-size="14">React • Next.js</text><text x="150" y="117" fill="#92cba9" font-size="14">TypeScript</text><circle cx="268" cy="28" r="5" fill="#55ffa0"><animate attributeName="r" values="4;7;4" dur="2.5s" repeatCount="indefinite"/></circle></g>
<g transform="translate(850 680)"><rect width="300" height="150" rx="16" fill="#08251a" stroke="#1f7c50"/><text x="150" y="55" fill="#effff5" font-size="21" font-weight="900">NATIVE APPS</text><text x="150" y="92" fill="#92cba9" font-size="14">Swift • C# • Java</text><text x="150" y="117" fill="#92cba9" font-size="14">desktop systems</text><circle cx="268" cy="28" r="5" fill="#55ffa0"><animate attributeName="opacity" values=".2;1;.2" dur="2.8s" repeatCount="indefinite"/></circle></g>
<g transform="translate(1185 680)"><rect width="300" height="150" rx="16" fill="#08251a" stroke="#1f7c50"/><text x="150" y="55" fill="#effff5" font-size="21" font-weight="900">GAMES + GRAPHICS</text><text x="150" y="92" fill="#92cba9" font-size="14">Unity • Three.js</text><text x="150" y="117" fill="#92cba9" font-size="14">creative computing</text><circle cx="268" cy="28" r="5" fill="#55ffa0"><animate attributeName="r" values="4;7;4" dur="3s" repeatCount="indefinite"/></circle></g>
</g>
<text x="832" y="882" text-anchor="middle" fill="#2f9b68" font-family="ui-monospace,monospace" font-size="11" font-weight="800" letter-spacing="4">PUBLIC GITHUB TELEMETRY // {stats["forks"]} TOTAL FORKS // AUTO-REFRESHED DAILY</text>
</svg>'''

def main():
    stats = public_stats()
    calendar = contribution_calendar()
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(render(stats, calendar), encoding="utf-8")
    print(f"Wrote {OUT} for {USERNAME}: {stats}, contributions={calendar.get('totalContributions', 0)}")

if __name__ == "__main__":
    main()
