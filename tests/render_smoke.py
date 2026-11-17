"""Render desktop views with SDL's dummy driver and exercise modal clicks."""
import os
import sys
from pathlib import Path

os.environ["SDL_VIDEODRIVER"] = "dummy"
os.environ["SDL_AUDIODRIVER"] = "dummy"
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pygame

import game
from test_gameplay import GameplayRegressionTests


def click(city, logical):
    scale = min(city.display_size[0] / game.WIDTH, city.display_size[1] / game.HEIGHT)
    offset = ((city.display_size[0] - game.WIDTH * scale) / 2,
              (city.display_size[1] - game.HEIGHT * scale) / 2)
    pos = (round(offset[0] + logical[0] * scale), round(offset[1] + logical[1] * scale))
    city.handle_event(pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1, pos=pos))


def capture(city, name, size, output, hover=None):
    city.display = pygame.display.set_mode(size)
    city.display_size = size
    city.text_layer = pygame.Surface(size, pygame.SRCALPHA)
    city.modal_text_layer = pygame.Surface(size, pygame.SRCALPHA)
    labels = []
    original_text = game.text

    def checked_text(*args, **kwargs):
        rect = original_text(*args, **kwargs)
        labels.append((str(args[1]), rect, game.TEXT_TARGET))
        return rect

    game.text = checked_text
    original_mouse = pygame.mouse.get_pos
    if hover is not None:
        scale = min(size[0] / game.WIDTH, size[1] / game.HEIGHT)
        offset = ((size[0] - game.WIDTH * scale) / 2, (size[1] - game.HEIGHT * scale) / 2)
        physical = tuple(round(offset[index] + hover[index] * scale) for index in range(2))
        pygame.mouse.get_pos = lambda: physical
    try:
        city.render_frame()
    finally:
        game.text = original_text
        pygame.mouse.get_pos = original_mouse
    target = city.modal_text_layer if city.modal_open() else city.text_layer
    visible = [(label, rect) for label, rect, layer in labels if layer is target]
    for label, rect in visible:
        assert pygame.Rect((0, 0), size).contains(rect), f"{name}: text outside display: {label} {rect}"
    for index, (label, rect) in enumerate(visible):
        for other_label, other_rect in visible[index + 1:]:
            assert not rect.colliderect(other_rect), f"{name}: text overlap: {label!r} / {other_label!r}"
    pixels = pygame.surfarray.array3d(city.display)
    assert pixels.std() > 15, f"{name}: blank scene"
    pygame.image.save(city.display, str(output / f"{name}_{size[0]}x{size[1]}.png"))
    return [label for label, _ in visible]


def main():
    output = Path(__file__).resolve().parents[1] / "verification"
    output.mkdir(exist_ok=True)
    city = game.SkyCity()
    city.tutorial_step = None
    route = GameplayRegressionTests()
    route.bootstrap(city)
    for size in ((1280, 800), (1920, 1080)):
        for step in range(len(game.TUTORIAL_STEPS)):
            city.tutorial_step = step
            capture(city, f"tutorial_{step + 1}", size, output)
        city.tutorial_step = None
        capture(city, "play", size, output)
        click(city, game.TECH_BUTTON.center)
        assert city.tech_open
        capture(city, "technology", size, output)
        click(city, game.SkyCity.tech_rect("waterfall").center)
        assert "waterfall" in city.unlocked
        click(city, (1145, 87))
        assert not city.tech_open
        click(city, game.CITY_BUTTON.center)
        assert city.city_open
        capture(city, "visions", size, output)
        click(city, (765, 200))
        assert city.city_page == "combinations"
        capture(city, "combinations", size, output)
        click(city, (515, 200))
        assert city.city_page == "visions"
        click(city, (1089, 116))
        assert not city.city_open
        click(city, game.RELOCATE_BUTTON.center)
        assert city.relocation_mode
        city.click_cell(game.cell_center((4, 1)))
        capture(city, "relocation", size, output)
        city.begin_relocation()
        assert not city.relocation_mode
        city.selected = "cloud"
        labels = capture(city, "placement", size, output, hover=game.cell_center((4, 2)))
        assert any("水汽 +" in label for label in labels)
        city.settled_builds.add(((4, 2), "cloud"))
        labels = capture(city, "rebuild_preview", size, output, hover=game.cell_center((4, 2)))
        assert any("重建不再产出" in label for label in labels)
        city.settled_builds.remove(((4, 2), "cloud"))
        city.selected = None
    route.grow_natural(city)
    assert city.finished and city.result_visible
    print(f"Natural route: 36 cells, {city.score}/100, resources={dict(city.resources)}")
    for size in ((1280, 800), (1920, 1080)):
        city.result_visible = True
        capture(city, "result", size, output)
        click(city, (509, 642))
        assert not city.result_visible
        assert city.view_mode == "overview"
        capture(city, "overview", size, output)
        click(city, game.SHOWCASE_BACK.center)
        assert city.view_mode == "art"
        capture(city, "city", size, output)
        click(city, game.CITY_BUTTON.center)
        assert city.city_open
        capture(city, "visions_complete", size, output)
        click(city, (765, 200))
        capture(city, "combinations_complete", size, output)
        click(city, (515, 200))
        click(city, (1089, 116))
        click(city, game.TECH_BUTTON.center)
        assert city.result_visible
    click(city, (771, 642))
    assert not city.finished and not city.placed
    pygame.quit()
    print(f"Rendered views and modal input checks passed: {output}")


if __name__ == "__main__":
    main()
