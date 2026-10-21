#!/usr/bin/env python3
import datetime as dt
import html
import json
import os
import sys
import urllib.request
from pathlib import Path

USERNAME = os.getenv("PROFILE_USERNAME", "MakeItEzzz555")
TOKEN = os.getenv("GITHUB_TOKEN", "")
sys.path.insert(0, str(Path(__file__).resolve().parent))
OUT = Path("assets/signal")

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

def summary(calendar):
    """Day/month/year totals and streaks from the contribution calendar (last day = today)."""
    days = [(d["date"], int(d.get("contributionCount", 0)))
            for w in calendar.get("weeks", []) for d in w.get("contributionDays", [])]
    days.sort()
    if not days:
        return {"today": 0, "month": 0, "year": 0, "window": 0, "current": 0, "longest": 0}
    today = days[-1][0]
    longest = run = 0
    for _, count in days:
        run = run + 1 if count else 0
        longest = max(longest, run)
    current = 0
    tail = days[:-1] if days[-1][1] == 0 else days  # an empty today doesn't break the streak yet
    for _, count in reversed(tail):
        if not count:
            break
        current += 1
    return {
        "today": days[-1][1],
        "month": sum(c for d, c in days if d[:7] == today[:7]),
        "year": sum(c for d, c in days if d[:4] == today[:4]),
        "window": int(calendar.get("totalContributions", sum(c for _, c in days))),
        "current": current,
        "longest": longest,
    }


def level(count, maximum):
    if count <= 0:
        return 0
    return 1 + min(2, int(3 * count / max(1, maximum + 1)))


def render(stats, calendar, t):
    from build_signal_panels import W, svg, text
    weeks = calendar.get("weeks", [])[-53:]
    peak = max([int(d.get("contributionCount", 0)) for w in weeks for d in w.get("contributionDays", [])] or [0])
    cells = []
    for wi, week in enumerate(weeks):
        for day in week.get("contributionDays", []):
            count = int(day.get("contributionCount", 0))
            x, y = 96 + wi * 27, 196 + int(day.get("weekday", 0)) * 27
            cells.append(f'<rect x="{x}" y="{y}" width="22" height="22" fill="{t["cells"][level(count, peak)]}">'
                         f'<title>{html.escape(day.get("date", ""))}: {count}</title></rect>')
    s = summary(calendar)
    rows = [("Contributions today", s["today"], "Stars across my repositories", stats["stars"]),
            ("This month", s["month"], "Followers", stats["followers"]),
            ("This year", s["year"], "Current streak, days", s["current"]),
            ("Last 365 days", s["window"], "Longest streak, 365 days", s["longest"])]
    body = text(96, 130, "Log", 104, t, "display", tracking=-3)
    updated = dt.datetime.now(dt.timezone.utc).strftime("%-d %B %Y")
    body += text(W - 96, 130, f"Updated {updated}, refreshed daily", 30, t, fill=t["muted"], anchor="end")
    body += "".join(cells)
    for i, (la, va, lb, vb) in enumerate(rows):
        y = 470 + i * 84
        body += f'<path d="M96 {y - 58}H{W - 96}" stroke="{t["rule"]}" stroke-width="2"/>'
        body += text(96, y, la, 36, t, fill=t["muted"]) + text(780, y, str(va), 48, t, "display", anchor="end")
        body += text(884, y, lb, 36, t, fill=t["muted"]) + text(W - 96, y, str(vb), 48, t, "display", anchor="end")
    return svg(800, t, body, f"Log: {stats['stars']} stars, {s['year']} contributions this year, "
                            f"current streak {s['current']} days.")


def main():
    stats = public_stats()
    calendar = contribution_calendar()
    from build_signal_panels import THEMES
    for mode, theme in THEMES.items():
        (OUT / mode).mkdir(parents=True, exist_ok=True)
        (OUT / mode / "log.svg").write_text(render(stats, calendar, theme), encoding="utf-8")
    print(f"Wrote {OUT}: {stats}, contributions={calendar.get('totalContributions', 0)}")

if __name__ == "__main__":
    main()
