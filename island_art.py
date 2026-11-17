"""Native 2-D floating-island artwork.

The game deliberately keeps the island as painted geometry instead of one
large generated bitmap.  That keeps the board sharp at fullscreen sizes and
lets the placement grid remain readable over the continuous ground shape.
"""

from __future__ import annotations

import random
from functools import lru_cache
from typing import Sequence

import pygame


# A restrained paper-cut palette.  The values are intentionally opaque and
# flat: layering, not gradients, supplies the depth cue.
PAPER = (218, 221, 198)
PAPER_LIGHT = (232, 230, 207)
PAPER_SHADE = (190, 203, 183)
JADE = (104, 157, 147)
JADE_DARK = (57, 105, 105)
JADE_LIGHT = (143, 187, 168)
STONE_DARK = (69, 91, 101)
STONE_MID = (94, 119, 125)
STONE_LIGHT = (130, 151, 149)
ORE = (207, 164, 78)
INK = (50, 73, 78)


def _points_inside(rect: pygame.Rect, values: Sequence[tuple[float, float]]) -> list[tuple[int, int]]:
    return [(round(rect.left + rect.width * x), round(rect.top + rect.height * y)) for x, y in values]


def _outline(rect: pygame.Rect, seed: int) -> list[tuple[int, int]]:
    """Return an asymmetric, gently chamfered top silhouette."""
    rng = random.Random(seed)
    # Keep a long, mostly level lower edge so the 36-cell diamond has room.
    values = [
        (0.08, 0.06), (0.27, 0.015), (0.49, 0.01), (0.72, 0.035),
        (0.91, 0.12), (0.98, 0.27), (0.985, 0.43), (0.985, 0.60),
        (0.95, 0.78), (0.86, 0.93), (0.68, 0.985), (0.52, 0.96),
        (0.39, 1.0), (0.22, 0.975), (0.07, 0.91), (0.015, 0.76),
        (0.018, 0.60), (0.012, 0.43), (0.04, 0.25),
    ]
    # Tiny deterministic hand-cut irregularities avoid a perfect repeated
    # shape while retaining a stable footprint between frames.
    jittered = []
    for index, (x, y) in enumerate(values):
        dx = (rng.random() - 0.5) * (0.010 if index % 3 else 0.016)
        dy = (rng.random() - 0.5) * (0.010 if index % 2 else 0.016)
        jittered.append((max(0.0, min(1.0, x + dx)), max(0.0, min(1.0, y + dy))))
    return _points_inside(rect, jittered)


def _front_chain(outline: Sequence[tuple[int, int]], rect: pygame.Rect) -> list[tuple[int, int]]:
    """Extract a bottom-facing chain, ordered left-to-right."""
    # The outline is clockwise, beginning at the upper-left.  Points at or
    # below 57% of the height are the visible front lip of the island.
    chain = [point for point in outline if point[1] >= rect.top + rect.height * 0.56]
    chain.sort(key=lambda point: point[0])
    if len(chain) < 4:
        chain = [(rect.left, rect.bottom - 18), (rect.centerx, rect.bottom), (rect.right, rect.bottom - 18)]
    return chain


