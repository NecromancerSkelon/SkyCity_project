import math
import os
import random
import sys
import ctypes
from datetime import datetime
from collections import defaultdict

import pygame

from island_art import draw_island, draw_island_image
from scene_art import build_showcase, clear_scene_cache
from building_quotes import get_building_quote
from ending_text import get_ending

from city_rules import (TASKS, COMBINATIONS, STYLES, STYLE_NAMES, ZONE_NAMES, dominant_style,
                        position_bonus, position_description, style_scores,
                        task_progress, find_combinations, zones_for)


WIDTH, HEIGHT = 1280, 800
FPS = 60
BOARD_RECT = pygame.Rect(18, 54, 704, 680)
PANEL_RECT = pygame.Rect(726, 26, 520, 748)
BG_TOP = (17, 37, 70)
BG_BOTTOM = (83, 145, 169)
INK = (23, 45, 67)
CREAM = (249, 241, 213)
MUTED = (151, 190, 197)
GOLD = (245, 192, 91)
CORAL = (234, 113, 100)
TEAL = (84, 187, 178)

TILE_INFO = {
    "cloud": {"name": "云海", "tag": "水 · 自然", "desc": "收集水汽", "cost": {"structure": 1}, "guide": "基础水汽来源。适合先放在中心附近，为悬瀑与自然联动提供输入。", "color": (174, 216, 224)},
    "core": {"name": "浮岛核心", "tag": "核心 · 结构", "desc": "建设脉冲", "cost": {}, "guide": "首次结算产结构 2。每个新地块首次接入城市时，额外提供结构 1；不随等待重复生产。", "color": (238, 189, 91)},
    "wind": {"name": "风塔", "tag": "风 · 能源", "desc": "收集光能", "cost": {"vapor": 1}, "guide": "基础光能来源。靠近日晷站或桥廊时，能源网络更容易成形。", "color": (85, 187, 181)},
    "waterfall": {"name": "悬瀑", "tag": "水 · 流动", "desc": "大量水汽", "cost": {"structure": 1, "vapor": 1}, "guide": "强化水汽产出。与云海相邻时，适合建立自然路线。", "color": (104, 181, 219)},
    "sundial": {"name": "日晷站", "tag": "时间 · 能源", "desc": "稳定光能", "cost": {"structure": 1, "light": 1}, "guide": "把风塔的光能变得稳定，适合放在能源地块的中间。", "color": (236, 161, 74)},
    "forest": {"name": "森林台", "tag": "自然 · 生命", "desc": "水系邻接产结构", "cost": {"vapor": 2}, "guide": "基础产出共鸣 1；邻接云海或悬瀑额外产出结构 2。自然路线的扩建来源。", "color": (101, 174, 114)},
    "gear": {"name": "齿轮厂", "tag": "工业 · 结构", "desc": "生产结构", "cost": {"light": 2, "vapor": 1}, "guide": "消耗光能生产结构，是第一次扩建的重要准备。", "color": (189, 136, 91)},
    "bridge": {"name": "桥廊", "tag": "连接 · 结构", "desc": "港口联动", "cost": {"structure": 2, "light": 1}, "guide": "基础产结构 1、共鸣 1；邻接云港额外产结构 1、光能 1。用于连接城市外环。", "color": (188, 162, 109)},
    "residents": {"name": "居民环", "tag": "生活 · 共鸣", "desc": "点亮城市", "cost": {"vapor": 1, "resonance": 1}, "guide": "基础产共鸣 2；邻接森林台或空中花园额外产共鸣 1。组成生活套装可提高最终评分。", "color": (224, 129, 111)},
    "harbor": {"name": "云港", "tag": "贸易 · 连接", "desc": "外环联动", "cost": {"structure": 2, "light": 2}, "guide": "基础产结构 1、光能 1；邻接桥廊额外产结构 1。与观星台组成终局网络。", "color": (102, 163, 188)},
    "garden": {"name": "空中花园", "tag": "生命 · 生活", "desc": "自然套装", "cost": {"vapor": 2, "resonance": 2}, "guide": "基础产共鸣 2；邻接森林台额外产结构 1、共鸣 1。自然套装同样可以完成城市。", "color": (140, 189, 116)},
    "observatory": {"name": "观星台", "tag": "观测 · 共鸣", "desc": "终局地标", "cost": {"structure": 2, "light": 3, "resonance": 2}, "guide": "终局地标。留出高处或边缘的清晰轮廓，获得更高构成分。", "color": (156, 138, 193)},
}
TILE_IMAGES = {}
LANDSCAPE_IMAGES = {}
COMBINATION_IMAGES = {}

REWARDS = {
    "cloud": {"vapor": 1}, "core": {"structure": 2}, "wind": {"light": 1},
    "waterfall": {"vapor": 2}, "sundial": {"light": 2}, "forest": {"resonance": 1},
    "gear": {"structure": 2}, "bridge": {"structure": 1, "resonance": 1},
    "residents": {"resonance": 2}, "harbor": {"structure": 1, "light": 1},
    "garden": {"resonance": 2}, "observatory": {"resonance": 3},
}

TECH_TREE = {
    "waterfall": {"cost": 3, "parents": ("cloud",), "column": 0, "row": 0},
    "forest": {"cost": 4, "parents": ("waterfall",), "column": 0, "row": 1},
    "garden": {"cost": 5, "parents": ("forest",), "column": 0, "row": 2},
    "sundial": {"cost": 3, "parents": ("wind",), "column": 1, "row": 0},
    "gear": {"cost": 4, "parents": ("sundial",), "column": 1, "row": 1},
    "harbor": {"cost": 5, "parents": ("gear",), "column": 1, "row": 2},
    "bridge": {"cost": 4, "parents": ("forest", "gear"), "column": 2, "row": 1},
    "residents": {"cost": 4, "parents": ("forest", "gear"), "column": 2, "row": 2},
    "observatory": {"cost": 6, "parents": ("garden", "harbor"), "column": 1, "row": 3, "expansions": 2},
}
# Each pair is symmetric and counts once for the final network score.
SYNERGY_PAIRS = {
    frozenset(pair) for pair in (
        ("cloud", "waterfall"), ("cloud", "forest"), ("waterfall", "forest"),
        ("forest", "garden"), ("forest", "residents"), ("garden", "residents"),
        ("wind", "sundial"), ("wind", "gear"), ("sundial", "gear"),
        ("bridge", "harbor"), ("harbor", "observatory"),
    )
}
TECH_BUTTON = pygame.Rect(1090, 120, 118, 34)
SUPPLY_PREV = pygame.Rect(1104, 420, 42, 28)
SUPPLY_NEXT = pygame.Rect(1166, 420, 42, 28)
CITY_BUTTON = pygame.Rect(1090, 166, 118, 34)
RELOCATE_BUTTON = pygame.Rect(1090, 207, 118, 34)
VIEW_BUTTON = pygame.Rect(578, 77, 126, 30)
SHOWCASE_BACK = pygame.Rect(1080, 44, 142, 34)
SHOWCASE_EXPORT = pygame.Rect(952, 44, 112, 34)
SHOWCASE_SCORE = pygame.Rect(824, 44, 112, 34)
SHOWCASE_VISION = pygame.Rect(696, 44, 112, 34)

# Ground forms provide negative space; only landmarks carry the skyline.
BUILDING_SCALE = {
    "cloud": 0.38, "forest": 0.59, "waterfall": 0.63, "bridge": 0.54,
    "garden": 0.74, "residents": 0.80, "gear": 0.83, "harbor": 0.87,
    "sundial": 0.91, "wind": 1.12, "core": 1.20, "observatory": 1.32,
}
GROUND_KINDS = {"cloud", "forest", "waterfall"}

TUTORIAL_STEPS = [
    ("先看懂浮岛", "棋盘共有 36 个灰色菱形地块。亮边框代表当前可以插装的位置，深灰色地块需要扩建后才能使用。", "下一步"),
    ("搭建第一座城市", "点击结构卡，再点击亮起的空位。约 2 秒完成结算；每次有效建设，核心额外提供 1 点结构。已解锁建筑可以随时选择。", "下一步"),
    ("卡片有成本", "每张结构卡都有资源成本。放置前先看卡片底部的成本条，资源不足时卡片会提醒你先生产对应资源。", "下一步"),
    ("科技与自然路线", "灵感碎片用于研究科技，分支可以兼修。森林台邻接云海或悬瀑会产出结构，不依赖工业也能扩建。", "下一步"),
    ("拆除，重新布局", "右键场上建筑可以拆除并返还部分成本。填满 36 格并结算最后一笔资源后，城市将获得最终评分。", "下一步"),
    ("给城市一个方向", "选中卡片时，金色空位有位置奖励。愿景提供可选目标；一次重构可免费迁移一座建筑。构图预览能查看高低层次。", "开始搭建"),
]

CORE_ZONE = {(5, 2), (5, 3)}
RESOURCE_NAMES = {"light": "光能", "vapor": "水汽", "structure": "结构", "resonance": "共鸣"}
RESOURCE_SHORT = {"light": "光", "vapor": "水", "structure": "构", "resonance": "鸣"}


def make_cells():
    return [(row, col) for row in range(11) for col in range(1 + min(row, 10 - row))]


CELLS = make_cells()
NEIGHBOR_DIRS = ((1, 0), (-1, 0), (0, 1), (0, -1), (1, -1), (-1, 1))


def font(size, bold=False):
    candidates = [
        r"C:\Windows\Fonts\msyhbd.ttc" if bold else r"C:\Windows\Fonts\msyhl.ttc",
        r"C:\Windows\Fonts\msyh.ttc",
        r"C:\Windows\Fonts\simhei.ttf",
        r"C:\Windows\Fonts\segoeui.ttf",
    ]
    for path in candidates:
        if os.path.exists(path):
            return pygame.font.Font(path, size)
    return pygame.font.SysFont("Arial", size, bold=bold)


FONTS = {}
TEXT_TARGET = None
TEXT_SCALE = 1.0
TEXT_OFFSET = (0, 0)


def text(screen, value, pos, size=18, color=CREAM, bold=False, anchor="topleft"):
    target = TEXT_TARGET if TEXT_TARGET is not None else screen
    render_size = max(1, int(round(size * TEXT_SCALE))) if TEXT_TARGET is not None else size
    render_pos = (
        TEXT_OFFSET[0] + pos[0] * TEXT_SCALE,
        TEXT_OFFSET[1] + pos[1] * TEXT_SCALE,
    ) if TEXT_TARGET is not None else pos
    key = (render_size, bold)
    if key not in FONTS:
        FONTS[key] = font(render_size, bold)
    surf = FONTS[key].render(str(value), True, color)
    rect = surf.get_rect()
    setattr(rect, anchor, render_pos)
    target.blit(surf, rect)
    return rect


def text_fit(screen, value, pos, max_width, size=18, color=CREAM, bold=False, anchor="topleft", min_size=9):
    """Render one line at the largest readable size that fits its column."""
    value = str(value)
    chosen = max(min_size, size)
    for candidate in range(size, min_size - 1, -1):
        key = (candidate, bold)
        if key not in FONTS:
            FONTS[key] = font(candidate, bold)
        if FONTS[key].size(value)[0] <= max_width:
            chosen = candidate
            break
    return text(screen, value, pos, chosen, color, bold, anchor)


