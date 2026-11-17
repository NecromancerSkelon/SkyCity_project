"""Pure spatial rules for the 36-slot floating city."""

ZONE_NAMES = {"high": "高位", "edge": "边缘", "center": "中心"}
STYLE_NAMES = {
    "natural": "自然", "industrial": "工业", "living": "生活", "hybrid": "融合",
}
STYLES = {
    "natural": {"name": "自然", "color": (116, 179, 121)},
    "industrial": {"name": "工业", "color": (230, 178, 92)},
    "living": {"name": "生活", "color": (224, 141, 151)},
}

TASKS = (
    {"id": "grove", "name": "泉林共生", "description": "让 2 座森林台邻接云海或悬瀑", "target": 2, "reward": {"structure": 2}},
    {"id": "skyline", "name": "天际之风", "description": "在高位接入 2 座风塔、日晷站或观星台", "target": 2, "reward": {"light": 2}},
    {"id": "district", "name": "多彩街区", "description": "让 5 种不同结构接入核心网络", "target": 5, "reward": {"resonance": 2}},
)

COMBINATIONS = (
    {"id": "spring_grove", "name": "泉林共鸣", "description": "云海邻接悬瀑，森林台再接入其中一座。", "parts": ("cloud", "waterfall", "forest"), "reward": {"structure": 2}, "accent": "spring"},
    {"id": "sky_route", "name": "天际航路", "description": "风塔与日晷站相邻，云港接入这条能源航路。", "parts": ("wind", "sundial", "harbor"), "reward": {"light": 2}, "accent": "airway"},
    {"id": "bridge_hamlet", "name": "桥畔聚落", "description": "桥廊分别连接空中花园与居民环。", "parts": ("bridge", "garden", "residents"), "reward": {"resonance": 2}, "accent": "hamlet"},
)

_STYLE_KINDS = {
    "natural": {"cloud", "waterfall", "forest", "garden"},
    "industrial": {"wind", "sundial", "gear", "harbor", "bridge"},
    "living": {"forest", "garden", "residents", "bridge"},
}
_STYLE_PAIRS = {
    "natural": {frozenset(pair) for pair in (
        ("cloud", "waterfall"), ("cloud", "forest"), ("waterfall", "forest"),
        ("forest", "garden"), ("waterfall", "garden"),
    )},
    "industrial": {frozenset(pair) for pair in (
        ("wind", "sundial"), ("wind", "gear"), ("sundial", "gear"),
        ("gear", "harbor"), ("bridge", "harbor"),
    )},
    "living": {frozenset(pair) for pair in (
        ("forest", "garden"), ("forest", "residents"),
        ("garden", "residents"), ("bridge", "residents"), ("bridge", "garden"),
    )},
}


def zones_for(cell):
    """Return ordered, possibly overlapping labels for a valid board cell."""
    row, col = cell
    if not 0 <= row <= 10:
        return ()
    width = 1 + min(row, 10 - row)
    if not 0 <= col < width:
        return ()
    zones = []
    if row <= 3:
        zones.append("high")
    is_edge = col == 0 or col == width - 1
    if is_edge:
        zones.append("edge")
    if 4 <= row <= 6 and not is_edge:
        zones.append("center")
    return tuple(zones)


def position_bonus(cell, kind):
    """Action-settlement bonus; no production is awarded just for waiting."""
    zones = zones_for(cell)
    if "high" in zones and kind in {"wind", "sundial", "observatory"}:
        return {"light": 1}
    if "edge" in zones and kind in {"cloud", "waterfall"}:
        return {"vapor": 1}
    if "edge" in zones and kind in {"bridge", "harbor"}:
        return {"structure": 1}
    if "center" in zones and kind in {"forest", "garden", "residents"}:
        return {"resonance": 1}
    return {}


def position_description(kind):
    if kind in {"wind", "sundial", "observatory"}:
        return "高位：额外光能 +1"
    if kind in {"cloud", "waterfall"}:
        return "边缘：额外水汽 +1"
    if kind in {"bridge", "harbor"}:
        return "边缘：额外结构 +1"
    if kind in {"forest", "garden", "residents"}:
        return "中心：额外共鸣 +1"
    return "无位置加成"


