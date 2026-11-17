import unittest

from scene_art import showcase_layout


class ShowcaseLayoutTests(unittest.TestCase):
    def test_layout_is_stable_for_same_placement(self):
        placed = {(row, col): "forest" for row in range(11)
                  for col in range(1 + min(row, 10 - row))}
        first = showcase_layout(placed)
        second = showcase_layout(placed)
        self.assertEqual(first, second)
        self.assertEqual(len(first), 36)

    def test_layout_is_compact_and_inside_panorama(self):
        placed = {(row, col): "core" for row in range(11)
                  for col in range(1 + min(row, 10 - row))}
        layout = showcase_layout(placed)
        xs = [position[0] for position in layout.values()]
        ys = [position[1] for position in layout.values()]
        self.assertGreaterEqual(min(xs), 100)
        self.assertLessEqual(max(xs), 1180)
        self.assertGreaterEqual(min(ys), 330)
        self.assertLessEqual(max(ys), 520)
        # The six-cell midline should use the compact cadence rather than the
        # old loose 176px spacing.
        middle = [layout[(5, column)][0] for column in range(6)]
        self.assertLess(max(middle) - min(middle), 800)

    def test_depth_gives_rear_rows_more_height(self):
        placed = {(0, 0): "gear", (10, 0): "gear"}
        layout = showcase_layout(placed)
        self.assertGreater(layout[(0, 0)][2], layout[(10, 0)][2])

    def test_tall_rear_landmark_stays_below_header(self):
        layout = showcase_layout({
            (0, 0): "observatory",
            (10, 0): "core",
        })
        # The logical showcase header ends at y=106; retain a visible gap.
        top = layout[(0, 0)][1] - layout[(0, 0)][2]
        self.assertGreaterEqual(top, 110)


if __name__ == "__main__":
    unittest.main()