def text_wrap(value, size, max_width, bold=False):
    """Wrap mixed Chinese and Latin text by rendered width, preserving words."""
    value = str(value)
    face = font(size, bold)
    lines = []
    line = ""
    for char in value:
        if char == "\n":
            lines.append(line)
            line = ""
            continue
        candidate = line + char
        if line and face.size(candidate)[0] > max_width:
            lines.append(line)
            line = char
        else:
            line = candidate
    if line or not lines:
        lines.append(line)
    return lines


def rounded(screen, rect, color, radius=12, border=None, width=1):
    pygame.draw.rect(screen, color, rect, border_radius=radius)
    if border:
        pygame.draw.rect(screen, border, rect, width, border_radius=radius)


def diamond(center, rx, ry):
    x, y = center
    return [(x, y - ry), (x + rx, y), (x, y + ry), (x - rx, y)]


def draw_slot_icon(surface, center, kind, alpha=220):
    """Small placement preview that stays inside the enlarged diamond slot."""
    cx, cy = int(center[0]), int(center[1])
    color = TILE_INFO[kind]["color"]
    ink = (*color, alpha)
    pygame.draw.polygon(surface, (52, 83, 92), diamond((cx, cy), 28, 17))
    pygame.draw.polygon(surface, (232, 220, 178), diamond((cx, cy), 27, 16), 2)
    if kind == "cloud":
        for dx, dy, radius in ((-12, 2, 8), (-2, -4, 10), (9, 2, 8)):
            pygame.draw.circle(surface, ink, (cx + dx, cy + dy), radius)
        pygame.draw.line(surface, (220, 244, 245, alpha), (cx - 14, cy + 8), (cx + 16, cy + 8), 3)
    elif kind == "core":
        pygame.draw.circle(surface, (255, 213, 112, alpha), (cx, cy - 3), 8)
        pygame.draw.arc(surface, (139, 102, 62, alpha), (cx - 14, cy - 16, 28, 27), 0.2, 2.9, 3)
    elif kind == "wind":
        pygame.draw.line(surface, ink, (cx, cy + 11), (cx, cy - 11), 3)
        for end in ((cx, cy - 13), (cx - 12, cy + 1), (cx + 12, cy + 1)):
            pygame.draw.line(surface, (239, 224, 174, alpha), (cx, cy - 7), end, 3)
        pygame.draw.circle(surface, (249, 216, 132, alpha), (cx, cy - 7), 3)
    elif kind in ("waterfall", "forest", "garden"):
        pygame.draw.polygon(surface, ink, ((cx - 13, cy + 7), (cx - 4, cy - 11), (cx + 5, cy - 4), (cx + 13, cy + 7)))
        pygame.draw.line(surface, (218, 244, 246, alpha), (cx + 2, cy - 1), (cx + 8, cy + 11), 3)
    elif kind in ("gear", "bridge", "harbor"):
        pygame.draw.circle(surface, ink, (cx - 6, cy), 7, 3)
        pygame.draw.circle(surface, (239, 193, 92, alpha), (cx + 7, cy), 6, 3)
        pygame.draw.line(surface, ink, (cx - 13, cy + 9), (cx + 14, cy + 9), 3)
    elif kind in ("sundial", "observatory"):
        pygame.draw.circle(surface, ink, (cx, cy), 10, 3)
        pygame.draw.line(surface, (249, 215, 128, alpha), (cx, cy), (cx + 8, cy - 9), 3)
    else:
        pygame.draw.rect(surface, ink, (cx - 9, cy - 10, 18, 20), 3, border_radius=3)
    pygame.draw.polygon(surface, (245, 192, 91, min(230, alpha)), diamond((cx, cy + 18), 13, 7), 2)


def cell_center(cell):
    row, col = cell
    n = 1 + min(row, 10 - row)
    x = 512 + (col - (n - 1) / 2) * 170
    # The board is a front-facing 2D elevation, so the grid uses even rows
    # rather than a perspective slope. This leaves room for tall structures.
    y = 170 + row * 45
    scale = BOARD_RECT.w / 1024
    return BOARD_RECT.left + x * scale, BOARD_RECT.top + y * scale


def neighbors(cell):
    row, col = cell
    candidates = [(row, col - 1), (row, col + 1)]
    if row < 5:
        candidates.extend(((row - 1, col - 1), (row - 1, col), (row + 1, col), (row + 1, col + 1)))
    elif row > 5:
        candidates.extend(((row - 1, col), (row - 1, col + 1), (row + 1, col - 1), (row + 1, col)))
    else:
        candidates.extend(((row - 1, col - 1), (row - 1, col), (row + 1, col - 1), (row + 1, col)))
    return [candidate for candidate in candidates if candidate in CELLS]


def draw_tile_art(surface, center, kind, scale=1.0, ghost=False, selected=False, tile_scale=None, variant=0, anchor_bottom=False):
    cx, cy = center
    info = TILE_INFO[kind]
    if kind in TILE_IMAGES:
        images = TILE_IMAGES[kind]
        image = images[variant % len(images)] if isinstance(images, list) else images
        size = max(40, int(118 * scale))
        image = pygame.transform.smoothscale(image, (size, size))
        if ghost:
            image = image.copy()
            image.set_alpha(115)
        if anchor_bottom:
            bbox = image.get_bounding_rect()
            draw_x = int(cx - (bbox.left + bbox.width / 2))
            draw_y = int(cy + 3 - bbox.bottom)
        else:
            draw_x = int(cx - size / 2)
            draw_y = int(cy - size / 2)
        surface.blit(image, (draw_x, draw_y))
        if selected:
            pygame.draw.polygon(surface, (*GOLD, 230), diamond((cx, cy + int(9 * scale)), int(42 * scale), int(27 * scale)), max(1, int(3 * scale)))
        return
    alpha = 115 if ghost else 255
    layer = pygame.Surface((int(150 * scale), int(130 * scale)), pygame.SRCALPHA)
    ox, oy = layer.get_width() // 2, layer.get_height() // 2
    def poly(points, color):
        pygame.draw.polygon(layer, (*color, alpha), points)
    tile_scale = scale if tile_scale is None else tile_scale
    rx, ry = int(39 * tile_scale), int(22 * tile_scale)
    poly(diamond((ox, oy + int(16 * tile_scale)), rx, ry), (31, 62, 79))
    poly(diamond((ox, oy + int(9 * tile_scale)), rx, ry), (217, 225, 213))
    if selected:
        pygame.draw.polygon(layer, (*GOLD, 255), diamond((ox, oy + int(9 * tile_scale)), rx + int(4 * tile_scale), ry + int(4 * tile_scale)), max(1, int(3 * scale)))
    c = info["color"]
    def p(points, col=c):
        poly([(ox + int(x * scale), oy + int(y * scale)) for x, y in points], col)
    if kind == "cloud":
        for x, y, r in [(-22, 4, 15), (-7, -4, 19), (10, 1, 15), (24, 7, 11)]:
            pygame.draw.circle(layer, (*c, alpha), (ox + int(x * scale), oy + int(y * scale)), int(r * scale))
        pygame.draw.ellipse(layer, (217, 239, 239, alpha), (ox - int(27 * scale), oy - int(2 * scale), int(60 * scale), int(19 * scale)))
    elif kind == "core":
        pygame.draw.circle(layer, (*c, alpha), (ox, oy - int(13 * scale)), int(18 * scale))
        pygame.draw.circle(layer, (255, 235, 159, alpha), (ox, oy - int(13 * scale)), int(9 * scale))
        pygame.draw.arc(layer, (139, 102, 62, alpha), (ox - int(29 * scale), oy - int(42 * scale), int(58 * scale), int(58 * scale)), 0.2, 2.9, max(1, int(4 * scale)))
        pygame.draw.line(layer, (143, 109, 70, alpha), (ox - int(25 * scale), oy + int(5 * scale)), (ox + int(25 * scale), oy + int(5 * scale)), max(1, int(5 * scale)))
    elif kind == "wind":
        pygame.draw.rect(layer, (*c, alpha), (ox - int(5 * scale), oy - int(45 * scale), int(10 * scale), int(51 * scale)), border_radius=max(1, int(4 * scale)))
        pygame.draw.circle(layer, (239, 214, 146, alpha), (ox, oy - int(42 * scale)), int(5 * scale))
        for ang in (0, 2.1, 4.2):
            ex = ox + math.cos(ang) * 29 * scale
            ey = oy - int(42 * scale) + math.sin(ang) * 29 * scale
            pygame.draw.line(layer, (236, 227, 180, alpha), (ox, oy - int(42 * scale)), (int(ex), int(ey)), max(1, int(5 * scale)))
    elif kind == "waterfall":
        p([(-24, -12), (-5, -35), (15, -19), (24, 7), (7, 10), (-10, -4)])
        pygame.draw.line(layer, (211, 241, 244, alpha), (ox + int(7 * scale), oy - int(4 * scale)), (ox + int(15 * scale), oy + int(29 * scale)), max(1, int(5 * scale)))
        pygame.draw.line(layer, (211, 241, 244, alpha), (ox + int(17 * scale), oy - int(2 * scale)), (ox + int(24 * scale), oy + int(23 * scale)), max(1, int(3 * scale)))
    elif kind == "sundial":
        pygame.draw.circle(layer, (*c, alpha), (ox, oy - int(16 * scale)), int(23 * scale))
        pygame.draw.circle(layer, (254, 218, 139, alpha), (ox, oy - int(16 * scale)), int(15 * scale), max(1, int(2 * scale)))
        pygame.draw.line(layer, (128, 91, 58, alpha), (ox, oy - int(36 * scale)), (ox, oy + int(5 * scale)), max(1, int(3 * scale)))
    elif kind == "forest" or kind == "garden":
        for x, y, r in [(-19, -3, 14), (0, -18, 18), (20, 0, 15), (2, 2, 19)]:
            pygame.draw.circle(layer, (*c, alpha), (ox + int(x * scale), oy + int(y * scale)), int(r * scale))
        pygame.draw.rect(layer, (115, 92, 62, alpha), (ox - int(4 * scale), oy, int(8 * scale), int(20 * scale)))
        if kind == "garden":
            pygame.draw.circle(layer, (245, 183, 101, alpha), (ox - int(15 * scale), oy - int(11 * scale)), int(4 * scale))
            pygame.draw.circle(layer, (241, 123, 118, alpha), (ox + int(16 * scale), oy - int(1 * scale)), int(4 * scale))
    elif kind == "gear":
        pygame.draw.circle(layer, (*c, alpha), (ox, oy - int(17 * scale)), int(23 * scale))
        pygame.draw.circle(layer, (74, 92, 99, alpha), (ox, oy - int(17 * scale)), int(8 * scale))
        for ang in range(0, 360, 45):
            a = math.radians(ang)
            x1, y1 = ox + math.cos(a) * 22 * scale, oy - int(17 * scale) + math.sin(a) * 22 * scale
            x2, y2 = ox + math.cos(a) * 30 * scale, oy - int(17 * scale) + math.sin(a) * 30 * scale
            pygame.draw.line(layer, (221, 181, 112, alpha), (int(x1), int(y1)), (int(x2), int(y2)), max(1, int(5 * scale)))
    elif kind == "bridge":
        pygame.draw.line(layer, (*c, alpha), (ox - int(31 * scale), oy - int(16 * scale)), (ox + int(31 * scale), oy - int(16 * scale)), max(1, int(9 * scale)))
        pygame.draw.line(layer, (242, 210, 143, alpha), (ox - int(26 * scale), oy - int(26 * scale)), (ox + int(26 * scale), oy - int(26 * scale)), max(1, int(3 * scale)))
        for x in (-20, -7, 7, 20):
            pygame.draw.line(layer, (242, 210, 143, alpha), (ox + int(x * scale), oy - int(26 * scale)), (ox + int(x * scale), oy - int(12 * scale)), max(1, int(2 * scale)))
    elif kind == "residents":
        pygame.draw.arc(layer, (*c, alpha), (ox - int(31 * scale), oy - int(41 * scale), int(62 * scale), int(48 * scale)), math.pi, math.tau, max(1, int(8 * scale)))
        for x in (-22, -8, 8, 22):
            pygame.draw.rect(layer, (255, 214, 133, alpha), (ox + int(x * scale) - int(3 * scale), oy - int(20 * scale), int(6 * scale), int(8 * scale)), border_radius=2)
    elif kind == "harbor":
        p([(-28, 4), (-10, -26), (21, -25), (30, 4), (19, 7), (-13, 7)])
        pygame.draw.arc(layer, (255, 220, 133, alpha), (ox - int(26 * scale), oy - int(33 * scale), int(52 * scale), int(45 * scale)), math.pi, math.tau, max(1, int(3 * scale)))
    elif kind == "observatory":
        pygame.draw.rect(layer, (*c, alpha), (ox - int(25 * scale), oy - int(6 * scale), int(50 * scale), int(18 * scale)), border_radius=4)
        pygame.draw.arc(layer, (216, 196, 229, alpha), (ox - int(26 * scale), oy - int(42 * scale), int(52 * scale), int(58 * scale)), math.pi, math.tau, max(1, int(9 * scale)))
        pygame.draw.line(layer, (249, 230, 167, alpha), (ox - int(3 * scale), oy - int(34 * scale)), (ox + int(30 * scale), oy - int(50 * scale)), max(1, int(5 * scale)))
    surface.blit(layer, (int(cx - layer.get_width() / 2), int(cy - layer.get_height() / 2)))


