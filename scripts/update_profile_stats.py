#!/usr/bin/env python3
import datetime as dt
import html
import json
import os
import sys
import urllib.request
from pathlib import Path
from urllib.parse import quote

USERNAME = os.getenv("PROFILE_USERNAME", "MakeItEzzz555")
TOKEN = os.getenv("GITHUB_TOKEN", "")
sys.path.insert(0, str(Path(__file__).resolve().parent))
OUT = Path(__file__).resolve().parents[1] / "assets" / "telemetry"

def request_json(url, payload=None):
    headers = {
        "Accept": "application/vnd.github+json",
        "User-Agent": "animated-profile-telemetry",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    if TOKEN:
        headers["Authorization"] = f"Bearer {TOKEN}"
    data = None if payload is None else json.dumps(payload).encode()
    if payload is not None:
        headers["Content-Type"] = "application/json"
    req = urllib.request.Request(url, data=data, headers=headers)
    with urllib.request.urlopen(req, timeout=30) as response:
        return json.load(response)


def public_repositories():
    """Fetch every public owned repo, not just GitHub's first 100 results.

    Fail closed on unexpectedly truncated/duplicated responses instead of
    publishing incorrect stars or dropping newly created projects.
    """
    repos = []
    seen = set()
    user = quote(USERNAME, safe="")
    for page in range(1, 101):
        url = (f"https://api.github.com/users/{user}/repos"
               f"?per_page=100&type=owner&sort=updated&page={page}")
        batch = request_json(url)
        if not isinstance(batch, list) or len(batch) > 100:
            raise RuntimeError(f"Invalid GitHub repository page {page}")
        for repo in batch:
            if not isinstance(repo, dict) or not isinstance(repo.get("name"), str):
                raise RuntimeError(f"Malformed GitHub repository record on page {page}")
            name = repo["name"]
            if not name or name in seen:
                raise RuntimeError(f"Invalid or duplicate repository name: {name!r}")
            seen.add(name)
            repos.append(repo)
        if len(batch) < 100:
            return repos
    raise RuntimeError("Repository pagination exceeded 100 pages; not publishing partial stats")


def public_stats():
    user = request_json(f"https://api.github.com/users/{quote(USERNAME, safe='')}")
    if not isinstance(user, dict) or not isinstance(user.get("public_repos"), int):
        raise RuntimeError("GitHub user statistics are missing or invalid")
    repos = public_repositories()
    owned = [r for r in repos if not r.get("fork")]
    per_repo = {}
    for repo in owned:
        if any(not isinstance(repo.get(field), int) or repo[field] < 0
               for field in ("stargazers_count", "forks_count")):
            raise RuntimeError(f"Missing or invalid GitHub counters for {repo['name']}")
        per_repo[repo["name"]] = {
            "stars": repo["stargazers_count"],
            "pushed": (repo.get("pushed_at") or "")[:10],
            "license": (repo.get("license") or {}).get("spdx_id"),
        }
    if len(repos) != user["public_repos"]:
        raise RuntimeError(
            f"GitHub public repo count mismatch: profile={user['public_repos']} fetched={len(repos)}"
        )
    if not isinstance(user.get("followers"), int) or user["followers"] < 0:
        raise RuntimeError("GitHub follower count missing or invalid")
    return {
        "per_repo": per_repo,
        "repos": len(repos),
        "followers": user["followers"],
        "stars": sum(r["stargazers_count"] for r in owned),
        "forks": sum(r["forks_count"] for r in owned),
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
    if not isinstance(result, dict) or result.get("errors"):
        raise RuntimeError("GitHub GraphQL contributions request failed")
    try:
        calendar = result["data"]["user"]["contributionsCollection"]["contributionCalendar"]
    except (KeyError, TypeError) as exc:
        raise RuntimeError("GitHub returned no contribution calendar") from exc
    if not isinstance(calendar, dict) or not isinstance(calendar.get("weeks"), list):
        raise RuntimeError("GitHub contribution calendar is incomplete")
    if not calendar["weeks"] or not any(week.get("contributionDays") for week in calendar["weeks"]):
        raise RuntimeError("GitHub contribution calendar contains no days")
    return calendar

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
