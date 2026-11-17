import unittest

import city_rules
import ending_text


class EndingTextTests(unittest.TestCase):
    def test_score_tier_boundaries(self):
        cases = (
            (0, 0), (59, 0), (60, 60), (69, 60), (70, 70), (79, 70),
            (80, 80), (89, 80), (90, 90), (99, 90), (100, 100),
        )
        for score, tier in cases:
            with self.subTest(score=score):
                self.assertEqual(ending_text.get_ending(score)["tier"], tier)

    def test_every_score_has_one_epilogue(self):
        for score in range(101):
            with self.subTest(score=score):
                result = ending_text.get_ending(score)
                self.assertEqual(set(result), {"tier", "title", "body", "style_line"})
                self.assertLessEqual(result["tier"], score)
                self.assertTrue(result["style_line"])

    def test_each_tier_has_unique_substantial_text(self):
        titles = [entry["title"] for entry in ending_text.ENDINGS]
        bodies = [entry["body"] for entry in ending_text.ENDINGS]
        self.assertEqual(len(set(titles)), 6)
        self.assertEqual(len(set(bodies)), 6)
        for entry in ending_text.ENDINGS:
            with self.subTest(tier=entry["tier"]):
                self.assertTrue(4 <= len(entry["title"]) <= 6)
                self.assertTrue(55 <= len(entry["body"]) <= 90)
                self.assertNotIn("：", entry["body"])
                self.assertNotIn("—", entry["body"])
                self.assertNotIn("不是", entry["body"])

    def test_existing_style_names_have_distinct_epilogues(self):
        self.assertEqual(set(ending_text.STYLE_LINES), set(city_rules.STYLE_NAMES))
        lines = {ending_text.get_ending(89, style)["style_line"] for style in city_rules.STYLE_NAMES}
        self.assertEqual(len(lines), 4)

    def test_unknown_style_falls_back_to_hybrid(self):
        self.assertEqual(ending_text.get_ending(89, "unknown"), ending_text.get_ending(89, "hybrid"))

    def test_returned_data_does_not_mutate_the_original(self):
        result = ending_text.get_ending(100)
        result["title"] = "changed"
        self.assertEqual(ending_text.get_ending(100)["title"], "云上之城")

    def test_invalid_scores_are_rejected(self):
        for score in (-1, 101):
            with self.subTest(score=score), self.assertRaises(ValueError):
                ending_text.get_ending(score)
        for score in (True, 90.5, "90", None):
            with self.subTest(score=score), self.assertRaises(TypeError):
                ending_text.get_ending(score)


if __name__ == "__main__":
    unittest.main()
