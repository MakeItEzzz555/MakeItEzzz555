import sys
import unittest
from pathlib import Path
from urllib.parse import urlsplit
from xml.etree import ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from build_animated_icons import catalog, generate
from validate_readme_images import Images, validate

NAMESPACE = "{http://www.w3.org/2000/svg}"

class AnimatedTechnologyIconTests(unittest.TestCase):
    def test_generated_files_match_committed_sources(self):
        for name in catalog():
            with self.subTest(name=name):
                path = ROOT / "assets" / "icons" / "animated" / (name + ".svg")
                self.assertEqual(path.read_bytes(), generate(name))

    def test_original_brand_shapes_and_green_accent_preserved(self):
        for name in catalog():
            with self.subTest(name=name):
                base = ET.parse(ROOT / "assets" / "icons" / (name + ".svg")).getroot()
                moving = ET.fromstring(generate(name))
                self.assertEqual(base.get("fill"), "#7DFFB4")
                self.assertEqual(moving.get("fill"), base.get("fill"))
                before = [(p.tag, sorted(p.attrib.items())) for p in base.iter()
                          if p.tag == NAMESPACE + "path"]
                after = [(p.tag, sorted(p.attrib.items())) for p in moving.iter()
                         if p.tag == NAMESPACE + "path"]
                self.assertEqual(before, after)
                self.assertTrue(after)

    def test_smil_animations_are_self_contained_and_nonblocking(self):
        for name in catalog():
            with self.subTest(name=name):
                root = ET.fromstring(generate(name))
                animations = [item for item in root.iter() if item.tag in
                              (NAMESPACE + "animate", NAMESPACE + "animateTransform")]
                self.assertEqual(len(animations), 1)
                motion = animations[0]
                self.assertEqual(motion.get("repeatCount"), "indefinite")
                self.assertTrue(motion.get("begin", "").startswith("-"))
                self.assertNotIn("0;0;0", motion.get("values", ""))
                self.assertLess(len(generate(name)), 20000)
                self.assertFalse(any(p.tag == NAMESPACE + "script" for p in root.iter()))
                self.assertFalse(any(p.tag == NAMESPACE + "style" for p in root.iter()))
                self.assertEqual(motion.get("attributeName"), "transform")
                self.assertNotIn("opacity", motion.attrib.values())

    def test_readme_has_static_reduced_motion_for_all_animated_icons(self):
        parser = Images()
        parser.feed((ROOT / "README.md").read_text(encoding="utf-8"))
        total = 0
        seen_names = set()
        for picture in parser.pictures:
            if picture["sources"][0].get("media") == "(prefers-color-scheme: dark)":
                continue
            self.assertEqual(len(picture["sources"]), 1)
            self.assertEqual(len(picture["images"]), 1)
            src, alt = picture["images"][0]
            source = picture["sources"][0]
            name = Path(urlsplit(src).path).stem
            seen_names.add(name)
            self.assertIn(name, catalog())
            self.assertTrue(alt)
            self.assertEqual(source["media"], "(prefers-reduced-motion: reduce)")
            self.assertEqual(source["srcset"], "./assets/icons/" + name + ".svg")
            total += 1
        self.assertLessEqual(seen_names, set(catalog()))
        self.assertEqual(total, 28)
        self.assertEqual(len(catalog()), 31)

    def test_full_readme_validator_passes_offline(self):
        count, local, remote, svgs, problems = validate(ROOT, check_remote=False)
        self.assertEqual(problems, [])
        self.assertGreater(count, 0)
        self.assertGreaterEqual(svgs, 31)
        self.assertEqual(local + remote, count)

if __name__ == "__main__":
    unittest.main()
