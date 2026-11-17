import os
import unittest

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pygame


class LandscapeAssetTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        pygame.init()
        pygame.display.set_mode((1, 1))

    @classmethod
    def tearDownClass(cls):
        pygame.quit()

    def test_generated_cloud_and_waterfall_are_transparent_cutouts(self):
        for relative in ("generated_assets/landscape/cloud_bank.png",
                         "generated_assets/landscape/waterfall.png"):
            with self.subTest(relative=relative):
                self.assertTrue(os.path.exists(relative))
                image = pygame.image.load(relative).convert_alpha()
                self.assertEqual(image.get_size(), (1024, 1024))
                bounds = image.get_bounding_rect(min_alpha=20)
                self.assertGreater(bounds.width, 0)
                self.assertGreater(bounds.height, 0)
                self.assertLess(bounds.width * bounds.height, image.get_width() * image.get_height())

    def test_generated_island_base_is_an_organic_transparent_cutout(self):
        image = pygame.image.load("generated_assets/landscape/island_base.png").convert_alpha()
        self.assertEqual(image.get_size(), (1024, 1024))
        bounds = image.get_bounding_rect(min_alpha=20)
        self.assertGreater(bounds.width, 800)
        self.assertGreater(bounds.height, 300)
        self.assertGreater((pygame.surfarray.array_alpha(image) == 0).sum(), image.get_width() * image.get_height() // 3)

    def test_generated_combination_accents_are_transparent_cutouts(self):
        for name in ("spring", "airway", "hamlet"):
            relative = f"generated_assets/combinations/{name}.png"
            with self.subTest(name=name):
                image = pygame.image.load(relative).convert_alpha()
                self.assertEqual(image.get_size(), (1024, 1024))
                alpha = pygame.surfarray.array_alpha(image)
                self.assertLess(int((alpha == 0).sum()), alpha.size)
                self.assertGreater(int((alpha == 0).sum()), alpha.size // 3)

    def test_unified_building_variants_are_transparent_and_available_to_loader(self):
        for kind in ("core", "wind", "residents"):
            relative = f"generated_assets/{kind}/{kind}_v04.png"
            with self.subTest(kind=kind):
                image = pygame.image.load(relative).convert_alpha()
                self.assertEqual(image.get_size(), (1024, 1024))
                bounds = image.get_bounding_rect(min_alpha=20)
                self.assertGreater(bounds.height, bounds.width // 3)
                self.assertGreater(int((pygame.surfarray.array_alpha(image) == 0).sum()), image.get_width() * image.get_height() // 3)


if __name__ == "__main__":
    unittest.main()
