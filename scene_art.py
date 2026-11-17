"""Read-only, front-facing city presentation, separate from placement geometry."""
import math

import pygame

from island_art import draw_island, draw_island_image


GROUND_KINDS = {"cloud", "forest", "waterfall"}
_CROPS = {}
_SPRITES = {}


def clear_scene_cache():
    _CROPS.clear()
    _SPRITES.clear()


def showcase_layout(placed):
    """Stable visual feet and heights; never changes the board or its adjacency."""
    layout = {}
    # The panorama is a front elevation rather than the placement diamond.  A
    # 150px cadence keeps neighboring buildings visually connected while still
    # leaving enough air for the tallest landmarks.  All variation is derived
    # from the cell coordinate, so opening the same showcase never reshuffles
    # the skyline.
    heights = {"cloud": 37, "forest": 85, "waterfall": 57,
               "core": 235, "wind": 170, "observatory": 200,
               "gear": 130, "sundial": 135, "bridge": 75,
               "residents": 120, "harbor": 135, "garden": 107}
    peers_by_kind = {}
    for peer_cell, peer_kind in sorted(placed.items()):
        peers_by_kind.setdefault(peer_kind, []).append(peer_cell)
    for cell, kind in sorted(placed.items()):
        row, col = cell
        width = 1 + min(row, 10 - row)
        phase = row * 13 + col * 7
        x = 640 + (col - (width - 1) / 2) * 150
        x += math.sin(phase * 1.7) * 13
        # Rows nearer the front edge sit lower and are intentionally quieter;
        # the rear rows form a taller, readable silhouette behind them.
        y = 348 + row * 15 + math.sin(phase * 0.8) * 5
        depth_scale = 1.14 - row * 0.029
        variation = 0.86 + ((phase * 17 + row * 3) % 11) * 0.033
        height = heights[kind] * depth_scale * variation
        if kind == "core":
            # The core is the visual anchor, but its depth still gives it a
            # subtle relationship to the surrounding skyline.
            height = heights[kind] * (1.02 + (10 - row) * 0.008)
        elif kind in {"wind", "sundial"}:
            # Keep one or two landmark accents high; later copies step down
            # progressively instead of collapsing to identical miniatures.
            peers = peers_by_kind.get(kind, [])
            ordinal = peers.index(cell) if cell in peers else 0
            height *= 1.0 if ordinal == 0 else max(0.76, 0.94 - ordinal * 0.06)
        elif kind == "observatory":
            height *= 1.04
        # Keep even a rear-row landmark below the showcase header.  This is a
        # presentation-only crop guard; the card artwork and board footprint
        # remain unchanged.
        if kind != "core":
            height = min(height, 230)
        layout[cell] = (x, y, round(height))
    return layout


def crop_scene_sprite(image, kind):
    """Extract upper foliage or remove the insertion tab, leaving card art intact."""
    key = id(image), kind
    if key in _CROPS:
        return _CROPS[key]
    bounds = image.get_bounding_rect(min_alpha=20)
    if not bounds.width or not bounds.height:
        return image.copy()
    start, end = 0.0, 1.0
    if kind == "forest":
        end = 0.29
    elif kind == "cloud":
        start, end = 0.42, 0.57
    elif kind == "waterfall":
        end = 0.59
    elif kind == "garden":
        end = 0.73
    elif kind in {"core", "bridge", "harbor"}:
        end = 0.94
    rect = pygame.Rect(bounds.x, bounds.y + round(bounds.height * start), bounds.width,
                       max(1, round(bounds.height * (end - start))))
    sprite = image.subsurface(rect).copy()
    if kind in GROUND_KINDS or kind == "garden":
        # A short alpha taper hides the crop edge in the shared ground layer.
        fade = max(1, round(sprite.get_height() * 0.12))
        mask = pygame.Surface(sprite.get_size(), pygame.SRCALPHA)
        mask.fill((255, 255, 255, 255))
        for offset in range(fade):
            y = sprite.get_height() - fade + offset
            pygame.draw.line(mask, (255, 255, 255, round(255 * (1 - offset / fade))),
                             (0, y), (sprite.get_width() - 1, y))
        sprite.blit(mask, (0, 0), special_flags=pygame.BLEND_RGBA_MULT)
    _CROPS[key] = sprite
    return sprite


