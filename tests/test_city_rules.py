import unittest

import city_rules as rules


CELLS = [(row, col) for row in range(11) for col in range(1 + min(row, 10 - row))]


def neighbors(cell):
    row, col = cell
    candidates = [(row, col - 1), (row, col + 1)]
    if row < 5:
        candidates.extend(((row - 1, col - 1), (row - 1, col), (row + 1, col), (row + 1, col + 1)))
    elif row > 5:
        candidates.extend(((row - 1, col), (row - 1, col + 1), (row + 1, col - 1), (row + 1, col)))
    else:
        candidates.extend(((row - 1, col - 1), (row - 1, col), (row + 1, col - 1), (row + 1, col)))
    return [candidate for candidate in candidates if candidate in CELLS]


class CityRulesTests(unittest.TestCase):
    def test_zones_are_valid_and_can_overlap(self):
        self.assertEqual(rules.zones_for((0, 0)), ("high", "edge"))
        self.assertEqual(rules.zones_for((3, 1)), ("high",))
        self.assertEqual(rules.zones_for((5, 0)), ("edge",))
        self.assertEqual(rules.zones_for((5, 2)), ("center",))
        self.assertEqual(rules.zones_for((7, 1)), ())
        for invalid in ((-1, 0), (11, 0), (3, 4), (4, -1)):
            self.assertEqual(rules.zones_for(invalid), ())

    def test_position_bonuses_require_matching_kind_and_slot(self):
        cases = (
            ((2, 1), "wind", {"light": 1}),
            ((2, 0), "observatory", {"light": 1}),
            ((5, 0), "cloud", {"vapor": 1}),
            ((5, 5), "waterfall", {"vapor": 1}),
            ((8, 2), "harbor", {"structure": 1}),
            ((8, 0), "bridge", {"structure": 1}),
            ((4, 2), "forest", {"resonance": 1}),
            ((6, 1), "garden", {"resonance": 1}),
            ((5, 3), "residents", {"resonance": 1}),
            ((5, 2), "wind", {}),
            ((5, 0), "forest", {}),
            ((0, 0), "core", {}),
        )
        for cell, kind, bonus in cases:
            with self.subTest(cell=cell, kind=kind):
                self.assertEqual(rules.position_bonus(cell, kind), bonus)
                self.assertIsInstance(rules.position_description(kind), str)

    def test_grove_counts_forests_not_water_neighbors_and_is_capped(self):
        placed = {(5, 0): "cloud", (5, 1): "forest", (4, 0): "waterfall", (4, 1): "forest", (6, 1): "forest"}
        self.assertEqual(rules.task_progress("grove", placed, set(placed), neighbors), 2)
        self.assertEqual(rules.task_progress("grove", placed, {(5, 1), (4, 1)}, neighbors), 0)

    def test_spring_grove_combination_requires_all_three_connected_parts(self):
        placed = {(5, 0): "cloud", (4, 0): "waterfall", (5, 1): "forest"}
        matches = rules.find_combinations(placed, set(placed), neighbors)
        self.assertEqual(matches["spring_grove"], ((5, 0), (4, 0), (5, 1)))
        self.assertNotIn("spring_grove", rules.find_combinations(placed, {(5, 0), (5, 1)}, neighbors))
        self.assertNotIn("spring_grove", rules.find_combinations(
            {(5, 0): "cloud", (4, 0): "waterfall"}, {(5, 0), (4, 0)}, neighbors))

    def test_bridge_hamlet_requires_two_distinct_neighbors(self):
        placed = {(5, 1): "bridge", (5, 0): "garden", (4, 1): "residents"}
        self.assertEqual(rules.find_combinations(placed, set(placed), neighbors)["bridge_hamlet"],
                         ((5, 1), (5, 0), (4, 1)))

    def test_skyline_requires_high_connected_buildings(self):
        placed = {(2, 0): "wind", (3, 1): "sundial", (5, 0): "wind", (1, 1): "observatory"}
        self.assertEqual(rules.task_progress("skyline", placed, set(placed), neighbors), 2)
        self.assertEqual(rules.task_progress("skyline", placed, {(5, 0)}, neighbors), 0)

    def test_district_is_distinct_and_capped(self):
        placed = {(5, i): kind for i, kind in enumerate(("core", "cloud", "wind", "forest", "garden", "waterfall"))}
        self.assertEqual(rules.task_progress("district", placed, set(placed), neighbors), 5)
        self.assertEqual(rules.task_progress("district", placed, {(5, 0), (5, 1)}, neighbors), 2)
        with self.assertRaises(ValueError):
            rules.task_progress("missing", placed, set(placed), neighbors)

    def test_each_route_can_reach_maximum_without_other_styles(self):
        layouts = {
            "natural": {(5, 0): "cloud", (4, 0): "waterfall", (5, 1): "forest", (4, 1): "garden"},
            "industrial": {(2, 0): "wind", (2, 1): "sundial", (3, 0): "gear", (3, 1): "harbor", (3, 3): "bridge"},
            "living": {(5, 1): "forest", (5, 2): "garden", (4, 1): "residents", (4, 0): "bridge"},
        }
        for style, placed in layouts.items():
            with self.subTest(style=style):
                scores = rules.style_scores(placed, set(placed), neighbors)
                self.assertEqual(scores[style], 15)
                self.assertEqual(rules.dominant_style(scores), style)

    def test_building_spam_cannot_replace_complementary_layout(self):
        placed = {cell: "forest" for cell in CELLS}
        scores = rules.style_scores(placed, set(placed), neighbors)
        self.assertEqual(scores["natural"], 5)
        self.assertEqual(scores["living"], 5)
        self.assertEqual(scores["industrial"], 0)
        self.assertEqual(rules.dominant_style(scores), "hybrid")

    def test_disconnected_structures_do_not_affect_scores(self):
        placed = {(5, 0): "cloud", (4, 0): "waterfall", (5, 1): "forest", (4, 1): "garden"}
        self.assertEqual(rules.style_scores(placed, set(), neighbors), dict.fromkeys(rules.STYLES, 0))
        scores = rules.style_scores(placed, {(5, 1)}, neighbors)
        self.assertEqual(scores["natural"], 3)
        self.assertEqual(scores["living"], 3)

    def test_edges_count_once_and_formula_is_exact(self):
        placed = {(5, 0): "cloud", (5, 1): "forest"}
        # Two kinds: 3; one complementary edge: 2; two suitable positions: 2.
        self.assertEqual(rules.style_scores(placed, set(placed), neighbors)["natural"], 7)
        self.assertEqual(rules.style_scores(placed, set(placed), neighbors), rules.style_scores(dict(reversed(list(placed.items()))), set(placed), neighbors))

    def test_scores_are_capped_and_empty_city_is_hybrid(self):
        kinds = tuple(sorted({kind for group in rules._STYLE_KINDS.values() for kind in group}))
        placed = {cell: kinds[index % len(kinds)] for index, cell in enumerate(CELLS)}
        for score in rules.style_scores(placed, set(placed), neighbors).values():
            self.assertIsInstance(score, int)
            self.assertTrue(0 <= score <= 15)
        self.assertEqual(rules.dominant_style({}), "hybrid")
        self.assertEqual(rules.dominant_style({"natural": 4, "industrial": 4, "living": 1}), "hybrid")
        self.assertEqual(rules.dominant_style({"natural": 0, "industrial": 0, "living": 0}), "hybrid")


if __name__ == "__main__":
    unittest.main()
