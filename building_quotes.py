"""Verified literary epigraphs for the Sky City building catalogue.

The quotations are short excerpts from public-domain classical works.  The
``source`` field points to the source text used when transcribing each line.
"""

BUILDING_QUOTES = {
    "core": {
        "quote": "人是一座神圣的城，由奇妙的大地筑成。",
        "author": "John Masefield",
        "work": "Chorus（《Pompey the Great》）",
        "original": "Man is a sacred city, built of marvellous earth",
        "source": "https://www.gutenberg.org/files/61286/old/61286-h/61286-h.htm",
    },
    "cloud": {
        "quote": "大地、水与空气，饮尽光之泉涌出的光辉。",
        "author": "Mary W. Shelley",
        "work": "The Mourner",
        "original": "Earth, water, air drink to overflowing the radiance that streams from yonder well of light",
        "source": "https://dev.gutenberg.org/cache/epub/56665/pg56665-images.html",
    },
    "wind": {
        "quote": "我还要回到海上，回到寂寥的海与天空。",
        "author": "John Masefield",
        "work": "Sea-Fever（《Salt-Water Ballads》）",
        "original": "I must go down to the seas again, to the lonely sea and the sky",
        "source": "https://www.gutenberg.org/files/61286/old/61286-h/61286-h.htm",
    },
    "waterfall": {
        "quote": "那里没有风暴，绿色的潮汐在静默港湾起伏。",
        "author": "Gerard Manley Hopkins",
        "work": "Heaven—Haven",
        "original": "Where no storms come, / Where the green swell is in the havens dumb",
        "source": "https://www.gutenberg.org/cache/epub/22403/pg22403.html",
    },
    "forest": {
        "quote": "绿树村边合，青山郭外斜。",
        "author": "孟浩然",
        "work": "《过故人庄》",
        "source": "https://zh.wikisource.org/zh-hans/%E9%81%8E%E6%95%85%E4%BA%BA%E8%8E%8A",
    },
    "garden": {
        "quote": "从一粒沙看见世界，从一朵野花看见天堂。",
        "author": "William Blake",
        "work": "Auguries of Innocence",
        "original": "To see a world in a grain of sand, / And a heaven in a wild flower",
        "source": "https://en.wikisource.org/wiki/Page%3ALife_of_William_Blake%2C_Pictor_ignotus_%28Volume_2%29.djvu/111",
    },
    "sundial": {
        "quote": "海日生残夜，江春入旧年。",
        "author": "王湾",
        "work": "《次北固山下》",
        "source": "https://zh.wikisource.org/wiki/%E6%AC%A1%E5%8C%97%E5%9B%BA%E5%B1%B1%E4%B8%8B",
    },
    "gear": {
        "quote": "如切如磋，如琢如磨。",
        "author": "《诗经》",
        "work": "《淇奥》",
        "source": "https://zh.wikisource.org/zh-hans/%E8%A9%A9%E7%B6%93/%E6%B7%87%E5%A5%A7",
    },
    "bridge": {
        "quote": "小桥流水人家。",
        "author": "马致远",
        "work": "《天净沙·秋思》",
        "source": "https://zh.wikisource.org/zh-hans/%E5%A4%A9%E6%B7%A8%E6%B2%99%C2%B7%E7%A7%8B%E6%80%9D",
    },
    "residents": {
        "quote": "安得广厦千万间，大庇天下寒士俱欢颜。",
        "author": "杜甫",
        "work": "《茅屋为秋风所破歌》",
        "source": "https://zh.wikisource.org/zh-hans/%E8%8C%85%E5%B1%8B%E4%B8%BA%E7%A7%8B%E9%A3%8E%E6%89%80%E7%A0%B4%E6%AD%8C",
    },
    "harbor": {
        "quote": "潮平两岸阔，风正一帆悬。",
        "author": "王湾",
        "work": "《次北固山下》",
        "source": "https://zh.wikisource.org/wiki/%E6%AC%A1%E5%8C%97%E5%9B%BA%E5%B1%B1%E4%B8%8B",
    },
    "observatory": {
        "quote": "伟人抵达并守住的高度，从来不是一跃而成。",
        "author": "Henry Wadsworth Longfellow",
        "work": "The Ladder of St. Augustine",
        "original": "The heights by great men reached and kept / Were not attained by sudden flight",
        "source": "https://www.gutenberg.org/files/23332/23332-h/23332-h.htm",
    },
}


def get_building_quote(kind):
    """Return the catalogue epigraph for ``kind`` or ``None`` if unknown."""
    return BUILDING_QUOTES.get(kind)
