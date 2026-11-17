import unittest

import game
from building_quotes import BUILDING_QUOTES, get_building_quote


class BuildingQuoteTests(unittest.TestCase):
    def test_every_building_has_a_distinct_epigraph_and_source(self):
        quotes = [get_building_quote(kind) for kind in game.TILE_INFO]
        self.assertEqual(set(game.TILE_INFO), set(BUILDING_QUOTES))
        self.assertEqual(len({entry["quote"] for entry in quotes}), len(quotes))
        for entry in quotes:
            self.assertTrue(entry["quote"])
            self.assertTrue(entry["author"])
            self.assertTrue(entry["work"])
            self.assertTrue(entry["source"].startswith("https://"))

    def test_catalogue_keeps_a_cross_cultural_mix(self):
        foreign = {"core", "cloud", "wind", "waterfall", "garden", "observatory"}
        self.assertGreaterEqual(len(foreign), 6)
        self.assertTrue(all(get_building_quote(kind)["author"] not in {"王勃", "王维", "李白", "白居易", "王安石"}
                            for kind in foreign))
        self.assertEqual(get_building_quote("garden")["original"],
                         "To see a world in a grain of sand, / And a heaven in a wild flower")


if __name__ == "__main__":
    unittest.main()
