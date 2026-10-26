import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import build_telemetry_panels as panels
from update_profile_stats import summary
from validate_readme_images import validate


def calendar(counts, start="2026-09-28"):
    import datetime as dt
    first = dt.date.fromisoformat(start)
    days = [{"date": (first + dt.timedelta(i)).isoformat(), "contributionCount": c, "weekday": i % 7}
            for i, c in enumerate(counts)]
    return {"totalContributions": sum(counts),
            "weeks": [{"contributionDays": days[i:i + 7]} for i in range(0, len(days), 7)]}


class TelemetryPanelTests(unittest.TestCase):
    def test_flagships_order_and_readme_showcase(self):
        self.assertEqual([repo for repo, *_ in panels.FLAGSHIPS],
                         ["tuck-bit", "Gridline", "claude-widget-kit"])
        readme = (ROOT / "README.md").read_text(encoding="utf-8")
        tuck = readme.index("./assets/telemetry/sheet-tuck-bit.svg")
        gridline = readme.index("./assets/telemetry/sheet-Gridline.svg")
        claude = readme.index("./assets/telemetry/sheet-claude-widget-kit.svg")
        self.assertLess(tuck, gridline)
        self.assertLess(gridline, claude)
        self.assertIn("https://github.com/MakeItEzzz555/Gridline", readme)
        self.assertIn("\nhttps://github.com/user-attachments/assets/a397a1b3-0f50-4d00-948a-62c9537144d8\n", readme)  # bare line, so GitHub renders the player
        self.assertNotIn("sheet-codex-widget-kit.svg", readme)
        self.assertNotIn("assets/work/codex-kit.jpg", readme)

    def test_contribution_card_uses_dynamic_counts_and_repo_metadata(self):
        from xml.etree import ElementTree as ET

        def labels(svg):
            return [node.text for node in ET.fromstring(svg).iter()
                    if node.tag.endswith("text") and node.text]

        data = {
            "updated": "2026-10-23",
            "stars": 13,
            "followers": 3,
            "public_repos": 7,
            "summary": {
                "today": 2, "month": 11, "year": 101, "window": 211,
                "current": 4, "current_from": "2026-10-20",
                "longest": 6, "longest_from": "2026-10-08",
                "longest_to": "2026-10-13",
            },
            "calendar": [("2026-10-23", 2, 5)],
            "repos": {"Gridline": {"stars": 6, "pushed": "2026-10-23", "license": "MIT"}},
        }
        first = labels(panels.contributions(data))
        for field in ("13", "3", "7", "2", "11", "101", "211", "4 DAYS", "6 DAYS"):
            self.assertIn(field, first)
        card = labels(panels.project_sheet("Gridline", "Gridline",
                                          "AI skills for architecture, CAD and BIM.",
                                          "PYTHON / CAD / BIM", data))
        for field in ("6", "2026-10-23", "MIT"):
            self.assertIn(field, card)
        data["stars"] = 26
        data["followers"] = 5
        data["public_repos"] = 8
        data["summary"]["month"] = 20
        data["repos"]["Gridline"]["stars"] = 12
        second = labels(panels.contributions(data))
        self.assertIn("26", second)
        self.assertIn("5", second)
        self.assertIn("8", second)
        self.assertIn("20", second)
        self.assertNotEqual(first, second)
        self.assertIn("12", labels(panels.project_sheet(
            "Gridline", "Gridline", "AI skills for architecture, CAD and BIM.",
            "PYTHON / CAD / BIM", data)))

    def test_committed_panels_match_generator(self):
        for rel, content in panels.outputs().items():
            with self.subTest(rel=rel):
                self.assertEqual((panels.OUT / rel).read_text(encoding="utf-8"), content)

    def test_no_gradients_and_reduced_motion_everywhere(self):
        for rel, content in panels.outputs().items():
            with self.subTest(rel=rel):
                self.assertNotIn("Gradient", content)
                self.assertIn("prefers-reduced-motion:reduce", content)

    def test_globe_carries_every_technology(self):
        hero = panels.outputs()["hero.svg"]
        for slug, _, _ in panels.STACK:
            self.assertIn(f'href="#i-{slug}"', hero)

    def test_each_ripple_starts_on_a_different_node(self):
        edges, glows = panels.ripple_schedule(panels.sphere_points(len(panels.STACK)))
        ripple_starts = {k * panels.LOOP / panels.RIPPLES for k in range(panels.RIPPLES)}
        starts = [node for node, at in glows if at in ripple_starts]
        self.assertEqual(len(set(starts)), panels.RIPPLES)
        self.assertTrue(edges)

    def test_summary_totals_and_streak_ranges(self):
        # 28 Sep .. 21 Oct 2026; an empty today does not break the streak.
        counts = [1, 1, 1, 0] + [2] * 19 + [0]
        s = summary(calendar(counts))
        self.assertEqual((s["today"], s["month"], s["year"]), (0, 38, sum(counts)))
        self.assertEqual((s["current"], s["current_from"]), (19, "2026-10-02"))
        self.assertEqual((s["longest"], s["longest_from"], s["longest_to"]), (19, "2026-10-02", "2026-10-20"))

    def test_readme_validator_passes_offline(self):
        count, local, remote, svgs, problems = validate(ROOT, check_remote=False)
        self.assertEqual(problems, [])
        self.assertGreater(local, 0)


if __name__ == "__main__":
    unittest.main()