def task_progress(task_id, placed, connected, neighbors):
    """Count only connected structures; a water neighbor must also be connected."""
    live = {cell: kind for cell, kind in placed.items() if cell in connected}
    if task_id == "grove":
        count = sum(
            kind == "forest" and any(
                live.get(other) in {"cloud", "waterfall"} for other in neighbors(cell)
            )
            for cell, kind in live.items()
        )
    elif task_id == "skyline":
        count = sum(
            "high" in zones_for(cell) and kind in {"wind", "sundial", "observatory"}
            for cell, kind in live.items()
        )
    elif task_id == "district":
        count = len(set(live.values()))
    else:
        raise ValueError("Unknown city task: " + str(task_id))
    target = next(task["target"] for task in TASKS if task["id"] == task_id)
    return min(target, count)


def find_combinations(placed, connected, neighbors):
    """Return the first deterministic connected match for each spatial set."""
    live = {cell: kind for cell, kind in placed.items() if cell in connected}
    matches = {}
    for combo in COMBINATIONS:
        cells = None
        if combo["id"] == "spring_grove":
            for waterfall in sorted(c for c, kind in live.items() if kind == "waterfall"):
                for cloud in sorted(n for n in neighbors(waterfall) if live.get(n) == "cloud"):
                    forests = sorted(c for c, kind in live.items() if kind == "forest"
                                     and c not in {cloud, waterfall}
                                     and (c in neighbors(cloud) or c in neighbors(waterfall)))
                    if forests:
                        cells = (cloud, waterfall, forests[0])
                        break
                if cells:
                    break
        elif combo["id"] == "sky_route":
            for wind in sorted(c for c, kind in live.items() if kind == "wind"):
                for sundial in sorted(n for n in neighbors(wind) if live.get(n) == "sundial"):
                    harbors = sorted(c for c, kind in live.items() if kind == "harbor"
                                     and c not in {wind, sundial}
                                     and (c in neighbors(wind) or c in neighbors(sundial)))
                    if harbors:
                        cells = (wind, sundial, harbors[0])
                        break
                if cells:
                    break
        else:
            for bridge in sorted(c for c, kind in live.items() if kind == "bridge"):
                gardens = sorted(n for n in neighbors(bridge) if live.get(n) == "garden")
                residents = sorted(n for n in neighbors(bridge) if live.get(n) == "residents")
                if gardens and residents:
                    cells = (bridge, gardens[0], residents[0])
                    break
        if cells:
            matches[combo["id"]] = cells
    return matches


def style_scores(placed, connected, neighbors):
    """Each style earns 0..15: diversity 0..6, complementary edges 0..6, placement 0..3.

    Diversity is nearest-integer 6 * min(distinct kinds, 4) / 4 (halves round up).
    Each undirected complementary edge earns 2, capped at 6; same-kind edges earn 0.
    Each building in a position-bonus slot earns 1, capped at 3. Disconnected cells
    never contribute. All styles therefore use the same targets, including the
    five-kind industrial branch, and repeated copies cannot replace diversity.
    """
    live = {cell: kind for cell, kind in placed.items() if cell in connected}
    results = {}
    for style, kinds in _STYLE_KINDS.items():
        members = {cell: kind for cell, kind in live.items() if kind in kinds}
        distinct = min(4, len(set(members.values())))
        diversity = (6 * distinct + 2) // 4
        edges = {
            frozenset((cell, other))
            for cell, kind in members.items()
            for other in neighbors(cell)
            if other in members and frozenset((kind, members[other])) in _STYLE_PAIRS[style]
        }
        layout = sum(bool(position_bonus(cell, kind)) for cell, kind in members.items())
        results[style] = diversity + min(6, 2 * len(edges)) + min(3, layout)
    return results


def dominant_style(scores):
    highest = max((scores.get(style, 0) for style in STYLES), default=0)
    winners = [style for style in STYLES if scores.get(style, 0) == highest]
    return winners[0] if highest > 0 and len(winners) == 1 else "hybrid"