def _draw_cliff(surface: pygame.Surface, rect: pygame.Rect, outline: Sequence[tuple[int, int]], cliff_height: int, rng: random.Random) -> pygame.Rect:
    chain = _front_chain(outline, rect)
    left, right = chain[0][0], chain[-1][0]
    panorama = rect.width / max(1, rect.height) >= 3.0
    baseline = max(y for _, y in chain)
    bottom_y = min(surface.get_height() - 1, baseline + cliff_height)

    def front_y(x: int) -> int:
        for (x1, y1), (x2, y2) in zip(chain, chain[1:]):
            if x1 <= x <= x2:
                return round(y1 + (y2 - y1) * (x - x1) / max(1, x2 - x1))
        return chain[0][1] if x < chain[0][0] else chain[-1][1]

    # Unequal ledges, missing chunks and a central hanging tongue echo the
    # reference silhouette.  This deliberately avoids a grid of rock columns.
    lower_values = [
        (0.0, 0.16), (0.035, 0.33), (0.10, 0.28), (0.15, 0.53),
        (0.22, 0.46), (0.26, 0.67), (0.32, 0.54), (0.40, 0.67),
        (0.45, 0.52), (0.52, 1.0), (0.57, 0.75), (0.64, 0.64),
        (0.70, 0.51), (0.79, 0.63), (0.85, 0.43), (0.91, 0.35),
        (0.96, 0.22), (1.0, 0.12),
    ]
    if not panorama:
        lower_values = [(fraction, depth * (0.74 + 0.26 * (1.0 - abs(fraction - 0.52)))) for fraction, depth in lower_values]
    lower = [
        (round(left + (right - left) * fraction), min(bottom_y, round(baseline + cliff_height * depth)))
        for fraction, depth in lower_values
    ]
    face = list(chain) + list(reversed(lower))
    pygame.draw.polygon(surface, STONE_MID, face)
    pygame.draw.lines(surface, STONE_DARK, False, list(reversed(lower)), 2)

    groups = ((0, 3), (3, 6), (6, 9), (9, 11), (11, 14), (14, 17))
    for index, (first, last) in enumerate(groups):
        x1, _ = lower[first]
        x2, _ = lower[last]
        top = ((x1, front_y(x1)), (x2, front_y(x2)))
        color = (STONE_LIGHT, STONE_MID, STONE_DARK, (111, 137, 136), STONE_MID, (119, 146, 142))[index]
        polygon = list(top) + list(reversed(lower[first:last + 1]))
        pygame.draw.polygon(surface, color, polygon)
        # The diagonal shade is a large plane, not a texture sprayed across
        # every individual stone.
        if index in (0, 2, 5):
            mid_x = round(x1 + (x2 - x1) * 0.63)
            top_y = front_y(mid_x)
            bottom_x, low_y = lower[first + (last - first) // 2]
            pygame.draw.polygon(surface, STONE_MID if index != 2 else (57, 80, 89), ((x1, front_y(x1)), (mid_x, top_y), (bottom_x, low_y)))

    # Two shallow strata make the upper stone read as continuous rock.  They
    # follow the irregular front lip, so the face is not a second rectangle.
    for amount, color in ((0.12, (161, 177, 161)), (0.22, (99, 132, 126))):
        offset = max(3, round(cliff_height * amount))
        band = list(chain) + [(x, min(bottom_y, y + offset)) for x, y in reversed(chain)]
        pygame.draw.polygon(surface, color, band)
    for index in (3, 7, 12, 15):
        x, y = lower[index]
        pygame.draw.line(surface, (63, 94, 100), (x - 4, front_y(x) + round(cliff_height * 0.24)), (x + 9, y - 5), 1)
    for fraction, depth in ((0.17, 0.38), (0.63, 0.31), (0.89, 0.27)):
        x = round(left + (right - left) * fraction)
        y = min(bottom_y - 7, front_y(x) + round(cliff_height * depth))
        pygame.draw.lines(surface, ORE, False, ((x - 12, y + 3), (x - 2, y), (x + 7, y + 5)), 2)
    return pygame.Rect(max(0, left), min(y for _, y in outline), max(1, right - left + 1), max(1, bottom_y - min(y for _, y in outline) + 1))


def _draw_top(surface: pygame.Surface, rect: pygame.Rect, outline: Sequence[tuple[int, int]], rng: random.Random) -> None:
    pygame.draw.polygon(surface, PAPER_SHADE, outline)
    # Chalk-coloured interior planes are sparse and irregular, never a tiled
    # pattern.  The actual placement diamonds are painted above this layer.
    inset = [(x + round((rect.centerx - x) * 0.035), y + round((rect.centery - y) * 0.035)) for x, y in outline]
    pygame.draw.polygon(surface, PAPER, inset)
    # Hand-cut jade rim, broken in a few places so it does not look like a
    # uniform UI border.
    pygame.draw.lines(surface, JADE_DARK, True, outline, 3)
    for start in (1, 5, 9, 14):
        if start + 2 < len(outline):
            pygame.draw.lines(surface, JADE_LIGHT, False, outline[start:start + 3], 2)

    patches = [
        ((0.09, 0.27), (0.26, 0.22), (0.34, 0.29), (0.18, 0.36)),
        ((0.63, 0.17), (0.86, 0.22), (0.80, 0.34), (0.68, 0.31)),
        ((0.20, 0.73), (0.37, 0.68), (0.47, 0.80), (0.27, 0.86)),
        ((0.62, 0.68), (0.83, 0.66), (0.88, 0.82), (0.69, 0.88)),
    ]
    for patch_index, patch in enumerate(patches):
        points = _points_inside(rect, patch)
        pygame.draw.polygon(surface, PAPER_LIGHT if patch_index % 2 else PAPER_SHADE, points)
        pygame.draw.lines(surface, (177, 193, 177), False, points[:3], 1)

    # Restrained ore marks suggest a living mineral island and help the gold
    # accents read as material rather than decoration.
    margin_x = min(42, max(3, rect.width // 8))
    margin_y = min(30, max(3, rect.height // 5))
    for _ in range(max(5, min(11, rect.width // 100))):
        x = rng.randint(rect.left + margin_x, rect.right - margin_x - 1)
        y = rng.randint(rect.top + margin_y, rect.bottom - margin_y - 1)
        pygame.draw.line(surface, ORE, (x, y), (x + rng.randint(5, 12), y + rng.randint(-3, 4)), 2)


def _draw_vines(surface: pygame.Surface, rect: pygame.Rect, outline: Sequence[tuple[int, int]]) -> None:
    # A few thin trailing strokes make the front edge feel inhabited while
    # remaining subordinate to the buildings.
    front = _front_chain(outline, rect)
    for index, (x, y) in enumerate(front[1:-1]):
        if index % 3:
            continue
        length = 10 + (index % 3) * 5
        pygame.draw.line(surface, JADE_DARK, (x, y), (x - 4 + index % 2 * 8, y + length), 2)
        pygame.draw.line(surface, JADE_LIGHT, (x - 2, y + length // 2), (x + 6, y + length // 2 + 2), 1)


@lru_cache(maxsize=8)
def _island_texture(width: int, height: int, cliff_height: int, seed: int) -> pygame.Surface:
    surface = pygame.Surface((width, height + cliff_height), pygame.SRCALPHA)
    rect = pygame.Rect(0, 0, width, height)
    rng = random.Random(seed)
    outline = _outline(rect, seed)
    if cliff_height:
        _draw_cliff(surface, rect, outline, cliff_height, rng)
    _draw_top(surface, rect, outline, rng)
    if cliff_height:
        _draw_vines(surface, rect, outline)
    return surface


def draw_island_image(surface: pygame.Surface, rect: pygame.Rect, image: pygame.Surface) -> pygame.Rect:
    """Draw a generated front-facing island cutout inside ``rect``.

    The image is cropped to its alpha bounds before scaling, so transparent
    chroma-key margins never change the visual footprint.  The program-drawn
    fallback remains available for systems without the optional asset.
    """
    if not isinstance(rect, pygame.Rect):
        rect = pygame.Rect(rect)
    bounds = image.get_bounding_rect(min_alpha=20)
    if not bounds.width or not bounds.height or rect.width < 12 or rect.height < 12:
        return rect.copy()
    sprite = image.subsurface(bounds).copy()
    sprite = pygame.transform.smoothscale(sprite, rect.size)
    surface.blit(sprite, rect.topleft)
    return rect.copy()


def draw_island(surface: pygame.Surface, rect: pygame.Rect, *, cliff_height: int | None = None, seed: int = 43) -> pygame.Rect:
    """Draw a continuous 2-D island and return its painted bounding box.

    ``rect`` describes the top surface, not an isometric projection.  The
    optional cliff height controls only the front elevation; a value of zero
    is useful for compact preview cards.
    """
    if not isinstance(rect, pygame.Rect):
        rect = pygame.Rect(rect)
    rect = rect.clip(surface.get_rect())
    if rect.width < 12 or rect.height < 12:
        return rect.copy()
    height = max(0, int(cliff_height if cliff_height is not None else min(112, rect.height * 0.35)))
    height = min(height, max(0, surface.get_height() - rect.bottom))
    artwork = _island_texture(rect.width, rect.height, height, seed)
    surface.blit(artwork, rect.topleft)
    return artwork.get_bounding_rect().move(rect.topleft).clip(surface.get_rect())


__all__ = ["draw_island", "draw_island_image"]