class SkyCity:
    def __init__(self):
        if sys.platform == "win32":
            try:
                ctypes.windll.shcore.SetProcessDpiAwareness(2)
            except Exception:
                try:
                    ctypes.windll.user32.SetProcessDPIAware()
                except Exception:
                    pass
        pygame.init()
        pygame.display.set_caption("天空之城 · 浮空构成")
        self.display = pygame.display.set_mode((0, 0), pygame.FULLSCREEN)
        self.display_size = self.display.get_size()
        self.screen = pygame.Surface((WIDTH, HEIGHT)).convert()
        self.text_layer = pygame.Surface(self.display_size, pygame.SRCALPHA)
        self.modal_text_layer = pygame.Surface(self.display_size, pygame.SRCALPHA)
        self.clock = pygame.time.Clock()
        self.running = True
        self.reset()
        # The board remains code-drawn and crisp, while the formal transparent
        # sprites are loaded per kind; a placed tile chooses one variant once
        # and keeps it, while the card preview remains deterministic.
        TILE_IMAGES.clear()
        LANDSCAPE_IMAGES.clear()
        COMBINATION_IMAGES.clear()
        clear_scene_cache()
        asset_root = os.path.join(os.path.dirname(os.path.abspath(__file__)), "generated_assets")
        for kind in TILE_INFO:
            images = []
            for variant_name in ("v01", "v02", "v03", "v04"):
                asset_path = os.path.join(asset_root, kind, f"{kind}_{variant_name}.png")
                if os.path.exists(asset_path):
                    images.append(pygame.image.load(asset_path).convert_alpha())
            if images:
                TILE_IMAGES[kind] = images
        for name in ("cloud_bank", "waterfall"):
            asset_path = os.path.join(asset_root, "landscape", f"{name}.png")
            if os.path.exists(asset_path):
                LANDSCAPE_IMAGES["cloud" if name == "cloud_bank" else "waterfall"] = pygame.image.load(asset_path).convert_alpha()
        asset_path = os.path.join(asset_root, "landscape", "island_base.png")
        if os.path.exists(asset_path):
            LANDSCAPE_IMAGES["island_base"] = pygame.image.load(asset_path).convert_alpha()
        asset_path = os.path.join(asset_root, "landscape", "board_base.png")
        if os.path.exists(asset_path):
            LANDSCAPE_IMAGES["board_base"] = pygame.image.load(asset_path).convert_alpha()
        for name in ("spring", "airway", "hamlet"):
            asset_path = os.path.join(asset_root, "combinations", f"{name}.png")
            if os.path.exists(asset_path):
                COMBINATION_IMAGES[name] = pygame.image.load(asset_path).convert_alpha()

    def reset(self):
        self.active = set(sorted(CELLS, key=lambda c: abs(c[0] - 5) + abs(c[1] - (1 + min(c[0], 10 - c[0]) - 1) / 2))[:18])
        self.placed = {}
        self.placed_variants = {}
        self.placed_jitter = {}
        self.unlocked = ["cloud", "core", "wind"]
        self.hand = ["cloud", "core", "wind"]
        self.supply_page = 0
        self.selected = None
        self.resources = defaultdict(int)
        self.fragments = 0
        self.tech_open = False
        self.tech_feedback = ""
        self.tech_hint_shown = False
        self.inspired_cells = set()
        self.settled_builds = set()
        self.expansions = 0
        self.toast = "先放置浮岛核心，让城市有一个心脏"
        self.toast_timer = 4.0
        self.pending = []
        self.particles = []
        self.pulse = 0.0
        self.score = 0
        self.score_breakdown = {}
        self.finished = False
        self.result_visible = False
        self.city_open = False
        self.claimed_tasks = set()
        self.claimed_combinations = set()
        self.city_page = "visions"
        self.relocation_available = True
        self.relocation_mode = False
        self.relocation_source = None
        self.view_mode = "art"
        self.final_style_scores = {}
        self.showcase_cache_key = None
        self.showcase_layers = None
        self.gallery_feedback = ""
        self.tutorial_step = 0

    def refill_hand(self):
        """Research unlocks a reusable supply, not a randomly inaccessible card."""
        self.hand = [kind for kind in self.unlocked if kind != "core" or not self.has_core()]
        self.supply_page = min(self.supply_page, max(0, (len(self.hand) - 1) // 3))

    def visible_hand(self):
        return self.hand[self.supply_page * 3:self.supply_page * 3 + 3]

    def modal_open(self):
        return self.tutorial_step is not None or self.tech_open or self.result_visible or self.city_open

    def connected_cells(self, placed=None):
        placed = self.placed if placed is None else placed
        connected = {cell for cell, kind in placed.items() if kind == "core"}
        frontier = list(connected)
        while frontier:
            for neighbor in neighbors(frontier.pop()):
                if neighbor in placed and neighbor not in connected:
                    connected.add(neighbor)
                    frontier.append(neighbor)
        return connected

    def placed_count(self, kind):
        return sum(1 for value in self.placed.values() if value == kind)

    def can_pay(self, kind):
        return all(self.resources[name] >= amount for name, amount in TILE_INFO[kind].get("cost", {}).items())

    def cost_text(self, kind):
        cost = TILE_INFO[kind].get("cost", {})
        if not cost:
            return "免费"
        return "  ".join(f"{RESOURCE_NAMES[name]} {amount}" for name, amount in cost.items())

    def short_cost_text(self, kind):
        cost = TILE_INFO[kind].get("cost", {})
        if not cost:
            return "无需消耗"
        return "  ".join(f"{RESOURCE_SHORT[name]}{amount}" for name, amount in cost.items())

    def missing_cost(self, kind):
        return next((f"{RESOURCE_NAMES[name]} {amount - self.resources[name]}" for name, amount in TILE_INFO[kind].get("cost", {}).items() if self.resources[name] < amount), "")

    def pay_cost(self, kind):
        for name, amount in TILE_INFO[kind].get("cost", {}).items():
            self.resources[name] -= amount

    def refund_cost(self, kind, unsettled=False):
        for name, amount in TILE_INFO[kind].get("cost", {}).items():
            self.resources[name] += amount if unsettled else amount // 2

    def has_core(self):
        return self.placed_count("core") > 0

    def adjacency_links(self):
        links = 0
        for cell in self.placed:
            links += sum(1 for neighbor in neighbors(cell) if neighbor in self.placed)
        return links // 2

    def settled_layout(self):
        pending_cells = {item["cell"] for item in self.pending}
        return {cell: kind for cell, kind in self.placed.items() if cell not in pending_cells}

    def city_tasks(self):
        placed = self.settled_layout()
        connected = self.connected_cells(placed)
        return [(task, task_progress(task["id"], placed, connected, neighbors)) for task in TASKS]

    def check_tasks(self):
        completed = []
        for task, progress in self.city_tasks():
            if task["id"] not in self.claimed_tasks and progress >= task["target"]:
                self.claimed_tasks.add(task["id"])
                for resource, amount in task["reward"].items():
                    self.resources[resource] += amount
                completed.append(task["name"])
        if completed:
            self.toast = "城市愿景达成 · " + " / ".join(completed)
            self.toast_timer = 3
        return completed

    def city_combinations(self):
        placed = self.settled_layout()
        connected = self.connected_cells(placed)
        matches = find_combinations(placed, connected, neighbors)
        return [(combo, matches.get(combo["id"])) for combo in COMBINATIONS]

    def check_combinations(self):
        completed = []
        for combo, cells in self.city_combinations():
            if cells and combo["id"] not in self.claimed_combinations:
                self.claimed_combinations.add(combo["id"])
                for resource, amount in combo["reward"].items():
                    self.resources[resource] += amount
                completed.append(combo["name"])
        if completed:
            prefix = "城市愿景达成 · " if self.toast.startswith("城市愿景达成 · ") and self.toast_timer > 0 else ""
            self.toast = prefix + "发现组合 · " + " / ".join(completed)
            self.toast_timer = 3
        return completed

    def city_style_scores(self):
        placed = self.settled_layout()
        return style_scores(placed, self.connected_cells(placed), neighbors)

    def begin_relocation(self):
        if self.finished or self.view_mode == "overview" or not self.relocation_available or self.pending:
            self.toast = "本局重构已使用" if not self.relocation_available else "等待当前建筑结算后再重构"
            self.toast_timer = 2.5
            return False
        self.relocation_mode = not self.relocation_mode
        self.relocation_source = None
        self.selected = None
        self.toast = "选择要迁移的建筑，再选择空插槽；核心不可移动" if self.relocation_mode else "已取消重构"
        self.toast_timer = 3
        return True

    def relocation_targets(self):
        source = self.relocation_source
        if not self.relocation_available or source not in self.placed or self.placed[source] == "core" or self.pending or self.finished or self.view_mode == "overview":
            return []
        targets = []
        for target in sorted(self.active - set(self.placed)):
            trial = dict(self.placed)
            trial[target] = trial.pop(source)
            if len(self.connected_cells(trial)) == len(trial):
                targets.append(target)
        return targets

    def relocate(self, source, target):
        if not self.relocation_mode or source != self.relocation_source or target not in self.relocation_targets():
            return False
        kind = self.placed.pop(source)
        self.placed[target] = kind
        self.placed_variants[target] = self.placed_variants.pop(source, 0)
        self.placed_jitter[target] = self.placed_jitter.pop(source, (0, 0))
        # Migration never creates a new settlement, research credit or pulse.
        self.settled_builds.add((target, kind))
        self.inspired_cells.add(target)
        self.relocation_available = False
        self.relocation_mode = False
        self.relocation_source = None
        self.toast = "重构完成 · 原资源与立绘保留，未重复结算"
        self.toast_timer = 3
        return True

    @staticmethod
    def cell_at(pos):
        matches = [cell for cell in CELLS
                   if abs(cell_center(cell)[0] - pos[0]) / 42 + abs(cell_center(cell)[1] - pos[1]) / 25 <= 1]
        return matches[0] if matches else None

    def placement_reward(self, cell, kind):
        if (cell, kind) in self.settled_builds:
            return None
        reward, _ = self.reward_for(cell, kind)
        if cell not in self.inspired_cells and kind != "core":
            reward["structure"] = reward.get("structure", 0) + 1
        return reward

    def valid_cells(self, kind):
        if self.finished or kind not in self.unlocked or not self.can_pay(kind):
            return []
        empty_active = [cell for cell in self.active if cell not in self.placed]
        if kind == "core":
            return [cell for cell in empty_active if cell in CORE_ZONE] if not self.has_core() else []
        if not self.has_core():
            return []
        connected = set()
        for cell in self.connected_cells():
            connected.update(neighbor for neighbor in neighbors(cell) if neighbor in self.active and neighbor not in self.placed)
        return [cell for cell in empty_active if cell in connected]

    def current_goal(self):
        if self.finished:
            return f"城市已完成 · 总分 {self.score} / 100"
        if not self.has_core():
            return "第一步：把浮岛核心放进中心的金色核心位"
        if self.placed_count("cloud") == 0 or self.placed_count("wind") == 0:
            return "第二步：把云海与风塔接入核心，建立水汽和光能"
        if self.fragments >= 3 and len(self.unlocked) == 3:
            return "研究科技：悬瀑走自然线，日晷站走能源线"
        if "forest" in self.unlocked and not any(
            self.placed.get(neighbor) in ("cloud", "waterfall")
            for cell, kind in self.placed.items() if kind == "forest"
            for neighbor in neighbors(cell)
        ):
            return "让森林邻接云海或悬瀑，获得结构用于扩建"
        if self.expansions == 0 and len(self.placed) < 6:
            return "第三步：先完成 6 格城市，再用结构资源扩建"
        if self.expansions == 0:
            return "第四步：满足下方清单后，扩建第一圈外环"
        if self.expansions == 1 and len(self.placed) < 14:
            return "第五步：在新外环继续连接建筑，完成 14 格城市"
        if self.expansions == 1:
            return "第六步：收集 3 点共鸣和 4 点结构，扩建第二圈"
        return f"定景：填满剩余 {len(CELLS) - len(self.placed)} 格，完成城市"

    def expansion_requirements(self):
        target_count = 6 if self.expansions == 0 else 14
        return [
            ("浮岛核心已入位", self.has_core()),
            ("基础循环已建立", self.placed_count("cloud") >= 1 and self.placed_count("wind") >= 1),
            (f"已构成 {target_count} 格", len(self.placed) >= target_count),
            ("结构资源 4", self.resources["structure"] >= 4),
            ("至少 1 条邻接联动", self.adjacency_links() >= 1),
        ] if self.expansions == 0 else [
            ("第一圈已扩建", self.expansions >= 1),
            ("已研究至少两项科技", len(self.unlocked) - 3 >= 2),
            (f"已构成 {target_count} 格", len(self.placed) >= target_count),
            ("结构资源 4", self.resources["structure"] >= 4),
            ("共鸣资源 3", self.resources["resonance"] >= 3),
        ]

    def can_expand(self):
        return not self.finished and self.expansions < 2 and all(done for _, done in self.expansion_requirements())

    def tech_missing(self, kind):
        spec = TECH_TREE[kind]
        if self.view_mode == "overview":
            return "返回插装后研究"
        if not any(parent in self.unlocked for parent in spec["parents"]):
            return "前置 " + " / ".join(TILE_INFO[parent]["name"] for parent in spec["parents"])
        if self.expansions < spec.get("expansions", 0):
            return "需要第二圈扩建"
        if self.fragments < spec["cost"]:
            return f"还缺 {spec['cost'] - self.fragments} 灵感"
        return ""

    def can_research(self, kind):
        return not self.finished and kind in TECH_TREE and kind not in self.unlocked and not self.tech_missing(kind)

    def research(self, kind):
        if not self.can_research(kind):
            if kind in TECH_TREE:
                self.tech_feedback = "已研究" if kind in self.unlocked else self.tech_missing(kind)
            return False
        self.fragments -= TECH_TREE[kind]["cost"]
        self.unlocked.append(kind)
        self.refill_hand()
        self.supply_page = self.hand.index(kind) // 3
        self.tech_feedback = f"{TILE_INFO[kind]['name']} 已研究，加入结构供应"
        self.toast = self.tech_feedback
        self.toast_timer = 3
        return True

    @staticmethod
    def tech_rect(kind):
        spec = TECH_TREE[kind]
        return pygame.Rect(164 + spec["column"] * 326, 215 + spec["row"] * 113, 284, 94)

    @staticmethod
    def card_rect(index):
        return pygame.Rect(758 + index * 157, 452, 143, 88)

    def draw_background(self):
        global TEXT_TARGET, TEXT_SCALE, TEXT_OFFSET
        self.text_layer.fill((0, 0, 0, 0))
        self.modal_text_layer.fill((0, 0, 0, 0))
        TEXT_SCALE = min(self.display_size[0] / WIDTH, self.display_size[1] / HEIGHT)
        TEXT_OFFSET = (
            (self.display_size[0] - WIDTH * TEXT_SCALE) / 2,
            (self.display_size[1] - HEIGHT * TEXT_SCALE) / 2,
        )
        TEXT_TARGET = self.text_layer
        for y in range(HEIGHT):
            t = y / HEIGHT
            col = tuple(int(BG_TOP[i] * (1 - t) + BG_BOTTOM[i] * t) for i in range(3))
            pygame.draw.line(self.screen, col, (0, y), (WIDTH, y))
        for i in range(9):
            x = 34 + i * 146
            y = 72 + (i % 3) * 172
            pygame.draw.circle(self.screen, (119, 181, 193), (x, y), 2)
        pygame.draw.ellipse(self.screen, (20, 49, 70), (48, 674, 641, 74))

    def draw_panel(self):
        rounded(self.screen, PANEL_RECT, (19, 39, 61), 22, (75, 130, 145), 2)
        text(self.screen, "浮空构成", (758, 48), 30, CREAM, True)
        text(self.screen, "SKY CITY / CONSTRUCTION", (760, 90), 12, MUTED, True)
        pygame.draw.line(self.screen, (55, 91, 105), (758, 111), (1208, 111), 1)
        text(self.screen, "灵感碎片", (761, 128), 15, MUTED, True)
        text(self.screen, f"{self.fragments:02d}", (904, 123), 25, GOLD, True)
        text(self.screen, f"已解锁 {len(self.unlocked)} / 12", (1060, 130), 13, MUTED, False, "topright")
        available = any(self.can_research(kind) for kind in TECH_TREE)
        rounded(self.screen, TECH_BUTTON, (91, 71, 42) if available else (38, 64, 79), 6, GOLD if available else (75, 130, 145), 1)
        text(self.screen, "城市评分" if self.finished else "科技树", TECH_BUTTON.center, 14, GOLD if available or self.finished else CREAM, True, "center")
        rounded(self.screen, CITY_BUTTON, (36, 70, 80) if not self.city_open else (91, 71, 42), 6, TEAL if not self.city_open else GOLD, 1)
        text(self.screen, f"愿景 {len(self.claimed_tasks)} / 3", CITY_BUTTON.center, 13, CREAM, True, "center")
        self.draw_resource_row(761, 166, "光能", self.resources["light"], (239, 198, 99))
        self.draw_resource_row(761, 204, "水汽", self.resources["vapor"], (130, 209, 226))
        self.draw_resource_row(761, 242, "结构", self.resources["structure"], (228, 166, 94))
        self.draw_resource_row(761, 280, "共鸣", self.resources["resonance"], (224, 139, 166))
        connected_count = len(self.connected_cells())
        network_ratio = connected_count / max(1, len(self.placed))
        text(self.screen, "连通率", (761, 325), 14, MUTED, True)
        pygame.draw.rect(self.screen, (52, 78, 94), pygame.Rect(835, 330, 260, 10), border_radius=5)
        pygame.draw.rect(self.screen, TEAL if network_ratio == 1 else CORAL, pygame.Rect(835, 330, int(260 * network_ratio), 10), border_radius=5)
        text(self.screen, f"{round(network_ratio * 100)}%", (1208, 323), 12, MUTED, False, "topright")
        text(self.screen, "核心网络", (835, 348), 12, MUTED)
        text(self.screen, f"已接入 {connected_count} / {len(self.placed)}", (1095, 348), 12, MUTED, False, "topright")
        pygame.draw.line(self.screen, (48, 79, 95), (758, 363), (1208, 363), 1)
        mission_rect = pygame.Rect(758, 374, 450, 42)
        rounded(self.screen, mission_rect, (36, 70, 80), 10, (92, 157, 153), 1)
        text(self.screen, "当前任务", (774, 383), 12, GOLD, True)
        text_fit(self.screen, self.current_goal(), (845, 383), 350, 11, CREAM, True, min_size=9)
        pages = max(1, math.ceil(len(self.hand) / 3))
        text(self.screen, "结构供应", (762, 426), 13, CREAM, True)
        pygame.draw.line(self.screen, (48, 79, 95), (854, 433), (1078, 433), 1)
        text(self.screen, f"{self.supply_page + 1} / {pages}", (1084, 426), 12, MUTED, False, "topright")
        for rect, direction in ((SUPPLY_PREV, -1), (SUPPLY_NEXT, 1)):
            rounded(self.screen, rect, (32, 58, 77), 5, (57, 91, 105), 1)
            cx, cy = rect.center
            color = MUTED if pages == 1 else CREAM
            pygame.draw.lines(self.screen, color, False, [(cx - direction * 3, cy - 5), (cx + direction * 3, cy), (cx - direction * 3, cy + 5)], 2)
        for idx, kind in enumerate(self.visible_hand()):
            rect = self.card_rect(idx)
            x, y = rect.topleft
            active = self.selected == kind
            rounded(self.screen, rect, (32, 58, 77) if not active else (59, 91, 95), 7, GOLD if active else (57, 91, 105), 2)
            if not self.can_pay(kind):
                pygame.draw.rect(self.screen, (11, 25, 39, 92), rect, border_radius=7)
            draw_tile_art(self.screen, (x + 32, y + 35), kind, 0.53, variant=0)
            text_fit(self.screen, TILE_INFO[kind]["name"], (x + 63, y + 13), 76, 13, CREAM, True, min_size=11)
            text_fit(self.screen, TILE_INFO[kind]["tag"], (x + 63, y + 37), 76, 10, TILE_INFO[kind]["color"], min_size=8)
            cost_color = TEAL if self.can_pay(kind) else CORAL
            text(self.screen, f"成本  {self.short_cost_text(kind)}", (rect.centerx, y + 65), 11, cost_color, True, "midtop")
        focus_kind = self.selected
        if focus_kind is None:
            mouse = self.logical_pos(pygame.mouse.get_pos())
            for idx, kind in enumerate(self.visible_hand()):
                if self.card_rect(idx).collidepoint(mouse):
                    focus_kind = kind
                    break
        help_rect = pygame.Rect(758, 542, 450, 132)
        rounded(self.screen, help_rect, (27, 53, 70), 12, (54, 94, 106), 1)
        if focus_kind:
            info = TILE_INFO[focus_kind]
            text(self.screen, f"{info['name']} · 怎么用", (776, 554), 14, info["color"], True)
            guide = info.get("guide", info["desc"])
            text(self.screen, f"成本：{self.cost_text(focus_kind)}", (776, 580), 12, TEAL if self.can_pay(focus_kind) else CORAL, True)
            for line_index, line in enumerate(text_wrap(guide, 11, 414)[:2]):
                text(self.screen, line, (776, 598 + line_index * 17), 11, CREAM)
            quote = get_building_quote(focus_kind)
            if quote:
                quote_line = f"“{quote['quote']}”"
                text_fit(self.screen, quote_line, (776, 635), 414, 10, (232, 205, 142), min_size=8)
                text_fit(self.screen, f"{quote['author']} · {quote['work']}", (776, 650), 414, 9, (202, 185, 139), min_size=8)
            text_fit(self.screen, position_description(focus_kind), (776, 665), 414, 10, GOLD, min_size=8)
        elif self.expansions == 2:
            text(self.screen, "定景目标", (776, 560), 14, GOLD, True)
            text(self.screen, "填满 36 格后自动结算，不要求指定终局建筑。", (776, 592), 12, CREAM)
            text(self.screen, f"城市风格：{STYLE_NAMES[dominant_style(self.city_style_scores())]}", (776, 621), 12, MUTED)
        else:
            text(self.screen, "扩建清单", (776, 560), 14, GOLD, True)
            for index, (label, done) in enumerate(self.expansion_requirements()):
                x = 776 + (index % 2) * 215
                y = 588 + (index // 2) * 28
                if done:
                    pygame.draw.lines(self.screen, TEAL, False, [(x, y + 8), (x + 3, y + 11), (x + 8, y + 4)], 2)
                else:
                    pygame.draw.circle(self.screen, MUTED, (x + 4, y + 8), 3, 1)
                text(self.screen, label, (x + 14, y), 12, TEAL if done else MUTED, True)
        button = pygame.Rect(758, 684, 450, 48)
        can_expand = self.can_expand()
        rounded(self.screen, button, (111, 84, 52) if can_expand else (39, 65, 79), 12, GOLD if can_expand else (59, 95, 107), 2)
        label = ("扩建浮岛 · 消耗 4 结构" if self.expansions == 0 else "扩建浮岛 · 消耗 4 结构 + 3 共鸣") if self.expansions < 2 else "城市已完成" if self.finished else "全岛开放 · 继续完成城市"
        text(self.screen, label, button.center, 15, CREAM if can_expand else MUTED, True, "center")
        rounded(self.screen, RELOCATE_BUTTON, (36, 70, 80) if self.relocation_available else (32, 53, 68), 6, TEAL if self.relocation_available else (59, 95, 107), 1)
        text(self.screen, "一次重构" if self.relocation_available else "重构已用", RELOCATE_BUTTON.center, 13, CREAM if self.relocation_available else MUTED, True, "center")
        text(self.screen, "研究与插装", (758, 747), 12, MUTED)
        text(self.screen, "自然 / 能源 / 生活", (1208, 747), 12, MUTED, False, "topright")

    def draw_resource_row(self, x, y, name, value, color):
        row = pygame.Rect(x - 3, y - 5, 310, 29)
        rounded(self.screen, row, (25, 50, 67), 7, (43, 78, 91), 1)
        pygame.draw.circle(self.screen, color, (x + 7, y + 8), 5)
        pygame.draw.circle(self.screen, (245, 241, 213), (x + 7, y + 8), 2)
        text(self.screen, name, (x + 22, y), 14, MUTED, True)
        text(self.screen, str(value), (1064, y - 3), 22, color, True, "topright")

    def logical_pos(self, pos):
        scale = min(self.display_size[0] / WIDTH, self.display_size[1] / HEIGHT)
        offset_x = (self.display_size[0] - WIDTH * scale) / 2
        offset_y = (self.display_size[1] - HEIGHT * scale) / 2
        return ((pos[0] - offset_x) / scale, (pos[1] - offset_y) / scale)

    def present(self):
        global TEXT_TARGET
        self.display.fill((8, 20, 34))
        scale = min(self.display_size[0] / WIDTH, self.display_size[1] / HEIGHT)
        size = (int(WIDTH * scale), int(HEIGHT * scale))
        offset = ((self.display_size[0] - size[0]) // 2, (self.display_size[1] - size[1]) // 2)
        if self.view_mode == "overview" and not self.modal_open() and self.showcase_layers:
            self.display.blit(self.showcase_layers[0], (0, 0))
            bob = round(math.sin(self.pulse * 0.6) * 2 * scale)
            self.display.blit(self.showcase_layers[1], (0, bob))
            self.display.blit(pygame.transform.smoothscale(self.showcase_ui, size), offset)
        else:
            self.display.blit(pygame.transform.smoothscale(self.screen, size), offset)
        # Text is rendered directly at physical resolution after the scene is
        # scaled, so Chinese glyphs never pass through smoothscale. Modal text
        # is isolated so normal HUD labels cannot sit above another panel.
        if self.modal_open():
            self.display.blit(self.modal_text_layer, (0, 0))
        else:
            self.display.blit(self.text_layer, (0, 0))
        TEXT_TARGET = None

    def draw_foundation(self):
        foundation = pygame.Rect(0, 118, 740, 494)
        board_base = LANDSCAPE_IMAGES.get("board_base")
        if board_base is not None:
            draw_island_image(self.screen, foundation, board_base)
        else:
            draw_island(self.screen, foundation, cliff_height=140)

    def draw_showcase(self, controls=True):
        key = (self.display_size, tuple(sorted(self.placed.items())),
               tuple(sorted(self.placed_variants.items())), tuple(sorted(self.placed_jitter.items())),
               tuple((kind, tuple(id(image) for image in images)) for kind, images in TILE_IMAGES.items()),
               tuple(sorted((combo, tuple(cells)) for combo, cells in find_combinations(
                   self.settled_layout(), self.connected_cells(self.settled_layout()), neighbors).items())),
               tuple((name, id(image)) for name, image in COMBINATION_IMAGES.items()))
        if key != self.showcase_cache_key:
            self.showcase_layers = build_showcase(self.display_size, self.placed, self.placed_variants,
                                                  self.placed_jitter, TILE_IMAGES, neighbors,
                                                  LANDSCAPE_IMAGES, COMBINATION_IMAGES,
                                                  find_combinations(self.settled_layout(),
                                                                    self.connected_cells(self.settled_layout()),
                                                                    neighbors))
            self.showcase_cache_key = key
        if self.modal_open():
            background, city = self.showcase_layers
            composite = background.copy()
            bob = round(math.sin(self.pulse * 0.6) * 2 * TEXT_SCALE)
            composite.blit(city, (0, bob))
            area = pygame.Rect(round(TEXT_OFFSET[0]), round(TEXT_OFFSET[1]),
                               round(WIDTH * TEXT_SCALE), round(HEIGHT * TEXT_SCALE))
            self.screen.blit(pygame.transform.smoothscale(composite.subsurface(area), (WIDTH, HEIGHT)), (0, 0))
        self.showcase_ui = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        text(self.screen, "天空之城", (66, 38), 31, (30, 62, 70), True)
        style = STYLE_NAMES[dominant_style(self.final_style_scores if self.finished else self.city_style_scores())]
        caption = f"{style}城市  ·  {len(self.placed)} / 36" + (f"  ·  {self.score} 分" if self.finished else "")
        text(self.screen, caption, (68, 83), 13, (53, 88, 91))
        if controls:
            buttons = ((SHOWCASE_VISION, "城市愿景"), (SHOWCASE_SCORE, "查看评分" if self.finished else "科技总览"),
                       (SHOWCASE_EXPORT, "导出画面"), (SHOWCASE_BACK, "返回插装视图"))
            for rect, label in buttons:
                pygame.draw.rect(self.showcase_ui, (225, 239, 230, 205), rect, border_radius=4)
                pygame.draw.line(self.showcase_ui, (122, 163, 158), rect.bottomleft, rect.bottomright, 1)
                text(self.screen, label, rect.center, 12, (33, 72, 78), True, "center")
            if self.gallery_feedback:
                text(self.screen, self.gallery_feedback, (1218, 754), 12, (46, 82, 87), False, "topright")

    def export_showcase(self):
        if self.view_mode != "overview" or self.modal_open():
            return None
        root = os.path.dirname(sys.executable) if getattr(sys, "frozen", False) else os.path.dirname(os.path.abspath(__file__))
        directory = os.path.join(root, "exports")
        try:
            os.makedirs(directory, exist_ok=True)
            path = os.path.join(directory, "skycity_" + datetime.now().strftime("%Y%m%d_%H%M%S_%f") + ".png")
            self.draw_background()
            self.draw_showcase(controls=False)
            self.present()
            pygame.image.save(self.display, path)
            self.gallery_feedback = "已导出 PNG · exports 文件夹"
            return path
        except (OSError, pygame.error):
            self.gallery_feedback = "导出失败 · 请检查游戏目录写入权限"
            return None

    def draw_board(self):
        self.draw_foundation()
        ground_colors = {"cloud": (206, 222, 220), "forest": (187, 210, 167), "waterfall": (179, 209, 212)}
        for cell, kind in self.placed.items():
            center = cell_center(cell)
            base_color = ground_colors.get(kind, (207, 218, 193))
            pygame.draw.polygon(self.screen, base_color, diamond(center, 42, 25))
            if self.view_mode != "overview":
                pygame.draw.polygon(self.screen, (157, 183, 170), diamond(center, 41, 24), 1)
        if self.view_mode != "overview":
            for cell in CELLS:
                center = cell_center(cell)
                active = cell in self.active
                if not active and cell not in self.placed:
                    pygame.draw.polygon(self.screen, (69, 94, 101), diamond(center, 42, 25))
                    pygame.draw.polygon(self.screen, (116, 139, 139), diamond(center, 41, 24), 1)
                elif active and cell not in self.placed:
                    pygame.draw.polygon(self.screen, (145, 158, 149), diamond(center, 42, 25))
                    pulse = int(10 + 8 * (0.5 + 0.5 * math.sin(self.pulse * 2 + cell[0])))
                    pygame.draw.polygon(self.screen, (121 + pulse, 158 + pulse, 157 + pulse), diamond(center, 42, 25), 2)
                    if not self.has_core() and cell in CORE_ZONE:
                        pygame.draw.polygon(self.screen, GOLD, diamond(center, 45, 28), 3)
                        pygame.draw.circle(self.screen, GOLD, (int(center[0]), int(center[1])), 3)
                    if self.selected and cell not in self.valid_cells(self.selected):
                        pygame.draw.polygon(self.screen, (93, 111, 112, 145), diamond(center, 42, 25), 1)
        # Keep front-to-back occlusion, but vary height and visual weight so
        # ground forms no longer compete with the few skyline landmarks.
        valid = set(self.valid_cells(self.selected)) if self.selected else set()
        move_targets = set(self.relocation_targets()) if self.relocation_mode else set()
        for cell, kind in sorted(self.placed.items(), key=lambda item: cell_center(item[0])[1]):
            variant = self.placed_variants.get(cell, 0)
            jitter_x, jitter_y = self.placed_jitter.get(cell, (0, 0))
            scale = BUILDING_SCALE.get(kind, 0.75)
            if self.view_mode == "overview" and kind in GROUND_KINDS:
                scale *= 0.82
            draw_tile_art(self.screen, (cell_center(cell)[0] + jitter_x, cell_center(cell)[1] + jitter_y), kind, scale, tile_scale=0.92, variant=variant, anchor_bottom=True)
        for item in self.pending:
            pos = cell_center(item["cell"])
            pygame.draw.circle(self.screen, (255, 231, 163), (int(pos[0]), int(pos[1] - 30)), 4)
            pygame.draw.circle(self.screen, (255, 231, 163), (int(pos[0]), int(pos[1] - 30)), 11, 1)
        if self.view_mode != "overview":
            # Placement overlays sit above portraits in planning mode. Only
            # the footprint is simplified; the artwork itself stays intact.
            for cell in valid | move_targets:
                center = cell_center(cell)
                bonus = position_bonus(cell, self.selected) if self.selected and (cell, self.selected) not in self.settled_builds else {}
                color = GOLD if bonus or cell in move_targets else TEAL
                pygame.draw.polygon(self.screen, color, diamond(center, 42, 25), 3 if bonus or cell in move_targets else 2)
                if self.selected:
                    draw_slot_icon(self.screen, center, self.selected, 230)
            if self.relocation_source:
                pygame.draw.polygon(self.screen, GOLD, diamond(cell_center(self.relocation_source), 45, 28), 3)
            hover = self.cell_at(self.logical_pos(pygame.mouse.get_pos()))
            if hover is not None and (self.selected or self.relocation_mode):
                labels = " / ".join(ZONE_NAMES[zone] for zone in zones_for(hover)) or "平地"
                detail = labels
                if self.selected and hover in valid:
                    reward = self.placement_reward(hover, self.selected)
                    detail += " · " + ("此格同类已结算，重建不再产出" if reward is None else
                                        "  ".join(f"{RESOURCE_NAMES[key]} +{amount}" for key, amount in reward.items()))
                text(self.screen, detail, (370, 650), 12, CREAM, True, "center")
        text(self.screen, "36 格浮空基底", (54, 697), 13, (219, 235, 224), True)
        text(self.screen, f"已构成 {len(self.placed):02d} / 36", (677, 697), 13, (219, 235, 224), True, "topright")
        toggle = VIEW_BUTTON
        rounded(self.screen, toggle, (36, 70, 80), 6, TEAL, 1)
        text(self.screen, "返回插装" if self.view_mode == "overview" else "构图预览", toggle.center, 12, CREAM, True, "center")

    def draw_modals(self):
        if self.tutorial_step is not None:
            return
        global TEXT_TARGET
        if not self.tech_open and not self.result_visible and not self.city_open:
            return
        TEXT_TARGET = self.modal_text_layer
        overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        overlay.fill((7, 18, 31, 166))
        self.screen.blit(overlay, (0, 0))
        if self.result_visible:
            self.draw_result_modal()
            return
        if self.city_open:
            self.draw_city_modal()
            return
        box = pygame.Rect(100, 54, 1080, 692)
        rounded(self.screen, box, (23, 46, 67), 20, (217, 183, 105), 2)
        text(self.screen, "科技树 · 自由研究", (640, 85), 28, CREAM, True, "midtop")
        text(self.screen, "灵感碎片可自由投入任意已满足前置的节点，研究后加入结构供应。", (640, 124), 14, MUTED, False, "midtop")
        text(self.screen, f"当前灵感  {self.fragments}", (150, 158), 14, GOLD, True)
        close = pygame.Rect(1124, 66, 42, 42)
        rounded(self.screen, close, (38, 64, 79), 5, (75, 130, 145), 1)
        pygame.draw.line(self.screen, CREAM, (1138, 80), (1152, 94), 2)
        pygame.draw.line(self.screen, CREAM, (1152, 80), (1138, 94), 2)
        for column, label, color in ((0, "自然 · 水汽转结构", (101, 174, 114)), (1, "能源 · 光能转结构", GOLD), (2, "连接 · 生活与地标", (224, 139, 166))):
            text(self.screen, label, (306 + column * 326, 188), 14, color, True, "center")
        # Only within-branch edges are drawn; shared prerequisites are spelled
        # out on the cards to avoid routing lines through other nodes.
        for parent, child in (("waterfall", "forest"), ("forest", "garden"), ("sundial", "gear"), ("gear", "harbor"), ("harbor", "observatory")):
            start = self.tech_rect(parent).midbottom
            end = self.tech_rect(child).midtop
            pygame.draw.line(self.screen, TEAL if parent in self.unlocked else (78, 100, 108), start, end, 2)
        text(self.screen, "森林台 / 齿轮厂研究后", (958, 243), 13, MUTED, False, "center")
        text(self.screen, "可接入连接与生活分支", (958, 273), 13, MUTED, False, "center")
        text(self.screen, "观星台不是通关必需", (958, 574), 13, GOLD, True, "center")
        text(self.screen, "任一进阶路线 + 第二圈扩建", (958, 604), 11, MUTED, False, "center")
        for kind in TECH_TREE:
            spec = TECH_TREE[kind]
            rect = self.tech_rect(kind)
            unlocked = kind in self.unlocked
            available = self.can_research(kind)
            color = TILE_INFO[kind]["color"] if unlocked or available else (78, 100, 108)
            rounded(self.screen, rect, (48, 77, 84) if unlocked else (31, 58, 75), 10, color, 2)
            draw_tile_art(self.screen, (rect.left + 40, rect.centery + 4), kind, 0.48, variant=0)
            text(self.screen, TILE_INFO[kind]["name"], (rect.left + 76, rect.top + 13), 15, CREAM if unlocked or available else MUTED, True)
            text(self.screen, f"{spec['cost']} 灵感", (rect.right - 12, rect.top + 15), 11, color, False, "topright")
            if unlocked:
                label, label_color = "已研究", TEAL
            elif available:
                label, label_color = f"研究 · 消耗 {TECH_TREE[kind]['cost']} 灵感", GOLD
            else:
                label, label_color = self.tech_missing(kind), MUTED
            text(self.screen, label, (rect.left + 76, rect.top + 40), 11, label_color, True)
            text(self.screen, TILE_INFO[kind]["desc"], (rect.left + 76, rect.top + 66), 11, color)
        if self.tech_feedback:
            text(self.screen, self.tech_feedback, (640, 688), 13, GOLD, True, "center")
        text(self.screen, "点击节点研究 · Esc 关闭", (640, 722), 12, MUTED, False, "center")

    def draw_result_modal(self):
        box = pygame.Rect(210, 82, 860, 624)
        rounded(self.screen, box, (23, 46, 67), 20, (217, 183, 105), 2)
        text(self.screen, "天空之城 · 构成完成", (640, 158), 27, CREAM, True, "midtop")
        text(self.screen, "36 格浮岛已全部完成插装", (640, 202), 14, MUTED, False, "midtop")
        text(self.screen, str(self.score), (640, 257), 52, GOLD, True, "center")
        text(self.screen, "/ 100  城市评分", (640, 297), 14, MUTED, False, "midtop")
        labels = (("构成", "composition", 35), ("网络", "network", 30), ("联动", "synergy", 15), ("风格", "style", 15), ("愿景", "tasks", 5))
        for index, (label, key, limit) in enumerate(labels):
            value = self.score_breakdown.get(key, 0)
            y = 333 + index * 35
            text(self.screen, label, (410, y), 14, CREAM, True)
            pygame.draw.rect(self.screen, (52, 78, 94), pygame.Rect(500, y + 5, 300, 10), border_radius=5)
            pygame.draw.rect(self.screen, GOLD if key in {"style", "tasks"} else TEAL, pygame.Rect(500, y + 5, int(300 * value / limit), 10), border_radius=5)
            text(self.screen, f"{value} / {limit}", (830, y - 2), 14, GOLD, True)
        style_key = dominant_style(self.final_style_scores)
        title = STYLE_NAMES[style_key]
        ending = get_ending(self.score, style_key)
        text(self.screen, f"{title}城市 · {ending['title']}", (640, 503), 16, GOLD, True, "midtop")
        body_lines = text_wrap(ending["body"], 11, 620)[:2]
        for index, line in enumerate(body_lines):
            text(self.screen, line, (640, 529 + index * 17), 11, CREAM, False, "midtop")
        text_fit(self.screen, ending["style_line"], (640, 566), 620, 11, MUTED, False, "midtop", min_size=9)
        view = pygame.Rect(404, 620, 210, 44)
        new = pygame.Rect(666, 620, 210, 44)
        rounded(self.screen, view, (36, 70, 80), 9, (92, 157, 153), 1)
        rounded(self.screen, new, (111, 84, 52), 9, GOLD, 1)
        text(self.screen, "查看城市", view.center, 14, CREAM, True, "center")
        text(self.screen, "重新开始", new.center, 14, CREAM, True, "center")

    def draw_city_modal(self):
        box = pygame.Rect(150, 82, 980, 636)
        rounded(self.screen, box, (23, 46, 67), 20, (92, 157, 153), 2)
        close = pygame.Rect(1068, 95, 42, 42)
        rounded(self.screen, close, (38, 64, 79), 5, (75, 130, 145), 1)
        pygame.draw.line(self.screen, CREAM, (1082, 109), (1096, 123), 2)
        pygame.draw.line(self.screen, CREAM, (1096, 109), (1082, 123), 2)
        text(self.screen, "城市图鉴", (640, 116), 28, CREAM, True, "midtop")
        subtitle = ("组合在全部相关建筑结算后发现；首次发现可领取资源，并点亮终局装饰。"
                    if self.city_page == "combinations" else
                    "完成任意愿景会立刻领取一次奖励；它们不改变 36 格通关条件。")
        text(self.screen, subtitle, (640, 159), 14, MUTED, False, "midtop")
        vision_tab = pygame.Rect(410, 184, 210, 32)
        combo_tab = pygame.Rect(660, 184, 210, 32)
        for rect, label, selected in ((vision_tab, "城市愿景", self.city_page == "visions"),
                                      (combo_tab, "空间组合", self.city_page == "combinations")):
            rounded(self.screen, rect, (60, 94, 94) if selected else (31, 58, 75), 7,
                    TEAL if selected else (75, 130, 145), 1)
            text(self.screen, label, rect.center, 13, CREAM if selected else MUTED, True, "center")
        if self.city_page == "combinations":
            current = {combo["id"]: cells for combo, cells in self.city_combinations()}
            for index, combo in enumerate(COMBINATIONS):
                rect = pygame.Rect(220, 232 + index * 137, 840, 112)
                matched = current.get(combo["id"])
                claimed = combo["id"] in self.claimed_combinations
                done = bool(matched)
                rounded(self.screen, rect, (43, 75, 78) if done else (31, 58, 75), 10,
                        TEAL if done else (75, 130, 145), 2)
                for part_index, kind in enumerate(combo["parts"]):
                    center = (rect.left + 44 + part_index * 43, rect.centery - 8)
                    draw_slot_icon(self.screen, center, kind, 235 if done else 170)
                    if part_index < 2:
                        pygame.draw.line(self.screen, TEAL if done else (91, 119, 126),
                                         (center[0] + 27, center[1]), (center[0] + 59, center[1]), 2)
                text(self.screen, combo["name"], (rect.left + 190, rect.top + 15), 17,
                     TEAL if done else CREAM, True)
                text(self.screen, combo["description"], (rect.left + 190, rect.top + 43), 12, MUTED)
                reward = "、".join(f"{RESOURCE_NAMES[key]} +{value}" for key, value in combo["reward"].items())
                text(self.screen, f"首次发现奖励：{reward}", (rect.left + 190, rect.top + 73), 11, GOLD)
                state = "奖励已领取" if claimed else ("布局已成立" if done else "待构成")
                text(self.screen, state, (rect.right - 20, rect.centery), 13,
                     TEAL if claimed else (GOLD if done else MUTED), True, "midright")
            text(self.screen, "组合只需相邻关系成立；拆改布局后，终局装饰随当前城市更新。",
                 (640, 660), 12, MUTED, False, "center")
            text(self.screen, "关闭 · Esc", (640, 681), 12, MUTED, False, "center")
            return
        for index, (task, progress) in enumerate(self.city_tasks()):
            rect = pygame.Rect(224 + (index % 2) * 416, 220 + (index // 2) * 154, 384, 120)
            done = task["id"] in self.claimed_tasks
            ratio = min(1, progress / max(1, task["target"]))
            rounded(self.screen, rect, (47, 77, 82) if done else (31, 58, 75), 12, TEAL if done else (75, 130, 145), 2)
            text(self.screen, task["name"], (rect.left + 20, rect.top + 17), 17, TEAL if done else CREAM, True)
            text(self.screen, "已完成 · 奖励已领取" if done else task["description"], (rect.left + 20, rect.top + 50), 12, MUTED)
            pygame.draw.rect(self.screen, (52, 78, 94), pygame.Rect(rect.left + 20, rect.bottom - 40, 260, 8), border_radius=4)
            pygame.draw.rect(self.screen, TEAL if done else GOLD, pygame.Rect(rect.left + 20, rect.bottom - 40, int(260 * ratio), 8), border_radius=4)
            text(self.screen, f"{progress} / {task['target']}", (rect.right - 20, rect.bottom - 47), 12, CREAM, True, "topright")
            reward = "、".join(f"{RESOURCE_NAMES[key]} +{value}" for key, value in task["reward"].items())
            text(self.screen, f"奖励：{reward}", (rect.left + 20, rect.bottom - 24), 11, task.get("color", GOLD))
        text(self.screen, "位置分区", (660, 389), 14, GOLD, True)
        text(self.screen, "高位 · 前四行，能源结构额外光能", (660, 420), 12, MUTED)
        text(self.screen, "边缘 · 每行两端，水系或连接结构加成", (660, 445), 12, MUTED)
        text(self.screen, "中心 · 中间三行内部，生活与自然额外共鸣", (660, 470), 12, MUTED)
        scores = self.city_style_scores()
        text(self.screen, "城市风格", (640, 542), 16, GOLD, True, "midtop")
        for index, style in enumerate(STYLES):
            x = 470 + index * 170
            color = STYLES[style]["color"]
            text(self.screen, STYLE_NAMES[style], (x, 581), 14, color, True, "center")
            text(self.screen, f"{scores.get(style, 0)} / 15", (x, 608), 15, CREAM, True, "center")
        text(self.screen, "关闭 · Esc", (640, 681), 12, MUTED, False, "center")

    def draw_tutorial(self):
        if self.tutorial_step is None:
            return
        global TEXT_TARGET
        TEXT_TARGET = self.modal_text_layer
        overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        overlay.fill((7, 18, 31, 172))
        self.screen.blit(overlay, (0, 0))
        box = pygame.Rect(220, 130, 840, 520)
        rounded(self.screen, box, (23, 46, 67), 22, (219, 186, 108), 2)
        title, body, action = TUTORIAL_STEPS[self.tutorial_step]
        text(self.screen, "浮空构成 · 入门引导", (640, 174), 17, GOLD, True, "midtop")
        text(self.screen, title, (640, 218), 30, CREAM, True, "midtop")
        lines = text_wrap(body, 15, 700)
        for index, line in enumerate(lines):
            text(self.screen, line, (640, 270 + index * 26), 15, MUTED, False, "midtop")
        if self.tutorial_step == 0:
            draw_tile_art(self.screen, (430, 440), "core", 0.9)
            draw_tile_art(self.screen, (640, 440), "cloud", 0.9)
            draw_tile_art(self.screen, (850, 440), "wind", 0.9)
            text(self.screen, "核心", (430, 514), 13, GOLD, True, "midtop")
            text(self.screen, "水汽", (640, 514), 13, (139, 214, 226), True, "midtop")
            text(self.screen, "光能", (850, 514), 13, TEAL, True, "midtop")
        elif self.tutorial_step == 1:
            pygame.draw.line(self.screen, GOLD, (434, 433), (842, 433), 3)
            pygame.draw.circle(self.screen, GOLD, (434, 433), 8)
            pygame.draw.circle(self.screen, (139, 214, 226), (842, 433), 8)
            text(self.screen, "选择卡片", (430, 466), 15, GOLD, True, "midtop")
            text(self.screen, "点击灰色空位", (842, 466), 15, (139, 214, 226), True, "midtop")
        elif self.tutorial_step == 2:
            for index, (label, color) in enumerate((("成本", CORAL), ("产出", TEAL), ("解锁", GOLD))):
                x = 420 + index * 220
                pygame.draw.circle(self.screen, color, (x, 440), 31)
                text(self.screen, str(index + 1), (x, 440), 22, (24, 49, 66), True, "center")
                text(self.screen, label, (x, 490), 15, color, True, "midtop")
        elif self.tutorial_step == 3:
            for index, kind in enumerate(("waterfall", "forest", "garden")):
                x = 430 + index * 210
                draw_tile_art(self.screen, (x, 438), kind, 0.8)
                text(self.screen, TILE_INFO[kind]["name"], (x, 506), 14, TILE_INFO[kind]["color"], True, "midtop")
        elif self.tutorial_step == 4:
            for index, (label, color) in enumerate((("拆除", CORAL), ("返还", TEAL), ("重排", GOLD))):
                x = 420 + index * 220
                pygame.draw.circle(self.screen, color, (x, 440), 31)
                text(self.screen, str(index + 1), (x, 440), 22, (24, 49, 66), True, "center")
                text(self.screen, label, (x, 490), 15, color, True, "midtop")
        else:
            for index, (label, color) in enumerate((("位置奖励", TEAL), ("城市愿景", GOLD), ("一次重构", CORAL))):
                x = 420 + index * 220
                pygame.draw.circle(self.screen, color, (x, 440), 31)
                text(self.screen, str(index + 1), (x, 440), 22, (24, 49, 66), True, "center")
                text(self.screen, label, (x, 490), 15, color, True, "midtop")
        action_rect = pygame.Rect(520, 560, 240, 48)
        rounded(self.screen, action_rect, (111, 84, 52), 12, GOLD, 2)
        text(self.screen, action, action_rect.center, 15, CREAM, True, "center")
        text(self.screen, "跳过教程  ·  Esc", (640, 624), 12, MUTED, False, "center")

    def click_cell(self, pos):
        if self.finished or self.view_mode == "overview":
            return
        nearest = self.cell_at(pos)
        if nearest is None:
            return
        if self.relocation_mode:
            if self.relocation_source is None:
                if nearest in self.placed and self.placed[nearest] != "core":
                    self.relocation_source = nearest
                    self.toast = "选择金色空插槽完成迁移；再次点击重构可取消"
                else:
                    self.toast = "先选择一座已经结算的非核心建筑"
                self.toast_timer = 3
            elif not self.relocate(self.relocation_source, nearest):
                self.toast = "迁移后所有建筑必须仍连接核心，请选择金色空插槽"
                self.toast_timer = 3
            return
        if nearest not in self.active:
            self.toast = "这块灰色地块还没有解锁"
            self.toast_timer = 2.5
            return
        if self.selected is None:
            self.toast = self.current_goal()
            self.toast_timer = 2.5
            return
        if nearest in self.placed:
            return
        kind = self.selected
        if not self.can_pay(kind):
            self.toast = f"资源不足：还需要 {self.missing_cost(kind)}"
            self.toast_timer = 2.8
            return
        valid = self.valid_cells(kind)
        if nearest not in valid:
            if kind == "core" and not self.has_core():
                self.toast = "浮岛核心只能放在中心的两个金色核心位"
            elif not self.has_core():
                self.toast = "先把浮岛核心放入中心，城市才有连接起点"
            else:
                self.toast = "这个建筑必须接入现有城市网络，试试亮起的边框位置"
            self.toast_timer = 2.8
            return
        self.pay_cost(kind)
        self.placed[nearest] = kind
        self.refill_hand()
        self.selected = None
        self.pending.append({"cell": nearest, "kind": kind, "time": 1.8})
        available_variants = len(TILE_IMAGES.get(kind, [])) if isinstance(TILE_IMAGES.get(kind), list) else 1
        self.placed_variants[nearest] = random.randrange(max(1, available_variants))
        self.placed_jitter[nearest] = (random.randint(-5, 5), random.randint(-2, 2))
        self.toast = f"{TILE_INFO[kind]['name']} 已插装，正在汇聚资源"
        self.toast_timer = 2.1
        self.pulse = 0
        for _ in range(10):
            c = cell_center(nearest)
            self.particles.append({"x": c[0], "y": c[1], "tx": 1110, "ty": 150 + random.random() * 160, "life": 1.1, "color": TILE_INFO[kind]["color"]})

    def dismantle_at(self, pos):
        if self.finished or self.relocation_mode or self.view_mode == "overview":
            return
        nearest = self.cell_at(pos)
        if nearest is None or nearest not in self.placed:
            self.toast = "右键场上的结构卡，可以拆除并重新布局"
            self.toast_timer = 2.4
            return
        kind = self.placed[nearest]
        if kind == "core" and len(self.placed) > 1:
            self.toast = "浮岛核心仍在为城市供能，请先拆除其他结构"
            self.toast_timer = 2.8
            return
        self.placed.pop(nearest)
        self.placed_variants.pop(nearest, None)
        self.placed_jitter.pop(nearest, None)
        unsettled = any(item["cell"] == nearest for item in self.pending)
        self.pending = [item for item in self.pending if item["cell"] != nearest]
        self.refund_cost(kind, unsettled)
        self.refill_hand()
        self.selected = None
        self.toast = f"{TILE_INFO[kind]['name']} 已拆除，" + ("未结算成本全额返还" if unsettled else "成本返还一半（向下取整）")
        self.toast_timer = 2.8

    def reward_for(self, cell, kind):
        reward = dict(REWARDS[kind])
        nearby = {self.placed[n] for n in neighbors(cell) if n in self.placed}
        def add(resource, amount):
            reward[resource] = reward.get(resource, 0) + amount
        if kind == "waterfall" and "cloud" in nearby:
            add("vapor", 1)
        elif kind == "forest" and nearby & {"cloud", "waterfall"}:
            add("structure", 2)
        elif kind == "garden" and "forest" in nearby:
            add("structure", 1)
            add("resonance", 1)
        elif kind == "wind" and "sundial" in nearby:
            add("light", 1)
        elif kind == "sundial" and "wind" in nearby:
            add("light", 1)
        elif kind == "gear" and nearby & {"wind", "sundial"}:
            add("structure", 1)
        elif kind == "residents" and nearby & {"forest", "garden"}:
            add("resonance", 1)
        elif kind == "bridge" and "harbor" in nearby:
            add("structure", 1)
            add("light", 1)
        elif kind == "harbor" and "bridge" in nearby:
            add("structure", 1)
        elif kind == "observatory" and "harbor" in nearby:
            add("resonance", 1)
        for resource, amount in position_bonus(cell, kind).items():
            add(resource, amount)
        synergy = any(frozenset((kind, other)) in SYNERGY_PAIRS for other in nearby)
        return reward, synergy

    def resolve_reward(self, pending):
        cell, kind = pending["cell"], pending["kind"]
        if self.placed.get(cell) != kind or cell not in self.connected_cells():
            self.toast = "建筑已脱离核心网络，未产生资源"
            self.toast_timer = 2.4
            return
        if (cell, kind) in self.settled_builds:
            self.toast = "已在此格结算过同类建筑，重新布局不重复生产"
            self.toast_timer = 2.4
            return
        reward, synergy = self.reward_for(cell, kind)
        first_cell = cell not in self.inspired_cells
        if first_cell and kind != "core":
            reward["structure"] = reward.get("structure", 0) + 1
        for key, value in reward.items():
            self.resources[key] += value
        if first_cell:
            self.fragments += 1 + int(synergy)
            self.inspired_cells.add(cell)
        self.settled_builds.add((cell, kind))
        gains = " · ".join(f"{RESOURCE_NAMES[key]} +{value}" for key, value in reward.items())
        self.toast = ("联动成立 · " if synergy else "结算 · ") + gains
        self.toast_timer = 2.4
        if self.fragments >= 3 and not self.tech_hint_shown:
            self.tech_hint_shown = True
            self.toast = "可以研究第一项科技了 · 点击右上角科技树"
            self.toast_timer = 4

    def expand(self):
        if not self.can_expand():
            return False
        self.resources["structure"] -= 4
        if self.expansions == 1:
            self.resources["resonance"] -= 3
        self.expansions += 1
        locked = [c for c in CELLS if c not in self.active]
        locked.sort(key=lambda c: abs(c[0] - 5) + abs(c[1] - (1 + min(c[0], 10 - c[0]) - 1) / 2))
        count = 8 if self.expansions == 1 else 10
        self.active.update(locked[:count])
        self.toast = f"浮岛扩建完成 · 第 {self.expansions} 圈开放"
        self.toast_timer = 3
        return True

    def calculate_score(self):
        edges = [(cell, other) for cell in self.placed for other in neighbors(cell)
                 if other in self.placed and cell < other]
        mixed = sum(self.placed[a] != self.placed[b] for a, b in edges)
        functional = sum(frozenset((self.placed[a], self.placed[b])) in SYNERGY_PAIRS for a, b in edges)
        kinds = set(self.placed.values())
        suites = (
            {"cloud", "waterfall", "forest", "garden"},
            {"wind", "sundial", "gear", "harbor"},
            {"forest", "garden", "residents"},
            {"wind", "bridge", "harbor"},
        )
        style = self.city_style_scores()
        low = sum(kind in GROUND_KINDS for kind in self.placed.values())
        tall = sum(kind in {"wind", "core", "observatory"} for kind in self.placed.values())
        mid = len(self.placed) - low - tall
        layers = round(3 * min(low, 8) / 8) + round(2 * min(mid, 4) / 4) + round(2 * min(tall, 2) / 2)
        return {
            "composition": round(18 * min(len(kinds), 6) / 6) + round(10 * mixed / max(1, len(edges))) + layers,
            "network": round(20 * len(self.connected_cells()) / len(CELLS)) + round(10 * min(functional, 12) / 12),
            "synergy": round(7 * min(functional, 12) / 12) + (5 if "observatory" in kinds else 0)
                       + min(3, sum(suite <= kinds for suite in suites) * 3),
            "style": max(style.values(), default=0),
            "tasks": min(5, len(self.claimed_tasks) * 2),
        }

    def check_complete(self):
        if not self.finished and len(self.placed) == len(CELLS) and not self.pending:
            self.score_breakdown = self.calculate_score()
            self.score = sum(self.score_breakdown.values())
            self.final_style_scores = self.city_style_scores()
            self.finished = True
            self.result_visible = True
            self.tech_open = False
            self.city_open = False
            self.relocation_mode = False
            self.relocation_source = None
            self.selected = None
            self.toast_timer = 0

    def update(self, dt):
        self.pulse += dt
        if self.toast_timer > 0:
            self.toast_timer -= dt
        for item in self.pending[:]:
            item["time"] -= dt
            if item["time"] <= 0:
                self.resolve_reward(item)
                self.pending.remove(item)
        for p in self.particles[:]:
            p["life"] -= dt
            p["x"] += (p["tx"] - p["x"]) * dt * 2.2
            p["y"] += (p["ty"] - p["y"]) * dt * 2.2
            if p["life"] <= 0:
                self.particles.remove(p)
        if not self.finished:
            tasks_completed = self.check_tasks()
            combinations_completed = self.check_combinations()
            if tasks_completed and combinations_completed:
                self.toast = "愿景达成 · " + " / ".join(tasks_completed) + "；发现组合 · " + " / ".join(combinations_completed)
        self.check_complete()

    def draw_particles(self):
        for p in self.particles:
            radius = max(1, int(5 * p["life"]))
            pygame.draw.circle(self.screen, p["color"], (int(p["x"]), int(p["y"])), radius)

    def handle_event(self, event):
        if event.type == pygame.QUIT:
            self.running = False
        elif event.type == pygame.KEYDOWN:
            if self.tutorial_step is not None:
                if event.key == pygame.K_ESCAPE:
                    self.tutorial_step = None
                elif event.key in (pygame.K_RETURN, pygame.K_SPACE):
                    self.tutorial_step = self.tutorial_step + 1 if self.tutorial_step < len(TUTORIAL_STEPS) - 1 else None
                return
            if self.result_visible:
                if event.key in (pygame.K_ESCAPE, pygame.K_RETURN):
                    self.result_visible = False
                    self.view_mode = "overview"
                return
            if self.tech_open:
                if event.key in (pygame.K_ESCAPE, pygame.K_t):
                    self.tech_open = False
                return
            if self.city_open:
                if event.key == pygame.K_ESCAPE:
                    self.city_open = False
                return
            if self.relocation_mode and event.key == pygame.K_ESCAPE:
                self.relocation_mode = False
                self.relocation_source = None
                return
            if self.view_mode == "overview" and event.key == pygame.K_ESCAPE:
                self.view_mode = "art"
                return
            if event.key == pygame.K_ESCAPE:
                self.running = False
            elif event.key == pygame.K_r:
                self.reset()
            elif event.key == pygame.K_t:
                if self.finished:
                    self.result_visible = True
                else:
                    self.tech_open = True
                    self.tech_feedback = ""
            elif event.key == pygame.K_v:
                self.view_mode = "art" if self.view_mode == "overview" else "overview"
                self.selected = None
                self.relocation_mode = False
                self.relocation_source = None
            elif event.key == pygame.K_c:
                self.city_open = True
            elif event.key == pygame.K_s and self.view_mode == "overview":
                self.export_showcase()
        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            pos = self.logical_pos(event.pos)
            if self.tutorial_step is not None:
                if pygame.Rect(520, 560, 240, 48).collidepoint(pos):
                    self.tutorial_step = self.tutorial_step + 1 if self.tutorial_step < len(TUTORIAL_STEPS) - 1 else None
                return
            if self.result_visible:
                if pygame.Rect(404, 620, 210, 44).collidepoint(pos):
                    self.result_visible = False
                    self.view_mode = "overview"
                elif pygame.Rect(666, 620, 210, 44).collidepoint(pos):
                    self.reset()
                    self.tutorial_step = None
                return
            if self.tech_open:
                if pygame.Rect(1124, 66, 42, 42).collidepoint(pos):
                    self.tech_open = False
                    return
                for kind in TECH_TREE:
                    if self.tech_rect(kind).collidepoint(pos):
                        self.research(kind)
                        break
                return
            if self.city_open:
                if pygame.Rect(1068, 95, 42, 42).collidepoint(pos):
                    self.city_open = False
                elif pygame.Rect(410, 184, 210, 32).collidepoint(pos):
                    self.city_page = "visions"
                elif pygame.Rect(660, 184, 210, 32).collidepoint(pos):
                    self.city_page = "combinations"
                return
            view_button = SHOWCASE_BACK if self.view_mode == "overview" else VIEW_BUTTON
            if view_button.collidepoint(pos):
                self.view_mode = "art" if self.view_mode == "overview" else "overview"
                self.selected = None
                self.relocation_mode = False
                self.relocation_source = None
                return
            city_button = SHOWCASE_VISION if self.view_mode == "overview" else CITY_BUTTON
            if city_button.collidepoint(pos):
                self.city_open = True
                return
            tech_button = SHOWCASE_SCORE if self.view_mode == "overview" else TECH_BUTTON
            if tech_button.collidepoint(pos):
                if self.finished:
                    self.result_visible = True
                else:
                    self.tech_open = True
                    self.tech_feedback = ""
                return
            if self.view_mode == "overview" and SHOWCASE_EXPORT.collidepoint(pos):
                self.export_showcase()
                return
            if self.finished:
                return
            if RELOCATE_BUTTON.collidepoint(pos):
                if self.view_mode != "overview":
                    self.begin_relocation()
                return
            if self.view_mode == "overview":
                return
            if SUPPLY_PREV.collidepoint(pos) or SUPPLY_NEXT.collidepoint(pos):
                direction = -1 if SUPPLY_PREV.collidepoint(pos) else 1
                self.supply_page = (self.supply_page + direction) % max(1, math.ceil(len(self.hand) / 3))
                return
            if BOARD_RECT.collidepoint(pos):
                self.click_cell(pos)
                return
            for idx, kind in enumerate(self.visible_hand()):
                if self.card_rect(idx).collidepoint(pos):
                    if not self.can_pay(kind):
                        self.toast = f"{TILE_INFO[kind]['name']} 需要 {self.missing_cost(kind)}"
                        self.toast_timer = 2.8
                        return
                    self.selected = None if self.selected == kind else kind
                    self.relocation_mode = False
                    self.relocation_source = None
                    self.toast = f"选择了 {TILE_INFO[kind]['name']}，点击棋盘灰色地块插装"
                    self.toast_timer = 2.4
                    return
            if pygame.Rect(758, 684, 450, 48).collidepoint(pos):
                if self.can_expand():
                    self.expand()
                else:
                    missing = next((label for label, done in self.expansion_requirements() if not done), "")
                    self.toast = f"还不能扩建：{missing}"
                    self.toast_timer = 2.8
        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 3:
            pos = self.logical_pos(event.pos)
            if not self.modal_open() and BOARD_RECT.collidepoint(pos):
                self.dismantle_at(pos)

    def render_frame(self):
        self.draw_background()
        if self.view_mode == "overview":
            self.draw_showcase()
        else:
            self.draw_board()
            self.draw_particles()
            self.draw_panel()
        if self.toast_timer > 0 and not self.modal_open() and self.view_mode != "overview":
            rect = pygame.Rect(54, 35, 625, 35)
            rounded(self.screen, rect, (13, 31, 49, 225), 12, (109, 169, 170), 1)
            text(self.screen, self.toast, rect.center, 14, CREAM, True, "center")
        self.draw_modals()
        self.draw_tutorial()
        self.present()

    def run(self):
        while self.running:
            dt = self.clock.tick(FPS) / 1000.0
            for event in pygame.event.get():
                self.handle_event(event)
            self.update(dt)
            self.render_frame()
            pygame.display.flip()
        pygame.quit()


if __name__ == "__main__":
    SkyCity().run()
