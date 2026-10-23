"""Regression coverage for dynamic profile statistics and fail-closed refreshes."""
import json
import sys
import tempfile
import unittest
from pathlib import Path
from urllib.parse import urlsplit, parse_qs
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import update_profile_stats as stats


def repo(i, *, fork=False, stars=None):
    return {
        "name": f"repo-{i}",
        "fork": fork,
        "stargazers_count": (i % 6 if stars is None else stars),
        "forks_count": i % 4,
        "pushed_at": "2026-10-23T06:20:00Z",
        "license": {"spdx_id": "MIT"},
    }


def calendar():
    return {
        "totalContributions": 7,
        "weeks": [{"contributionDays": [
            {"date": "2026-10-21", "contributionCount": 2, "weekday": 3},
            {"date": "2026-10-22", "contributionCount": 5, "weekday": 4},
            {"date": "2026-10-23", "contributionCount": 0, "weekday": 5},
        ]}],
    }


class ProfileStatsAPITests(unittest.TestCase):
    def test_paginates_all_public_repos_and_aggregates_stars(self):
        records = [repo(i) for i in range(149)] + [repo(149, fork=True)]
        visited = []

        def fake_api(url, payload=None):
            visited.append(url)
            if "/users/" in url and "/repos" not in url:
                return {"public_repos": 150, "followers": 42}
            page = parse_qs(urlsplit(url).query).get("page", [None])[0]
            if page == "1":
                return records[:100]
            if page == "2":
                return records[100:]
            self.fail(f"Unexpected request {url}")

        with patch.object(stats, "request_json", side_effect=fake_api):
            result = stats.public_stats()
        self.assertEqual(result["repos"], 150)
        self.assertEqual(result["followers"], 42)
        self.assertEqual(result["stars"], sum(r["stargazers_count"] for r in records[:-1]))
        self.assertEqual(len(result["per_repo"]), 149)
        self.assertNotIn("repo-149", result["per_repo"])
        self.assertEqual(sum("/repos?" in url for url in visited), 2)

    def test_exactly_hundred_repos_requests_last_empty_page(self):
        records = [repo(i) for i in range(100)]
        visited = []

        def fake_api(url, payload=None):
            visited.append(url)
            page = parse_qs(urlsplit(url).query).get("page", [None])[0]
            return records if page == "1" else []

        with patch.object(stats, "request_json", side_effect=fake_api):
            found = stats.public_repositories()
        self.assertEqual(len(found), 100)
        self.assertEqual(len(visited), 2)

    def test_duplicate_page_fails_instead_of_double_counting(self):
        records = [repo(i) for i in range(100)]
        with patch.object(stats, "request_json", side_effect=[records, records]):
            with self.assertRaisesRegex(RuntimeError, "duplicate"):
                stats.public_repositories()

    def test_count_mismatch_fails_closed(self):
        with patch.object(stats, "request_json", side_effect=[
            {"public_repos": 200, "followers": 10},
            [repo(1)],
        ]):
            with self.assertRaisesRegex(RuntimeError, "mismatch"):
                stats.public_stats()

    def test_missing_star_counter_fails_closed(self):
        bad = repo(1)
        bad.pop("stargazers_count")
        with patch.object(stats, "request_json", side_effect=[
            {"public_repos": 1, "followers": 10},
            [bad],
        ]):
            with self.assertRaisesRegex(RuntimeError, "counters"):
                stats.public_stats()

    def test_graphql_errors_or_missing_calendar_do_not_publish_zeros(self):
        with patch.object(stats, "request_json", return_value={"errors": [{"message": "throttled"}]}):
            with self.assertRaisesRegex(RuntimeError, "failed"):
                stats.contribution_calendar()
        with patch.object(stats, "request_json", return_value={"data": {"user": None}}):
            with self.assertRaisesRegex(RuntimeError, "no contribution calendar"):
                stats.contribution_calendar()
        with patch.object(stats, "request_json", return_value={"data": {
            "user": {"contributionsCollection": {"contributionCalendar": {"weeks": []}}}
        }}):
            with self.assertRaisesRegex(RuntimeError, "no days"):
                stats.contribution_calendar()

    def test_streaks_and_periods_reflect_fetched_days(self):
        s = stats.summary(calendar())
        self.assertEqual((s["today"], s["month"], s["year"], s["window"]), (0, 7, 7, 7))
        self.assertEqual((s["current"], s["current_from"]), (2, "2026-10-21"))
        self.assertEqual((s["longest"], s["longest_to"]), (2, "2026-10-22"))

    def test_failed_refresh_does_not_overwrite_existing_data(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "data.json"
            path.write_text('{"previous":"valid"}\n')
            with patch.object(stats, "OUT", Path(folder)), \
                    patch.object(stats, "public_stats", return_value={
                        "stars": 10, "followers": 20, "repos": 30,
                        "per_repo": {},
                    }), \
                    patch.object(stats, "contribution_calendar",
                                 side_effect=RuntimeError("GitHub down")):
                with self.assertRaisesRegex(RuntimeError, "GitHub down"):
                    stats.main()
            self.assertEqual(json.loads(path.read_text()), {"previous": "valid"})

    def test_successful_refresh_updates_all_displayed_metrics(self):
        with tempfile.TemporaryDirectory() as folder:
            with patch.object(stats, "OUT", Path(folder)), \
                    patch.object(stats, "public_stats", return_value={
                        "stars": 51, "followers": 37, "repos": 44,
                        "per_repo": {"Gridline": {"stars": 17, "pushed": "2026-10-23", "license": "MIT"}},
                    }), \
                    patch.object(stats, "contribution_calendar", return_value=calendar()), \
                    patch("build_telemetry_panels.main_write") as writer:
                stats.main()
            data = json.loads((Path(folder) / "data.json").read_text())
            self.assertEqual((data["stars"], data["followers"], data["public_repos"]), (51, 37, 44))
            self.assertEqual(data["repos"]["Gridline"]["stars"], 17)
            self.assertEqual(data["summary"]["month"], 7)
            self.assertEqual(data["summary"]["current"], 2)
            self.assertEqual(len(data["calendar"]), 3)
            writer.assert_called_once()


if __name__ == "__main__":
    unittest.main()