def _sprite(images, kind, variant, height):
    if kind not in images:
        return None
    variants = images[kind]
    source = variants[variant % len(variants)] if isinstance(variants, list) else variants
    key = id(source), kind, height
    if key not in _SPRITES:
        sprite = crop_scene_sprite(source, kind)
        width = max(1, round(sprite.get_width() * height / sprite.get_height()))
        _SPRITES[key] = pygame.transform.smoothscale(sprite, (width, height))
    return _SPRITES[key]


def _curve(points, steps=24):
    a, b, c, d = points
    return [((1 - t) ** 3 * a[0] + 3 * (1 - t) ** 2 * t * b[0] +
             3 * (1 - t) * t * t * c[0] + t ** 3 * d[0],
             (1 - t) ** 3 * a[1] + 3 * (1 - t) ** 2 * t * b[1] +
             3 * (1 - t) * t * t * c[1] + t ** 3 * d[1])
            for t in (index / steps for index in range(steps + 1))]


def _landscape_sprite(image, width=None, height=None):
    """Scale a transparent generated landscape sprite while retaining its aspect."""
    if image is None:
        return None
    bounds = image.get_bounding_rect(min_alpha=12)
    if not bounds.width or not bounds.height:
        return None
    sprite = image.subsurface(bounds).copy()
    if width is None:
        width = max(1, round(sprite.get_width() * height / sprite.get_height()))
    if height is None:
        height = max(1, round(sprite.get_height() * width / sprite.get_width()))
    return pygame.transform.smoothscale(sprite, (max(1, round(width)), max(1, round(height))))


