import os
import unittest

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pygame

from island_art import draw_island


class IslandArtTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        pygame.init()

    @classmethod
    def tearDownClass(cls):
        pygame.quit()

    def test_board_island_is_opaque_and_bounded(self):
        surface = pygame.Surface((800, 800), pygame.SRCALPHA)
        box = draw_island(surface, pygame.Rect(24, 112, 700, 444), cliff_height=185, seed=43)
        self.assertTrue(box.left >= 0 and box.top >= 0)
        self.assertLessEqual(box.right, 800)
        self.assertLessEqual(box.bottom, 800)
        self.assertGreater(surface.get_bounding_rect().width, 600)
        self.assertGreater(surface.get_bounding_rect().height, 400)
        # The tallest row has six slots, so its outer diamonds need enough
        # continuous ground even at the hand-cut indentation.
        for row in range(11):
            count = 1 + min(row, 10 - row)
            for column in range(count):
                x = 18 + (512 + (column - (count - 1) / 2) * 170) * 704 / 1024
                y = 54 + (170 + row * 45) * 704 / 1024
                for dx, dy in ((42, 0), (-42, 0), (0, 25), (0, -25)):
                    self.assertEqual(surface.get_at((round(x + dx), round(y + dy))).a, 255)

    def test_seed_is_deterministic(self):
        first = pygame.Surface((800, 800), pygame.SRCALPHA)
        second = pygame.Surface((800, 800), pygame.SRCALPHA)
        draw_island(first, pygame.Rect(24, 112, 700, 444), cliff_height=185, seed=7)
        draw_island(second, pygame.Rect(24, 112, 700, 444), cliff_height=185, seed=7)
        self.assertEqual(pygame.image.tostring(first, "RGBA"), pygame.image.tostring(second, "RGBA"))

    def test_panorama_has_a_flat_front_elevation(self):
        surface = pygame.Surface((1280, 800), pygame.SRCALPHA)
        box = draw_island(surface, pygame.Rect(110, 336, 1060, 205), cliff_height=185, seed=21)
        self.assertGreater(box.height, 300)
        self.assertGreater(box.width, 1000)
        self.assertLessEqual(box.bottom, 800)

    def test_zero_cliff_is_compact(self):
        surface = pygame.Surface((400, 300), pygame.SRCALPHA)
        box = draw_island(surface, pygame.Rect(20, 40, 300, 150), cliff_height=0, seed=2)
        self.assertLessEqual(box.bottom, 190)
        self.assertLessEqual(box.right, 320)


if __name__ == "__main__":
    unittest.main()
