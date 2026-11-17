import unittest

import game


class NaturalRouteGameplayTests(unittest.TestCase):
    """Regression tests for a resource-sustainable, no-industry natural route."""

    def new_game(self):
        city = game.SkyCity.__new__(game.SkyCity)
        city.reset()
        city.tutorial_step = None
        return city

    def place(self, city, kind, cell):
        self.assertIn(cell, game.CELLS)
        city.selected = kind
        self.assertIn(
            cell,
            city.valid_cells(kind),
            f"{kind} cannot be placed at {cell}; resources={dict(city.resources)}",
        )
        city.click_cell(game.cell_center(cell))
        if len(city.placed) == len(game.CELLS):
            self.assertFalse(city.finished)
            self.assertTrue(city.pending)
        city.update(1.9)
        self.assertEqual(city.placed.get(cell), kind)

    def place_first_available(self, city, kind, preferred=None):
        candidates = []
        if preferred:
            candidates.extend(preferred)
        candidates.extend(sorted(city.valid_cells(kind)))
        for cell in candidates:
            if cell in city.valid_cells(kind):
                self.place(city, kind, cell)
                return cell
        self.fail(f"no legal cell for {kind}; resources={dict(city.resources)}")

    def test_natural_route_can_research_and_expand_without_industry(self):
        city = self.new_game()

        # Core and the starter resource loop.
        self.place(city, "core", (5, 2))
        self.place(city, "cloud", (5, 1))
        self.place(city, "wind", (4, 1))

        # Natural technology branch: no sundial, gear, bridge, harbor or other
        # industrial/energy branch is researched or placed.
        self.assertTrue(city.research("waterfall"))
        self.place(city, "cloud", (4, 2))
        self.place(city, "waterfall", (4, 0))
        self.place(city, "cloud", (5, 0))
        self.assertTrue(city.research("forest"))
        self.place(city, "forest", (3, 1))

        # Keep a water/forest adjacency so the forest structure bonus funds the
        # first expansion. Prefer the active central ring for deterministic layout.
        self.assertTrue(city.can_expand(), city.expansion_requirements())
        city.expand()
        self.assertEqual(city.expansions, 1)
        self.assertEqual(len(city.active), 26)

        # A second natural cluster supplies resonance while keeping the route
        # free of industrial buildings.
        self.place_first_available(city, "forest", preferred=[(6, 0), (6, 1), (3, 0)])
        self.place_first_available(city, "cloud", preferred=[(3, 0), (6, 0), (2, 0)])
        if city.resources["vapor"] < 2:
            self.place_first_available(city, "cloud")
        # Garden is the final natural tech node and is usable after forest.
        self.assertTrue(city.research("garden"))
        self.place_first_available(city, "garden")

        # Fill every newly opened cell with the natural supply. The test allows
        # any natural card order, but never injects resources or removes tiles.
        natural = ("forest", "garden", "waterfall", "cloud")
        while len(city.placed) < len(game.CELLS):
            progressed = False
            # Maintain water for growth and resonance for the second ring;
            # prefer productive natural conversions when they are affordable.
            choices = ("cloud",) if city.resources["vapor"] < 2 else natural
            for kind in choices:
                cells = city.valid_cells(kind)
                if cells:
                    def quality(cell):
                        nearby = {city.placed[n] for n in game.neighbors(cell) if n in city.placed}
                        synergy = sum(frozenset((kind, other)) in game.SYNERGY_PAIRS for other in nearby)
                        return (-synergy, cell)
                    self.place(city, kind, sorted(cells, key=quality)[0])
                    progressed = True
                    break
            if not progressed:
                self.fail(
                    f"natural route stalled at {len(city.placed)}/{len(game.CELLS)}; "
                    f"resources={dict(city.resources)}, expansions={city.expansions}, "
                    f"unlocked={city.unlocked}"
                )
            if city.expansions == 1 and len(city.placed) >= 14 and city.can_expand():
                city.expand()
                self.assertEqual(city.expansions, 2)
                self.assertEqual(len(city.active), 36)

        self.assertEqual(len(city.placed), 36)
        self.assertTrue({"cloud", "waterfall", "forest", "garden"} <= set(city.placed.values()))
        self.assertFalse({"gear", "sundial", "harbor"} & set(city.placed.values()))
        self.assertTrue(city.finished)
        self.assertTrue(city.result_visible)
        self.assertGreater(city.score, 0)
        self.assertLessEqual(city.score, 100)
        self.assertEqual(sum(city.score_breakdown.values()), city.score)
        final_layout = dict(city.placed)
        final_resources = dict(city.resources)
        final_score = city.score
        city.dismantle_at(game.cell_center((5, 1)))
        self.assertFalse(city.research("sundial"))
        self.assertFalse(city.can_expand())
        city.update(10.0)
        self.assertEqual(city.placed, final_layout)
        self.assertEqual(dict(city.resources), final_resources)
        self.assertEqual(city.score, final_score)

    def test_natural_tech_prerequisites_and_terminal_state(self):
        city = self.new_game()
        self.assertFalse(city.research("forest"))
        self.assertFalse(city.research("garden"))
        self.assertFalse(city.research("waterfall"))

        self.place(city, "core", (5, 2))
        self.place(city, "cloud", (5, 1))
        self.place(city, "wind", (4, 1))
        self.assertTrue(city.research("waterfall"))
        self.assertFalse(city.research("garden"))

        city.finished = True
        city.result_visible = True
        self.assertFalse(city.research("forest"))
        self.assertFalse(city.can_expand())
        self.assertEqual(city.valid_cells("cloud"), [])

    def test_same_cell_rebuild_cannot_repeat_resources_or_inspiration(self):
        city = self.new_game()
        self.place(city, "core", (5, 2))
        self.place(city, "cloud", (5, 1))
        fragments = city.fragments
        resources = dict(city.resources)
        city.dismantle_at(game.cell_center((5, 1)))
        self.place(city, "cloud", (5, 1))
        self.assertEqual(city.fragments, fragments)
        self.assertEqual(city.resources["vapor"], resources["vapor"])
        self.assertEqual(city.resources["structure"], resources["structure"] - 1)

    def test_first_two_researches_can_choose_both_branches_in_either_order(self):
        for first, second in (("waterfall", "sundial"), ("sundial", "waterfall")):
            with self.subTest(first=first, second=second):
                city = self.new_game()
                self.place(city, "core", (5, 2))
                self.place(city, "cloud", (5, 1))
                self.place(city, "wind", (4, 1))
                self.assertTrue(city.research(first))
                self.assertEqual(city.fragments, 0)
                if first == "waterfall":
                    self.place(city, "cloud", (4, 2))
                    self.place(city, "waterfall", (4, 0))
                else:
                    self.place(city, "sundial", (4, 2))
                    self.place(city, "cloud", (4, 0))
                self.assertTrue(city.research(second))
                self.assertIn("waterfall", city.unlocked)
                self.assertIn("sundial", city.unlocked)
                self.assertFalse(city.research(first))


if __name__ == "__main__":
    unittest.main()