def build_showcase(size, placed, variants, jitter, images, neighbors, landscape=None,
                   combination_assets=None, combo_matches=None):
    """Build native-resolution layers, cached by the game until layout changes."""
    factor = min(size[0] / 1280, size[1] / 800)
    offset = ((size[0] - 1280 * factor) / 2, (size[1] - 800 * factor) / 2)
    background = pygame.Surface(size)
    city = pygame.Surface(size, pygame.SRCALPHA)

    def point(x, y):
        return round(offset[0] + x * factor), round(offset[1] + y * factor)

    def rect(x, y, w, h):
        return pygame.Rect(*point(x, y), max(1, round(w * factor)), max(1, round(h * factor)))

    def polygon(color, points):
        pygame.draw.polygon(city, color, [point(x, y) for x, y in points])

    def line(color, points, width=1):
        pygame.draw.lines(city, color, False, [point(x, y) for x, y in points], max(1, round(width * factor)))

    # Painted sky bands, not a generated background with embedded UI text.
    for y in range(size[1]):
        t = y / max(1, size[1] - 1)
        top, bottom = (134, 176, 193), (213, 232, 222)
        color = tuple(round(top[index] * (1 - t) + bottom[index] * t) for index in range(3))
        pygame.draw.line(background, color, (0, y), (size[0], y))
    for index, (x, y, w) in enumerate(((20, 236, 300), (970, 183, 275), (60, 630, 290), (1040, 586, 290))):
        points = [(x, y + 18), (x + w * .12, y + 11), (x + w * .28, y + 12),
                  (x + w * .40, y), (x + w * .57, y + 7), (x + w * .68, y + 5),
                  (x + w * .82, y + 15), (x + w, y + 19), (x + w * .85, y + 27),
                  (x + w * .32, y + 28)]
        pygame.draw.polygon(background, (196 + index * 3, 219 + index * 2, 218 + index * 2),
                            [point(px, py) for px, py in points])

    island_image = (landscape or {}).get("island_base")
    if island_image is not None:
        draw_island_image(city, rect(96, 345, 1088, 384), island_image)
    else:
        draw_island(city, rect(96, 353, 1088, 171), cliff_height=round(212 * factor))
    layout = showcase_layout(placed)
    # Low-contrast connected beds replace per-slot colored footprints.
    for cell, kind in sorted(placed.items()):
        x, y, _ = layout[cell]
        phase = cell[0] * 5 + cell[1] * 11
        if kind in {"forest", "garden"}:
            color = (156, 179 + phase % 6, 143)
            for other in neighbors(cell):
                if other not in layout or cell >= other or placed[other] not in {"forest", "garden"}:
                    continue
                ox, oy, _ = layout[other]
                path = _curve(((x, y + 3), (x + (ox - x) * .35, y + 6),
                               (ox, oy - 5), (ox, oy + 3)))
                line(color, path, 24)
            points = []
            for index in range(20):
                angle = index * math.tau / 20
                radius = 1 + math.sin(index * 2.1 + phase) * .12
                points.append((x + math.cos(angle) * 65 * radius,
                               y + 3 + math.sin(angle) * 18 * radius))
            polygon(color, points)
        elif kind in {"cloud", "waterfall"}:
            pygame.draw.ellipse(city, (156, 191, 179), rect(x - 34, y - 6, 68, 16))
            if kind == "waterfall":
                line((207, 232, 210), _curve(((x - 21, y), (x - 9, y + 8),
                                           (x + 19, y - 4), (x + 27, y + 2))), 2)

    for cell, kind in sorted(placed.items()):
        if kind not in {"garden", "residents", "bridge", "harbor", "core"}:
            continue
        x, y, _ = layout[cell]
        near = [other for other in neighbors(cell) if other in placed and cell < other
                and placed[other] not in {"cloud", "waterfall"}]
        for other in near[:2]:
            ox, oy, _ = layout[other]
            path = _curve(((x, y + 5), (x + (ox - x) * .3, y + 13),
                           (ox - (ox - x) * .2, oy - 7), (ox, oy + 3)))
            line((97, 133, 119), path, 7)
            line((211, 216, 176), path, 4)

    # The island itself falls beneath the city. Generated cutouts replace the
    # old procedural circles and stripes, while still merging multiple cells
    # into one continuous cloud sea and a few deliberate waterfall accents.
    landscape = landscape or {}
    cloud_cells = sorted(cell for cell, kind in placed.items() if kind == "cloud")
    cloud_image = landscape.get("cloud")
    if cloud_cells and cloud_image is not None:
        cloud_x = sum(layout[cell][0] for cell in cloud_cells) / len(cloud_cells)
        cloud_y = sum(layout[cell][1] for cell in cloud_cells) / len(cloud_cells)
        cloud_width = min(720, max(330, 275 + len(cloud_cells) * 48))
        cloud_height = round(cloud_width * 0.31)
        bank = _landscape_sprite(cloud_image, width=cloud_width * factor,
                                 height=cloud_height * factor)
        if bank:
            target = point(cloud_x, cloud_y + 7)
            city.blit(bank, (round(target[0] - bank.get_width() / 2),
                             round(target[1] - bank.get_height())))

    # The streams carry surface water through the cliff face instead of each
    # water tile becoming another tower. They hang below the front elevation,
    # with the small painted ledge tucked into the island edge.
    outlets = sorted((cell for cell, kind in placed.items() if kind == "waterfall"),
                     key=lambda cell: (-cell[0], cell[1]))[:3]
    waterfall_image = landscape.get("waterfall")
    for index, cell in enumerate(outlets):
        x, _, _ = layout[cell]
        x += (-23, 25, 0)[index]
        if waterfall_image is not None:
            stream_height = (224 - index * 18) * factor
            stream = _landscape_sprite(waterfall_image, height=stream_height)
            if stream:
                target = point(x, 692 - index * 24)
                city.blit(stream, (round(target[0] - stream.get_width() / 2),
                                   round(target[1] - stream.get_height())))
        else:
            end = 650 - index * 37
            flow = _curve(((x, 512), (x + 7, 560), (x - 15, end - 24), (x - 8, end)))
            line((79, 143, 157), flow, 17)
            line((149, 208, 209), flow, 11)
            line((216, 239, 222), [(px - 2, py) for px, py in flow], 3)

    for cell in sorted(placed, key=lambda entry: (layout[entry][1], layout[entry][0])):
        kind = placed[cell]
        x, y, height = layout[cell]
        dx, dy = jitter.get(cell, (0, 0))
        x += dx
        y += dy
        variant = variants.get(cell, 0)
        if kind == "cloud":
            # Cloud cells are represented by the one continuous painted bank.
            continue
        # Most forest cells are low canopy; a few trees carry the skyline.
        if kind == "forest":
            peers = sorted(c for c, value in placed.items() if value == kind)
            if cell not in peers[:5]:
                height = round(height * 0.62)
        sprite = _sprite(images, kind, variant, max(1, round(height * factor)))
        if sprite is None:
            continue
        if kind == "waterfall":
            # Only two water arches act as skyline accents; others read as pools.
            peers = sorted(c for c, value in placed.items() if value == kind)
            if cell not in peers[:2]:
                line((199, 229, 216), ((x - 28, y - 2), (x - 4, y + 4), (x + 25, y)), 3)
                continue
        foot = point(x, y)
        bounds = sprite.get_bounding_rect(min_alpha=10)
        draw_x = round(foot[0] - bounds.centerx)
        draw_y = round(foot[1] - bounds.bottom)
        city.blit(sprite, (draw_x, draw_y))
        if kind == "forest":
            line((124, 144, 95), ((x - 21, y), (x - 16, y - 7), (x - 12, y)), 2)
        elif kind not in GROUND_KINDS:
            line((150, 167, 129), ((x - 13, y + 1), (x + 15, y + 1)), 2)

    combination_assets = combination_assets or {}
    combo_matches = combo_matches or {}
    for combo_id, asset_name, width, y_offset in (
        ("spring_grove", "spring", 112, -18),
        ("bridge_hamlet", "hamlet", 116, -32),
    ):
        cells = combo_matches.get(combo_id)
        if not cells:
            continue
        xs = [layout[cell][0] + jitter.get(cell, (0, 0))[0] for cell in cells]
        ys = [layout[cell][1] + jitter.get(cell, (0, 0))[1] for cell in cells]
        sprite = _landscape_sprite(combination_assets.get(asset_name), width=width * factor)
        if sprite:
            target = point(sum(xs) / len(xs), sum(ys) / len(ys) + y_offset)
            city.blit(sprite, (round(target[0] - sprite.get_width() / 2),
                               round(target[1] - sprite.get_height() / 2)))

    route = combo_matches.get("sky_route")
    if route:
        coords = [(layout[cell][0] + jitter.get(cell, (0, 0))[0],
                   layout[cell][1] + jitter.get(cell, (0, 0))[1] - 28) for cell in route]
        points = _curve((coords[0], (coords[0][0] + 18, coords[0][1] - 42),
                         (coords[2][0] - 18, coords[2][1] - 44), coords[2]))
        line((230, 192, 117, 150), points, 3)
        line((217, 229, 190, 180), points, 1)
        sprite = _landscape_sprite(combination_assets.get("airway"), width=172 * factor)
        if sprite:
            middle = points[len(points) // 2]
            target = point(*middle)
            city.blit(sprite, (round(target[0] - sprite.get_width() / 2),
                               round(target[1] - sprite.get_height() / 2)))

    return background, city
