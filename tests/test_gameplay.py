import unittest

import game


class GameplayRegressionTests(unittest.TestCase):
    """Black-box-ish gameplay tests using the same click/settle path as play."""

    def new_game(self):
        # reset() contains the model state and does not require a display.  This
        # keeps the suite usable in CI while still exercising click_cell().
        city = game.SkyCity.__new__(game.SkyCity)
        city.reset()
        city.tutorial_step = None
        return city

    def place(self, city, kind, cell=None):
        if cell is None:
            cells = sorted(city.valid_cells(kind))
            self.assertTrue(cells, self.state(city, f"no legal cell for {kind}"))
            cell = cells[0]
        self.assertIn(cell, game.CELLS)
        self.assertIn(
            cell,
            city.valid_cells(kind),
            self.state(city, f"{kind} cannot be placed at {cell}"),
        )
        city.selected = kind
        city.click_cell(game.cell_center(cell))
        if len(city.placed) == len(game.CELLS):
            self.assertFalse(city.finished, "the last tile must settle before the ending")
            self.assertFalse(city.result_visible)
        city.update(2.0)
        self.assertEqual(city.placed.get(cell), kind)
        self.assertFalse(city.pending, self.state(city, f"{kind} did not settle"))
        return cell

    @staticmethod
    def state(city, prefix="state"):
        return (
            f"{prefix}: placed={len(city.placed)}, active={len(city.active)}, "
            f"resources={dict(city.resources)}, fragments={city.fragments}, "
            f"expansions={city.expansions}, unlocked={city.unlocked}"
        )

    def place_best(self, city, kind, prefer=None):
        candidates = list(city.valid_cells(kind))
        self.assertTrue(candidates, self.state(city, f"no legal cell for {kind}"))
        preferred = set(prefer or ())

        def rank(cell):
            nearby = {
                city.placed[n]
                for n in game.neighbors(cell)
                if n in city.placed
            }
            # Natural buildings are deliberately put beside water/forest.  The
            # resulting route is deterministic but still uses real cell rules.
            if kind == "forest":
                return (0 if nearby & {"cloud", "waterfall"} else 1, cell)
            if kind == "garden":
                return (0 if "forest" in nearby else 1, cell)
            if cell in preferred:
                return (-1, cell)
            return (0, cell)

        return self.place(city, kind, min(candidates, key=rank))

    def bootstrap(self, city):
        self.place(city, "core", (5, 2))
        self.place_best(city, "cloud")
        self.place_best(city, "wind")

    def grow_natural(self, city):
        """Advance with only cloud/waterfall/forest/garden after bootstrap."""
        natural = ("cloud", "waterfall", "forest", "garden")
        for _ in range(180):
            if len(city.placed) == len(game.CELLS):
                return

            # Research is a player action, not a resource cheat.  Only research
            # a node once its ordinary fragment balance and parent are available.
            for kind in ("waterfall", "forest", "garden"):
                if kind in game.TECH_TREE and kind not in city.unlocked:
                    city.research(kind)

            if city.can_expand():
                previous_expansions = city.expansions
                before_structure = city.resources["structure"]
                before_resonance = city.resources["resonance"]
                self.assertTrue(city.expand(), self.state(city, "expand failed"))
                self.assertEqual(city.resources["structure"], before_structure - 4)
                self.assertEqual(
                    city.resources["resonance"],
                    before_resonance - (3 if previous_expansions == 1 else 0),
                )
                continue

            candidates = []
            for kind in natural:
                if kind not in city.unlocked or not city.can_pay(kind):
                    continue
                legal = list(city.valid_cells(kind))
                for cell in legal:
                    nearby = {
                        city.placed[n]
                        for n in game.neighbors(cell)
                        if n in city.placed
                    }
                    priority = 0
                    if kind == "forest" and not nearby & {"cloud", "waterfall"}:
                        priority += 20
                    elif kind == "forest":
                        priority -= 6
                    if kind == "garden" and "forest" not in nearby:
                        priority += 20
                    elif kind == "garden" and city.placed_count("garden") == 0:
                        priority -= 7
                    if kind == "cloud" and city.resources["vapor"] < 2:
                        priority -= 10
                    if kind == "waterfall" and city.resources["vapor"] < 4:
                        priority -= 8 if "cloud" in nearby else 7
                    candidates.append((priority, kind, cell))
            if not candidates:
                self.fail(self.state(city, "natural route stalled"))
            _, kind, cell = min(candidates, key=lambda item: (item[0], item[1], item[2]))
            self.place(city, kind, cell)

        self.fail(self.state(city, "natural route exceeded placement budget"))

    def grow_industrial(self, city, stop_at=None):
        """Use energy for structure and bridge resonance, without nature tech."""
        target = len(game.CELLS) if stop_at is None else stop_at
        available = ("cloud", "wind", "sundial", "gear", "bridge", "harbor")
        for _ in range(180):
            if len(city.placed) >= target:
                return
            for kind in ("sundial", "gear", "bridge", "harbor"):
                if kind not in city.unlocked:
                    city.research(kind)

            # Keep one structure in reserve after expansion.  Unlike the water
            # branch, this route needs starter clouds to replenish vapor.
            if city.can_expand() and city.resources["structure"] >= 5:
                before_structure = city.resources["structure"]
                before_resonance = city.resources["resonance"]
                previous_expansions = city.expansions
                self.assertTrue(city.expand())
                self.assertEqual(city.resources["structure"], before_structure - 4)
                self.assertEqual(
                    city.resources["resonance"],
                    before_resonance - (3 if previous_expansions == 1 else 0),
                )
                continue

            candidates = []
            for kind in available:
                for cell in city.valid_cells(kind):
                    nearby = {
                        city.placed[n]
                        for n in game.neighbors(cell)
                        if n in city.placed
                    }
                    priority = {
                        "cloud": -10 if city.resources["vapor"] < 2 else 4,
                        "wind": -9 if city.resources["light"] < 1 else 3,
                        "sundial": -8 if city.resources["light"] < 4 else 2,
                        "gear": -7 if city.resources["structure"] < 8 else 4,
                        "bridge": -6 if city.resources["resonance"] < 3 else 3,
                        "harbor": -5 if city.placed_count("harbor") == 0 else 4,
                    }[kind]
                    synergy = sum(
                        frozenset((kind, other)) in game.SYNERGY_PAIRS
                        for other in nearby
                    )
                    candidates.append((priority, -synergy, kind, cell))
            if not candidates:
                self.fail(self.state(city, "industrial route stalled"))
            _, _, kind, cell = min(candidates)
            self.place(city, kind, cell)

        self.fail(self.state(city, "industrial route exceeded placement budget"))

    def test_tech_tree_has_prerequisites_and_allows_both_branches(self):
        city = self.new_game()
        self.assertFalse(city.research("forest"))
        self.assertFalse(city.research("sundial"))

        self.bootstrap(city)
        # A third starter tile supplies enough inspiration for the first node.
        self.place_best(city, "cloud")
        before_fragments = city.fragments
        self.assertTrue(city.research("waterfall"), self.state(city, "waterfall locked"))
        self.assertEqual(city.fragments, before_fragments - game.TECH_TREE["waterfall"]["cost"])
        self.assertIn("waterfall", city.hand)
        before_fragments = city.fragments
        self.assertFalse(city.research("waterfall"), "duplicate research must not spend inspiration")
        self.assertEqual(city.fragments, before_fragments)
        self.assertFalse(city.research("forest"), self.state(city, "forest ignored its cost"))
        self.assertEqual(city.fragments, before_fragments)

        # Add a wind branch and enough ordinary settlements for both research
        # costs.  No fragment/resource values are injected by the test.
        for _ in range(6):
            if city.resources["vapor"] and city.valid_cells("wind"):
                self.place_best(city, "wind")
            elif city.valid_cells("cloud"):
                self.place_best(city, "cloud")
            else:
                break
        self.assertTrue(city.research("sundial"), self.state(city, "sundial unavailable"))
        self.assertIn("waterfall", city.unlocked)
        self.assertIn("sundial", city.unlocked)
        self.assertTrue(city.research("forest") or "forest" in city.unlocked)

    def test_expansion_is_strict_and_second_expansion_consumes_resonance(self):
        city = self.new_game()
        self.bootstrap(city)
        self.assertFalse(city.can_expand(), self.state(city, "expanded before six tiles"))
        self.place_best(city, "cloud")
        self.place_best(city, "wind")
        self.assertEqual(city.resources["structure"], 4)
        self.assertFalse(city.expand(), "structure alone must not bypass the six-tile gate")
        self.place_best(city, "cloud")
        self.assertTrue(city.can_expand(), self.state(city, "first expansion never became legal"))
        self.assertTrue(city.expand())
        self.assertEqual(city.expansions, 1)
        self.assertEqual(len(city.active), 26)

        # A second expansion cannot be bought with structure alone; the
        # resonance and research/count checks remain visible in the checklist.
        before = dict(city.resources)
        self.assertFalse(city.can_expand(), self.state(city, "second expansion bypassed gates"))
        self.assertEqual(city.resources["resonance"], before.get("resonance", 0))

    def test_natural_route_fills_board_and_ends_with_score(self):
        city = self.new_game()
        self.bootstrap(city)
        self.grow_natural(city)
        self.assertEqual(len(city.placed), len(game.CELLS), self.state(city))
        self.assertEqual(city.expansions, 2, self.state(city, "natural route did not expand twice"))
        self.assertTrue({"cloud", "waterfall", "forest", "garden"} <= set(city.placed.values()))
        self.assertFalse({"gear", "harbor", "bridge"} & set(city.placed.values()))
        self.assertFalse({"sundial", "gear", "harbor", "bridge"} & set(city.unlocked))
        self.assertTrue(city.finished)
        self.assertTrue(city.result_visible)
        self.assertGreater(city.score, 0)
        self.assertEqual(sum(city.score_breakdown.values()), city.score)
        self.assertLessEqual(city.score, 100)

    def test_finished_city_cannot_be_modified(self):
        city = self.new_game()
        city.finished = True
        city.result_visible = True
        snapshot = (dict(city.placed), dict(city.resources), city.fragments, city.expansions)
        city.selected = "cloud"
        city.click_cell(game.cell_center((5, 2)))
        city.dismantle_at(game.cell_center((5, 2)))
        self.assertEqual(snapshot, (dict(city.placed), dict(city.resources), city.fragments, city.expansions))
        self.assertFalse(city.research("waterfall"))
        self.assertFalse(city.expand())

    def test_industrial_route_fills_board_without_natural_technology(self):
        city = self.new_game()
        self.bootstrap(city)
        self.grow_industrial(city)
        self.assertEqual(len(city.placed), len(game.CELLS), self.state(city))
        self.assertEqual(city.expansions, 2, self.state(city))
        self.assertTrue({"sundial", "gear", "bridge", "harbor"} <= set(city.placed.values()))
        self.assertFalse({"waterfall", "forest", "garden"} & set(city.unlocked))
        self.assertTrue(city.finished)
        self.assertTrue(city.result_visible)
        self.assertEqual(city.score, sum(city.score_breakdown.values()))
        self.assertTrue(0 < city.score <= 100)

    def test_last_pending_build_delays_ending_and_score(self):
        city = self.new_game()
        self.bootstrap(city)
        self.grow_industrial(city, stop_at=35)
        cell = next(c for c in game.CELLS if c not in city.placed)
        self.assertIn(cell, city.valid_cells("sundial"), self.state(city))
        city.selected = "sundial"
        city.click_cell(game.cell_center(cell))
        self.assertEqual(len(city.placed), 36)
        self.assertTrue(city.pending)
        city.update(1.0)
        self.assertFalse(city.finished)
        self.assertFalse(city.result_visible)
        self.assertEqual(city.score, 0)
        self.assertEqual(city.score_breakdown, {})
        city.update(1.0)
        self.assertFalse(city.pending)
        self.assertTrue(city.finished)
        self.assertGreater(city.score, 0)

    def test_observatory_requires_branch_and_second_expansion(self):
        city = self.new_game()
        self.bootstrap(city)
        self.assertFalse(city.research("observatory"))
        self.assertIn("前置", city.tech_missing("observatory"))
        self.grow_industrial(city, stop_at=14)
        self.assertIn("harbor", city.unlocked, self.state(city))
        self.assertEqual(city.expansions, 1)
        before_fragments = city.fragments
        self.assertFalse(city.research("observatory"))
        self.assertIn("第二圈", city.tech_missing("observatory"))
        self.assertEqual(city.fragments, before_fragments)
        self.grow_industrial(city, stop_at=25)
        self.assertEqual(city.expansions, 2)
        self.assertTrue(city.can_research("observatory"), self.state(city))
        before_fragments = city.fragments
        self.assertTrue(city.research("observatory"))
        self.assertEqual(city.fragments, before_fragments - game.TECH_TREE["observatory"]["cost"])

    def test_unknown_technology_key_is_rejected_without_mutation(self):
        city = self.new_game()
        before = (city.fragments, list(city.unlocked), list(city.hand))
        self.assertFalse(city.can_research("not_a_building"))
        self.assertFalse(city.research("not_a_building"))
        self.assertEqual(before, (city.fragments, city.unlocked, city.hand))

    def test_rebuilding_same_cell_does_not_farm_settlement_or_fragments(self):
        city = self.new_game()
        self.bootstrap(city)
        cell = next(iter(city.placed))
        # Never dismantle the core; choose a settled starter building.
        if city.placed[cell] == "core":
            cell = next(c for c, kind in city.placed.items() if kind != "core")
        kind = city.placed[cell]
        fragments = city.fragments
        resources = dict(city.resources)
        settled = set(city.settled_builds)
        city.dismantle_at(game.cell_center(cell))
        self.place(city, kind, cell)
        self.assertEqual(city.fragments, fragments)
        self.assertTrue(settled <= set(city.settled_builds))
        for name, value in resources.items():
            self.assertLessEqual(city.resources[name], value, self.state(city, "rebuild farmed resources"))

    def test_unsettled_demolition_refunds_cost_and_cancels_reward(self):
        city = self.new_game()
        self.place(city, "core", (5, 2))
        cell = sorted(city.valid_cells("cloud"))[0]
        before_resources = dict(city.resources)
        before_fragments = city.fragments
        city.selected = "cloud"
        city.click_cell(game.cell_center(cell))
        self.assertTrue(city.pending)
        city.dismantle_at(game.cell_center(cell))
        self.assertFalse(city.pending)
        city.update(2.0)
        self.assertNotIn(cell, city.placed)
        self.assertEqual(dict(city.resources), before_resources)
        self.assertEqual(city.fragments, before_fragments)
        self.assertNotIn(cell, city.inspired_cells)
        self.place(city, "cloud", cell)
        self.assertEqual(city.fragments, before_fragments + 1)

    def test_supply_is_paged_in_groups_of_three(self):
        city = self.new_game()
        # This is a catalog-model test; research tests above cover actual costs.
        city.unlocked = ["cloud", "core", "wind", "waterfall", "forest", "garden", "sundial"]
        city.refill_hand()
        self.assertEqual(len(city.visible_hand()), 3)
        pages = (len(city.hand) + 2) // 3
        self.assertGreaterEqual(pages, 2)
        city.supply_page = 1
        self.assertEqual(len(city.visible_hand()), 3)
        self.assertNotEqual(city.visible_hand(), city.hand[:3])
        catalog = []
        for page in range(pages):
            city.supply_page = page
            self.assertLessEqual(len(city.visible_hand()), 3)
            catalog.extend(city.visible_hand())
        self.assertEqual(catalog, city.hand)
        city.supply_page = 999
        city.refill_hand()
        self.assertEqual(city.supply_page, pages - 1)
        self.place(city, "core", (5, 2))
        self.assertNotIn("core", city.hand)
        self.assertEqual(city.valid_cells("core"), [])


if __name__ == "__main__":
    unittest.main()
