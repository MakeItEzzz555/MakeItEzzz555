import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from build_signal_panels import THEMES, outputs
from update_profile_stats import render, summary


def calendar(counts, start="2026-09-28"):
    import datetime as dt
    first = dt.date.fromisoformat(start)
    days = [{"date": (first + dt.timedelta(i)).isoformat(), "contributionCount": c, "weekday": i % 7}
            for i, c in enumerate(counts)]
    return {"totalContributions": sum(counts), "weeks": [{"contributionDays": days[i:i + 7]}
                                                          for i in range(0, len(days), 7)]}


class SignalPanelTests(unittest.TestCase):
    def test_committed_panels_match_generator(self):
        for rel, content in outputs().items():
            with self.subTest(rel=rel):
                self.assertEqual((ROOT / "assets" / "signal" / rel).read_text(encoding="utf-8"), content)

    def test_no_gradients_and_motion_respects_reduced_motion(self):
        for rel, content in outputs().items():
            with self.subTest(rel=rel):
                self.assertNotIn("Gradient", content)
                if "@keyframes" in content:
                    self.assertIn("prefers-reduced-motion:reduce", content)

    def test_summary_totals_and_streaks(self):
        # 28 Sep .. 21 Oct 2026; today (last day) empty does not break the streak.
        counts = [1, 1, 1, 0] + [2] * 19 + [0]
        s = summary(calendar(counts))
        self.assertEqual(s["today"], 0)
        self.assertEqual(s["month"], 38)  # 1-21 October
        self.assertEqual(s["year"], sum(counts))
        self.assertEqual(s["current"], 19)
        self.assertEqual(s["longest"], 19)

    def test_log_renders_for_both_themes(self):
        stats = {"stars": 65, "followers": 30, "repos": 40, "forks": 3}
        for theme in THEMES.values():
            self.assertIn("65", render(stats, calendar([3] * 10), theme))


if __name__ == "__main__":
    unittest.main()
