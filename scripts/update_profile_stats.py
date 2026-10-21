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
OUT = Path(__file__).resolve().parents[1] / "assets" / "telemetry"

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
        "per_repo": {r["name"]: {"stars": int(r.get("stargazers_count", 0)), "pushed": (r.get("pushed_at") or "")[:10],
                                 "license": (r.get("license") or {}).get("spdx_id")} for r in owned},
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
    """Day/month/year totals and streaks (with date ranges) from the calendar; last day = today."""
    days = sorted((d["date"], int(d.get("contributionCount", 0)))
                  for w in calendar.get("weeks", []) for d in w.get("contributionDays", []))
    if not days:
        return {"today": 0, "month": 0, "year": 0, "window": 0, "current": 0, "longest": 0,
                "current_from": None, "longest_from": None, "longest_to": None}
    today = days[-1][0]
    longest, longest_span, run, run_from = 0, (None, None), 0, None
    for date, count in days:
        run, run_from = (run + 1, run_from or date) if count else (0, None)
        if run > longest:
            longest, longest_span = run, (run_from, date)
    current, current_from = 0, None
    tail = days[:-1] if days[-1][1] == 0 else days  # an empty today doesn't break the streak yet
    for date, count in reversed(tail):
        if not count:
            break
        current, current_from = current + 1, date
    return {
        "today": days[-1][1],
        "month": sum(c for d, c in days if d[:7] == today[:7]),
        "year": sum(c for d, c in days if d[:4] == today[:4]),
        "window": int(calendar.get("totalContributions", sum(c for _, c in days))),
        "current": current, "current_from": current_from,
        "longest": longest, "longest_from": longest_span[0], "longest_to": longest_span[1],
    }


def main():
    stats = public_stats()
    calendar = contribution_calendar()
    days = sorted(((d["date"], int(d.get("contributionCount", 0)), int(d.get("weekday", 0)))
                   for w in calendar.get("weeks", [])[-53:] for d in w.get("contributionDays", [])))
    data = {
        "updated": dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%d"),
        "stars": stats["stars"], "followers": stats["followers"], "public_repos": stats["repos"],
        "summary": summary(calendar),
        "calendar": days,
    }
    data["repos"] = stats["per_repo"]
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "data.json").write_text(json.dumps(data, indent=1, sort_keys=True) + "\n", encoding="utf-8")
    import build_telemetry_panels
    build_telemetry_panels.main_write()
    print(f"Wrote {OUT}: stars={stats['stars']}, contributions={calendar.get('totalContributions', 0)}")


if __name__ == "__main__":
    main()
