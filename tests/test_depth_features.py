import unittest

import pygame

import city_rules
import game


class DepthFeatureRegressionTests(unittest.TestCase):
    """Integration checks for action-based spatial decisions and recovery."""

    def new_game(self):
        city = game.SkyCity.__new__(game.SkyCity)
        city.reset()
        city.tutorial_step = None
        city.running = True
        city.logical_pos = lambda pos: pos
        return city

    def start_placement(self, city, kind, cell):
        self.assertIn(cell, city.valid_cells(kind), (kind, cell, dict(city.resources)))
        city.selected = kind
        city.click_cell(game.cell_center(cell))
        self.assertEqual(city.placed.get(cell), kind)
        self.assertTrue(any(item["cell"] == cell for item in city.pending))

    def place(self, city, kind, cell):
        self.start_placement(city, kind, cell)
        city.update(2.0)
        self.assertFalse(city.pending)

    @staticmethod
    def resources(city):
        return {name: city.resources.get(name, 0) for name in game.RESOURCE_NAMES}

    def snapshot(self, city):
        return (
            dict(city.placed), self.resources(city), city.fragments,
            list(city.pending), dict(city.placed_variants), dict(city.placed_jitter),
        )

    def bootstrap(self, city):
        self.place(city, "core", (5, 2))
        self.place(city, "cloud", (5, 1))
        self.place(city, "wind", (4, 1))

    def unlock_forest_with_real_actions(self, city):
        self.bootstrap(city)
        self.assertTrue(city.research("waterfall"))
        self.place(city, "cloud", (4, 2))
        self.place(city, "waterfall", (4, 0))
        self.place(city, "cloud", (5, 0))
        self.assertTrue(city.research("forest"))

    @staticmethod
    def progress(city, task_id):
        return next(progress for task, progress in city.city_tasks() if task["id"] == task_id)

    def test_reward_combines_position_and_functional_adjacency(self):
        cases = (
            ((3, 1), "wind", {(4, 1): "sundial"}, {"light": 3}, True),
            ((5, 1), "forest", {(5, 0): "cloud"}, {"resonance": 2, "structure": 2}, True),
            ((5, 0), "cloud", {}, {"vapor": 2}, False),
            ((8, 0), "bridge", {(8, 1): "harbor"}, {"structure": 3, "resonance": 1, "light": 1}, True),
        )
        for cell, kind, placed, expected, expected_synergy in cases:
            with self.subTest(cell=cell, kind=kind):
                city = self.new_game()
                city.placed = placed
                reward, synergy = city.reward_for(cell, kind)
                self.assertEqual(reward, expected)
                self.assertEqual(synergy, expected_synergy)

    def test_high_slot_bonus_is_received_after_actual_settlement_only(self):
        city = self.new_game()
        self.place(city, "core", (5, 2))
        self.place(city, "cloud", (4, 2))
        before = self.resources(city)
        self.start_placement(city, "wind", (3, 1))
        self.assertEqual(city.resources["light"], before["light"])
        city.update(1.0)
        self.assertEqual(city.resources["light"], before["light"])
        city.update(1.0)
        self.assertEqual(city.resources["light"], before["light"] + 2)
        self.assertEqual(city.resources["structure"], before["structure"] + 1)
        settled = self.resources(city)
        city.update(60.0)
        self.assertEqual(self.resources(city), settled, "position bonuses cannot become idle production")

    def test_grove_and_district_complete_automatically_once_after_settlement(self):
        city = self.new_game()
        self.unlock_forest_with_real_actions(city)
        self.assertEqual(self.progress(city, "district"), 4)
        self.assertNotIn("district", city.claimed_tasks)
        before = self.resources(city)
        self.start_placement(city, "forest", (3, 1))
        self.assertEqual(self.progress(city, "district"), 4)
        self.assertNotIn("district", city.claimed_tasks)
        city.update(2.0)
        self.assertIn("district", city.claimed_tasks)
        self.assertEqual(self.progress(city, "district"), 5)
        self.assertEqual(city.resources["resonance"], before["resonance"] + 3)
        self.assertEqual(self.progress(city, "grove"), 1)

        before = self.resources(city)
        self.start_placement(city, "forest", (3, 2))
        self.assertEqual(self.progress(city, "grove"), 1)
        self.assertNotIn("grove", city.claimed_tasks)
        city.update(2.0)
        self.assertIn("grove", city.claimed_tasks)
        self.assertEqual(self.progress(city, "grove"), 2)
        self.assertEqual(city.resources["structure"], before["structure"] + 5)
        self.assertEqual(city.resources["resonance"], before["resonance"] + 1)

        settled = self.resources(city)
        for _ in range(3):
            city.check_tasks()
            city.update(2.0)
        self.assertEqual(self.resources(city), settled)
        city.dismantle_at(game.cell_center((3, 2)))
        self.assertIn("grove", city.claimed_tasks)
        before_rebuild = self.resources(city)
        self.place(city, "forest", (3, 2))
        self.assertEqual(city.resources["structure"], before_rebuild["structure"])
        self.assertEqual(city.resources["resonance"], before_rebuild["resonance"])

    def test_skyline_reward_is_optional_and_cannot_be_reclaimed(self):
        city = self.new_game()
        self.place(city, "core", (5, 2))
        self.place(city, "cloud", (4, 2))
        self.place(city, "wind", (3, 1))
        self.place(city, "cloud", (4, 1))
        before = city.resources["light"]
        self.start_placement(city, "wind", (3, 2))
        self.assertEqual(self.progress(city, "skyline"), 1)
        self.assertNotIn("skyline", city.claimed_tasks)
        city.update(2.0)
        self.assertIn("skyline", city.claimed_tasks)
        self.assertEqual(city.resources["light"], before + 4)
        city.check_tasks()
        self.assertEqual(city.resources["light"], before + 4)
        self.assertFalse(city.finished, "optional objectives must not end the city")

    def test_combinations_reward_once_only_after_every_part_settles(self):
        city = self.new_game()
        city.placed = {
            (5, 2): "core", (5, 0): "cloud",
            (4, 0): "waterfall", (5, 1): "forest",
        }
        city.pending = [{"cell": (5, 0)}]
        self.assertIsNone(dict((combo["id"], cells) for combo, cells in city.city_combinations())["spring_grove"])
        before = city.resources["structure"]
        self.assertEqual(city.check_combinations(), [])
        self.assertEqual(city.resources["structure"], before)
        city.pending.clear()
        self.assertEqual(city.check_combinations(), ["泉林共鸣"])
        self.assertEqual(city.resources["structure"], before + 2)
        city.placed.pop((5, 0))
        city.placed[(5, 0)] = "cloud"
        before = city.resources["structure"]
        self.assertEqual(city.check_combinations(), [])
        self.assertEqual(city.resources["structure"], before)
        city.reset()
        self.assertFalse(city.claimed_combinations)

    def test_disconnected_or_unsettled_structures_do_not_complete_tasks(self):
        city = self.new_game()
        city.placed = {(5, 2): "core", (0, 0): "wind", (1, 0): "sundial"}
        city.check_tasks()
        self.assertEqual(self.progress(city, "skyline"), 0)
        self.assertEqual(city.claimed_tasks, set())
        city.placed = {(5, 2): "core", (4, 2): "cloud", (3, 1): "wind", (3, 2): "sundial"}
        city.pending = [{"cell": (3, 2), "kind": "sundial", "time": 1.8}]
        city.check_tasks()
        self.assertEqual(self.progress(city, "skyline"), 1)
        self.assertNotIn("skyline", city.claimed_tasks)

    def test_free_relocation_is_once_only_and_preserves_art_without_reproduction(self):
        city = self.new_game()
        self.bootstrap(city)
        self.place(city, "cloud", (6, 1))
        source, target = (4, 1), (4, 2)
        city.placed_variants[source] = 2
        city.placed_jitter[source] = (-3, 2)
        before_resources, before_fragments = self.resources(city), city.fragments
        self.assertTrue(city.begin_relocation())
        city.relocation_source = source
        self.assertIn(target, city.relocation_targets())
        self.assertTrue(city.relocate(source, target))
        self.assertNotIn(source, city.placed)
        self.assertEqual(city.placed[target], "wind")
        self.assertEqual(city.placed_variants[target], 2)
        self.assertEqual(city.placed_jitter[target], (-3, 2))
        self.assertEqual(self.resources(city), before_resources)
        self.assertEqual(city.fragments, before_fragments)
        self.assertFalse(city.pending)
        self.assertFalse(city.relocation_mode)
        self.assertFalse(city.relocation_available)
        self.assertIn((target, "wind"), city.settled_builds)
        self.assertIn(target, city.inspired_cells)
        city.update(3.0)
        self.assertEqual(self.resources(city), before_resources)
        self.assertFalse(city.begin_relocation())
        self.assertFalse(city.relocate(target, source))

        city.dismantle_at(game.cell_center(target))
        before_rebuild = self.resources(city)
        self.place(city, "wind", target)
        self.assertEqual(city.fragments, before_fragments)
        self.assertEqual(city.resources["light"], before_rebuild["light"])
        self.assertEqual(city.resources["structure"], before_rebuild["structure"])
        city.reset()
        self.assertTrue(city.relocation_available)

    def test_relocation_can_reconnect_a_bridge_but_cannot_orphan_a_branch(self):
        city = self.new_game()
        source = (4, 1)
        city.placed = {(5, 2): "core", source: "cloud", (3, 1): "wind"}
        self.assertEqual(city.connected_cells(), set(city.placed))
        self.assertTrue(city.begin_relocation())
        city.relocation_source = source
        targets = city.relocation_targets()
        self.assertIn((4, 2), targets, "moving a bridge is legal if it reconnects every remaining building")
        self.assertNotIn((5, 3), targets, "a destination by the core must not orphan the far branch")
        before = self.snapshot(city)
        self.assertFalse(city.relocate(source, (5, 3)))
        self.assertEqual(self.snapshot(city), before)
        self.assertTrue(city.relocation_available)
        self.assertTrue(city.relocate(source, (4, 2)))
        self.assertEqual(city.connected_cells(), set(city.placed))

    def test_relocation_rejects_core_locked_occupied_wrong_source_and_pending(self):
        city = self.new_game()
        self.bootstrap(city)
        self.assertTrue(city.begin_relocation())
        city.relocation_source = (5, 2)
        self.assertEqual(city.relocation_targets(), [])
        self.assertFalse(city.relocate((5, 2), (4, 2)))
        city.relocation_source = (4, 1)
        before = self.snapshot(city)
        for source, target in (((4, 1), (0, 0)), ((4, 1), (5, 2)), ((5, 1), (4, 2)), ((4, 1), (99, 99))):
            with self.subTest(source=source, target=target):
                self.assertFalse(city.relocate(source, target))
                self.assertEqual(self.snapshot(city), before)
                self.assertTrue(city.relocation_available)
        city.pending = [{"cell": (4, 1), "kind": "wind", "time": 1.8}]
        self.assertFalse(city.begin_relocation())
        self.assertEqual(city.relocation_targets(), [])
        self.assertFalse(city.relocate((4, 1), (4, 2)))
        city.pending = []
        city.finished = True
        self.assertFalse(city.begin_relocation())
        self.assertEqual(city.relocation_targets(), [])
        self.assertFalse(city.relocate((4, 1), (4, 2)))

    def test_relocation_cancellation_does_not_consume_the_permission(self):
        city = self.new_game()
        self.bootstrap(city)
        before = self.snapshot(city)
        self.assertTrue(city.begin_relocation())
        city.relocation_source = (4, 1)
        self.assertTrue(city.begin_relocation())
        self.assertFalse(city.relocation_mode)
        self.assertIsNone(city.relocation_source)
        self.assertTrue(city.relocation_available)
        self.assertEqual(self.snapshot(city), before)

    def test_relocation_uses_the_actual_button_and_two_board_clicks(self):
        city = self.new_game()
        self.bootstrap(city)
        before_resources, before_fragments = self.resources(city), city.fragments
        source, target = (4, 1), (4, 2)
        city.handle_event(pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1, pos=game.RELOCATE_BUTTON.center))
        self.assertTrue(city.relocation_mode)
        city.handle_event(pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1, pos=game.cell_center((5, 2))))
        self.assertIsNone(city.relocation_source, "clicking the core must not select a relocation source")
        city.handle_event(pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1, pos=game.cell_center(source)))
        self.assertEqual(city.relocation_source, source)
        city.handle_event(pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=3, pos=game.cell_center(source)))
        self.assertIn(source, city.placed, "right-click must not accidentally demolish during relocation")
        city.handle_event(pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1, pos=game.cell_center(target)))
        self.assertEqual(city.placed.get(target), "wind")
        self.assertNotIn(source, city.placed)
        self.assertFalse(city.relocation_available)
        self.assertEqual(self.resources(city), before_resources)
        self.assertEqual(city.fragments, before_fragments)

    def test_composition_preview_is_read_only_and_escape_returns_to_play(self):
        city = self.new_game()
        self.bootstrap(city)
        city.handle_event(pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1, pos=game.VIEW_BUTTON.center))
        before = self.snapshot(city)
        city.handle_event(pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=3, pos=game.cell_center((5, 1))))
        city.selected = "cloud"
        city.handle_event(pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1, pos=game.cell_center((4, 2))))
        city.handle_event(pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1, pos=game.RELOCATE_BUTTON.center))
        self.assertEqual(self.snapshot(city), before)
        self.assertFalse(city.relocation_mode)
        city.handle_event(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_ESCAPE))
        self.assertEqual(city.view_mode, "art")
        self.assertTrue(city.running)

    def test_score_exposes_five_bounded_components_and_ending_snapshots_style(self):
        city = self.new_game()
        # A graph/scoring fixture, not a production test: use all slot/type
        # combinations to exercise maximum bounds independently of economy.
        kinds = tuple(kind for kind in game.TILE_INFO if kind != "core")
        city.placed = {cell: kinds[index % len(kinds)] for index, cell in enumerate(game.CELLS)}
        city.placed[(5, 2)] = "core"
        city.claimed_tasks = {task["id"] for task in city_rules.TASKS}
        scores = city.calculate_score()
        self.assertEqual(set(scores), {"composition", "network", "synergy", "style", "tasks"})
        self.assertTrue(all(isinstance(score, int) and score >= 0 for score in scores.values()))
        self.assertTrue(0 < sum(scores.values()) <= 100)
        self.assertLessEqual(scores["style"], 15)
        expected_styles = city.city_style_scores()
        city.check_complete()
        self.assertTrue(city.finished)
        self.assertTrue(city.result_visible)
        self.assertEqual(city.score_breakdown, scores)
        self.assertEqual(city.score, sum(scores.values()))
        self.assertEqual(city.final_style_scores, expected_styles)
        city.update(10.0)
        self.assertEqual(city.score_breakdown, scores)
        self.assertEqual(city.final_style_scores, expected_styles)

    def test_city_modal_and_view_toggle_do_not_mutate_the_board(self):
        city = self.new_game()
        self.bootstrap(city)
        before = self.snapshot(city)
        city.handle_event(pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1, pos=game.CITY_BUTTON.center))
        self.assertTrue(city.city_open)
        self.assertTrue(city.modal_open())
        city.handle_event(pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=3, pos=game.cell_center((5, 1))))
        self.assertEqual(self.snapshot(city), before)
        city.handle_event(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_ESCAPE))
        self.assertFalse(city.city_open)
        self.assertTrue(city.running)
        old_mode = city.view_mode
        city.handle_event(pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1, pos=game.VIEW_BUTTON.center))
        self.assertNotEqual(city.view_mode, old_mode)
        self.assertEqual(self.snapshot(city), before)
        city.handle_event(pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1, pos=game.SHOWCASE_BACK.center))
        self.assertEqual(city.view_mode, old_mode)

    def test_neighbors_are_symmetric_at_the_center_seam(self):
        for cell in game.CELLS:
            for neighbor in game.neighbors(cell):
                self.assertIn(cell, game.neighbors(neighbor))

    def test_slot_hit_test_uses_the_diamond_not_a_nearby_circle(self):
        center = game.cell_center((5, 2))
        self.assertEqual(game.SkyCity.cell_at(center), (5, 2))
        self.assertIsNone(game.SkyCity.cell_at((center[0] + 35, center[1] + 6)))

    def test_reward_preview_matches_new_and_rebuilt_settlements(self):
        city = self.new_game()
        self.bootstrap(city)
        cell = (4, 2)
        predicted = city.placement_reward(cell, "cloud")
        before = self.resources(city)
        self.place(city, "cloud", cell)
        cost = game.TILE_INFO["cloud"]["cost"]
        actual = {name: city.resources[name] - before[name] + cost.get(name, 0)
                  for name in game.RESOURCE_NAMES if name in predicted}
        self.assertEqual(predicted, actual)
        city.dismantle_at(game.cell_center(cell))
        self.assertIsNone(city.placement_reward(cell, "cloud"))
        self.assertIsNotNone(city.placement_reward(cell, "wind"))

    def test_composition_preview_cannot_spend_research_fragments(self):
        city = self.new_game()
        self.bootstrap(city)
        self.assertTrue(city.can_research("waterfall"))
        city.view_mode = "overview"
        before = city.fragments, tuple(city.unlocked)
        city.handle_event(pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1, pos=game.SHOWCASE_SCORE.center))
        self.assertTrue(city.tech_open)
        city.handle_event(pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1, pos=city.tech_rect("waterfall").center))
        self.assertEqual((city.fragments, tuple(city.unlocked)), before)
        self.assertIn("返回插装", city.tech_feedback)
        city.tech_open = False
        city.view_mode = "art"
        self.assertTrue(city.research("waterfall"))


if __name__ == "__main__":
    unittest.main()
