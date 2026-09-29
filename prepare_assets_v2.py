"""切分第二版欧提努斯动作图集，并生成透明精灵、主神之枪和程序图标。"""

from collections import deque
from pathlib import Path

import numpy as np
from PIL import Image, ImageChops, ImageDraw, ImageFilter, ImageFont
from scipy.ndimage import find_objects, label as label_components


ROOT = Path(__file__).resolve().parent
SOURCE = ROOT / "assets_v2"
OUT = ROOT / "assets" / "sprites_v2"

SHEETS = {
    "sheet_core_v2.png": [
        "idle_neutral", "idle_smile", "idle_smug",
        "wave_cheer", "jump_excited", "pat_bliss",
        "angry_pout", "surprise_shock", "cry_sad",
    ],
    "sheet_daily_v3_transparent.png": [
        "eat_happy", "eat_smug", "tea_calm",
        "yawn_sleepy", "confused", "shy_blush",
        "laugh_happy", "bored_sit", "gift_heart",
    ],
    "sheet_battle_v3_transparent.png": [
        "magic_focus", "magic_smug", "spear_float",
        "spear_ready", "spear_thrust", "spear_spin",
        "spear_victory", "spear_tired", "spear_guard",
    ],
}

# 图像生成器会让少量笔触跨过九宫格边界；这些区域只包含相邻格残片。
CELL_CLEAR_RECTS = {
    ("sheet_daily_v3_transparent.png", 1): [(0, 188, 38, 244)],
    ("sheet_daily_v3_transparent.png", 3): [(0, 0, 426, 31), (0, 397, 426, 410)],
    ("sheet_daily_v3_transparent.png", 4): [(0, 0, 426, 29), (0, 198, 13, 242)],
    ("sheet_daily_v3_transparent.png", 5): [(0, 0, 426, 31), (232, 389, 324, 410)],
    ("sheet_daily_v3_transparent.png", 7): [(0, 145, 14, 205)],
    ("sheet_battle_v3_transparent.png", 3): [(0, 0, 418, 9), (0, 375, 418, 418)],
    ("sheet_battle_v3_transparent.png", 4): [(0, 0, 418, 9), (0, 366, 418, 418), (409, 0, 418, 418)],
    ("sheet_battle_v3_transparent.png", 5): [(0, 0, 418, 9), (0, 390, 418, 418)],
    ("sheet_battle_v3_transparent.png", 7): [(399, 94, 418, 220)],
}

FINAL_CLEAR_RECTS = {
    "shy_blush": [(258, 444, 358, 480)],
    "spear_ready": [(45, 30, 150, 96)],
    "spear_thrust": [(450, 308, 466, 354)],
    "spear_tired": [(48, 35, 128, 93)],
}


def content_bbox(image: Image.Image, threshold: int = 4):
    alpha = image.getchannel("A")
    mask = alpha.point(lambda value: 255 if value > threshold else 0)
    return mask.getbbox()


def normalize(image: Image.Image, size: int = 480) -> Image.Image:
    image = image.convert("RGBA")
    bbox = content_bbox(image)
    if bbox is None:
        return Image.new("RGBA", (size, size), (0, 0, 0, 0))
    sprite = image.crop(bbox)
    limit = int(size * 0.94)
    scale = min(limit / sprite.width, limit / sprite.height)
    target = (max(1, round(sprite.width * scale)), max(1, round(sprite.height * scale)))
    sprite = sprite.resize(target, Image.Resampling.LANCZOS)
    canvas = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    x = (size - sprite.width) // 2
    y = size - sprite.height - int(size * 0.02)
    canvas.alpha_composite(sprite, (x, y))
    return canvas


def remove_border_fragments(image: Image.Image, threshold: int = 4, area_ratio: float = 0.04) -> Image.Image:
    """移除跨格生成时落入相邻单元格的小碎片，保留角色、道具和独立表情符号。"""
    image = image.convert("RGBA")
    alpha = image.getchannel("A")
    width, height = image.size
    pixels = alpha.load()
    visited = bytearray(width * height)
    components: list[tuple[list[tuple[int, int]], bool, tuple[int, int, int, int]]] = []

    for y in range(height):
        for x in range(width):
            offset = y * width + x
            if visited[offset] or pixels[x, y] <= threshold:
                continue
            queue = deque([(x, y)])
            visited[offset] = 1
            points: list[tuple[int, int]] = []
            min_x = max_x = x
            min_y = max_y = y
            touches_border = False
            while queue:
                px, py = queue.pop()
                points.append((px, py))
                min_x, max_x = min(min_x, px), max(max_x, px)
                min_y, max_y = min(min_y, py), max(max_y, py)
                if px <= 1 or py <= 1 or px >= width - 2 or py >= height - 2:
                    touches_border = True
                for nx, ny in ((px - 1, py), (px + 1, py), (px, py - 1), (px, py + 1)):
                    if not (0 <= nx < width and 0 <= ny < height):
                        continue
                    neighbor = ny * width + nx
                    if not visited[neighbor] and pixels[nx, ny] > threshold:
                        visited[neighbor] = 1
                        queue.append((nx, ny))
            components.append((points, touches_border, (min_x, min_y, max_x, max_y)))

    if not components:
        return image
    largest = max(len(points) for points, _, _ in components)
    cleaned = image.copy()
    draw = ImageDraw.Draw(cleaned)
    for points, touches_border, (min_x, min_y, max_x, max_y) in components:
        if touches_border and len(points) < largest * area_ratio:
            draw.rectangle(
                (max(0, min_x - 2), max(0, min_y - 2), min(width - 1, max_x + 2), min(height - 1, max_y + 2)),
                fill=(0, 0, 0, 0),
            )
    return cleaned


def keep_main_cutout(image: Image.Image, threshold: int = 12) -> Image.Image:
    """保留与角色主体相连的透明抠图，清掉背景提取留下的零散彩色像素。"""
    image = image.convert("RGBA")
    alpha = image.getchannel("A")
    width, height = image.size
    pixels = alpha.load()
    visited = bytearray(width * height)
    largest: list[tuple[int, int]] = []
    for y in range(height):
        for x in range(width):
            offset = y * width + x
            if visited[offset] or pixels[x, y] <= threshold:
                continue
            queue = deque([(x, y)])
            visited[offset] = 1
            points: list[tuple[int, int]] = []
            while queue:
                px, py = queue.pop()
                points.append((px, py))
                for nx, ny in ((px - 1, py), (px + 1, py), (px, py - 1), (px, py + 1)):
                    if not (0 <= nx < width and 0 <= ny < height):
                        continue
                    neighbor = ny * width + nx
                    if not visited[neighbor] and pixels[nx, ny] > threshold:
                        visited[neighbor] = 1
                        queue.append((nx, ny))
            if len(points) > len(largest):
                largest = points

    if not largest:
        return image
    core = Image.new("L", image.size, 0)
    core_pixels = core.load()
    for x, y in largest:
        core_pixels[x, y] = 255
    # 向外恢复三像素抗锯齿边缘，同时不接回远离主体的杂点。
    keep = core.filter(ImageFilter.MaxFilter(7))
    image.putalpha(ImageChops.multiply(alpha, keep))
    return image


def hair_mask_and_stats(image: Image.Image):
    """返回最大金发连通区域及其 HSV 均值；分离的枪、魔法阵和食物不会入选。"""
    rgba = np.asarray(image.convert("RGBA"))
    rgb = rgba[:, :, :3].astype(np.float32)
    hsv = np.asarray(image.convert("RGB").convert("HSV")).astype(np.float32) / 255.0
    red, green, blue = rgb[:, :, 0], rgb[:, :, 1], rgb[:, :, 2]
    hue, saturation = hsv[:, :, 0], hsv[:, :, 1]
    candidate = (
        (rgba[:, :, 3] > 100)
        & (hue > 0.075) & (hue < 0.19)
        & (saturation > 0.18)
        & (red > 145) & (green > 90) & (blue < 195)
        & (red >= green * 0.94) & (green > blue * 1.12)
    )
    labels, count = label_components(candidate)
    if count == 0:
        return None, None
    areas = np.bincount(labels.ravel())
    areas[0] = 0
    mask = labels == int(np.argmax(areas))
    if int(mask.sum()) < 500:
        return None, None
    stats = tuple(float(hsv[:, :, channel][mask].mean()) for channel in range(3))
    return mask, stats


def normalize_hair_color(image: Image.Image, target_stats: tuple[float, float, float]) -> Image.Image:
    mask, source_stats = hair_mask_and_stats(image)
    if mask is None or source_stats is None:
        return image
    rgba = np.asarray(image.convert("RGBA")).copy()
    hsv = np.asarray(image.convert("RGB").convert("HSV")).astype(np.float32) / 255.0
    source_h, source_s, source_v = source_stats
    target_h, target_s, target_v = target_stats
    hsv[:, :, 0][mask] = np.mod(hsv[:, :, 0][mask] + target_h - source_h, 1.0)
    hsv[:, :, 1][mask] = np.clip(hsv[:, :, 1][mask] * target_s / max(0.01, source_s), 0.0, 1.0)
    hsv[:, :, 2][mask] = np.clip(hsv[:, :, 2][mask] + target_v - source_v, 0.0, 1.0)
    corrected = Image.fromarray(np.uint8(np.round(hsv * 255)), "HSV").convert("RGB")
    rgba[:, :, :3] = np.asarray(corrected)
    return Image.fromarray(rgba, "RGBA")


def extract_grid_subject(sheet: Image.Image, row: int, col: int) -> Image.Image:
    """按透明连通轮廓提取九宫格主体，允许帽尖、鞋和武器跨过名义格线。"""
    image = sheet.convert("RGBA")
    alpha_array = np.asarray(image.getchannel("A"))
    labels, count = label_components(alpha_array > 12, structure=np.ones((3, 3), dtype=np.uint8))
    component_slices = find_objects(labels)
    cell_width = image.width / 3
    cell_height = image.height / 3
    selected: list[int] = []

    for component_id in range(1, count + 1):
        component_slice = component_slices[component_id - 1]
        if component_slice is None:
            continue
        y_slice, x_slice = component_slice
        local = labels[y_slice, x_slice] == component_id
        area = int(local.sum())
        if area < 40:
            continue
        local_y, local_x = np.nonzero(local)
        center_x = x_slice.start + float(local_x.mean())
        center_y = y_slice.start + float(local_y.mean())
        assigned_col = min(2, max(0, int(center_x / cell_width)))
        assigned_row = min(2, max(0, int(center_y / cell_height)))
        if assigned_row == row and assigned_col == col:
            selected.append(component_id)

    if not selected:
        return Image.new("RGBA", image.size, (0, 0, 0, 0))

    core = Image.fromarray(np.where(np.isin(labels, selected), 255, 0).astype(np.uint8), "L")
    # 恢复阈值之外的三像素抗锯齿边缘，但不会把相邻格角色重新接进来。
    keep = core.filter(ImageFilter.MaxFilter(7))
    subject = image.copy()
    subject.putalpha(ImageChops.multiply(image.getchannel("A"), keep))
    return subject


def slice_sheet(path: Path, names: list[str]) -> dict[str, Image.Image]:
    sheet = Image.open(path).convert("RGBA")
    result = {}
    for index, name in enumerate(names):
        row, col = divmod(index, 3)
        result[name] = normalize(extract_grid_subject(sheet, row, col))
    return result


def normalize_spear(path: Path) -> Image.Image:
    image = Image.open(path).convert("RGBA")
    bbox = content_bbox(image, threshold=18)
    spear = image.crop(bbox) if bbox else image
    canvas = Image.new("RGBA", (160, 480), (0, 0, 0, 0))
    spear.thumbnail((148, 462), Image.Resampling.LANCZOS)
    canvas.alpha_composite(spear, ((160 - spear.width) // 2, (480 - spear.height) // 2))
    return canvas


def prepare_world_end_overlay(path: Path) -> Image.Image:
    """保留角色与主神之枪的相连主体，并为全屏演出留下透明安全边距。"""
    image = keep_main_cutout(Image.open(path), threshold=12)
    bbox = content_bbox(image, threshold=8)
    cutout = image.crop(bbox) if bbox else image.convert("RGBA")
    padding = max(36, round(max(cutout.size) * 0.035))
    canvas = Image.new(
        "RGBA",
        (cutout.width + padding * 2, cutout.height + padding * 2),
        (0, 0, 0, 0),
    )
    canvas.alpha_composite(cutout, (padding, padding))
    return canvas


def make_destroy_declaration() -> Image.Image:
    """把宣誓词预渲染为透明位图，避免全屏窗口启动早期出现缺字方框。"""
    size = (1800, 260)
    font_candidates = (
        Path("C:/Windows/Fonts/msyhbd.ttc"),
        Path("C:/Windows/Fonts/msyh.ttc"),
        Path("C:/Windows/Fonts/simhei.ttf"),
    )
    font_path = next((path for path in font_candidates if path.exists()), None)
    if font_path is None:
        raise FileNotFoundError("No Chinese font available for declaration artwork")
    font = ImageFont.truetype(str(font_path), 64)
    lines = (
        "琐碎的争斗就到此为止吧——",
        "此刻，就让世界在我的意志下归于沉寂",
    )

    mask = Image.new("L", size, 0)
    mask_draw = ImageDraw.Draw(mask)
    positions = []
    for index, line in enumerate(lines):
        bbox = mask_draw.textbbox((0, 0), line, font=font, stroke_width=1)
        x = (size[0] - (bbox[2] - bbox[0])) // 2
        y = 34 + index * 102
        positions.append((x, y, line))
        mask_draw.text((x, y), line, font=font, fill=255, stroke_width=1, stroke_fill=255)

    glow = mask.filter(ImageFilter.GaussianBlur(11))
    image = Image.new("RGBA", size, (0, 0, 0, 0))
    glow_layer = Image.new("RGBA", size, (255, 177, 53, 0))
    glow_layer.putalpha(glow.point(lambda value: round(value * 0.60)))
    image.alpha_composite(glow_layer)
    draw = ImageDraw.Draw(image)
    for x, y, line in positions:
        draw.text(
            (x + 3, y + 4), line, font=font,
            fill=(0, 0, 0, 210), stroke_width=3, stroke_fill=(0, 0, 0, 190),
        )
        draw.text(
            (x, y), line, font=font,
            fill=(255, 249, 218, 255), stroke_width=2, stroke_fill=(183, 103, 31, 245),
        )
    return image


def make_icon(idle: Image.Image) -> None:
    # 用户指定透明底全身照：直接复用已确认的母模型，不增加圆框、底色、阴影或重绘偏差。
    idle = keep_main_cutout(idle)
    bbox = content_bbox(idle)
    sprite = idle.crop(bbox) if bbox else idle.copy()
    sprite.thumbnail((236, 236), Image.Resampling.LANCZOS)
    icon = Image.new("RGBA", (256, 256), (0, 0, 0, 0))
    icon.alpha_composite(sprite, ((256 - sprite.width) // 2, (256 - sprite.height) // 2))
    icon.save(ROOT / "assets" / "othinus_icon_v4_fullbody.png", optimize=True)
    icon.save(
        ROOT / "assets" / "othinus_icon_v4_fullbody.ico",
        format="ICO",
        sizes=[(16, 16), (24, 24), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)],
    )


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    sprites: dict[str, Image.Image] = {}
    for filename, names in SHEETS.items():
        sprites.update(slice_sheet(SOURCE / filename, names))

    sprites["sleep_touma_a"] = normalize(Image.open(SOURCE / "sleep_touma_a_v2.png"))
    sprites["sleep_touma_b"] = normalize(Image.open(SOURCE / "sleep_touma_b_v2.png"))
    sprites["drag_dangle"] = normalize(keep_main_cutout(Image.open(SOURCE / "drag_dangle_v1_transparent.png")))
    sprites["walk_step"] = normalize(keep_main_cutout(Image.open(SOURCE / "walk_step_v1_transparent.png")))
    sprites["edge_peek"] = normalize(keep_main_cutout(Image.open(SOURCE / "edge_peek_v1_transparent.png")))

    _, target_hair = hair_mask_and_stats(sprites["idle_neutral"])
    if target_hair is not None:
        for name in list(sprites):
            sprites[name] = normalize_hair_color(sprites[name], target_hair)

    for name, sprite in sprites.items():
        sprite.save(OUT / f"{name}.png", optimize=True)

    spear = normalize_spear(SOURCE / "gungnir_v2.png")
    spear.save(OUT / "gungnir_float.png", optimize=True)
    world_end = prepare_world_end_overlay(SOURCE / "destroy_world_v1_raw.png")
    world_end.save(ROOT / "assets" / "destroy_world_full.png", optimize=True)
    make_destroy_declaration().save(ROOT / "assets" / "destroy_declaration.png", optimize=True)
    make_icon(sprites["idle_smile"])

    print(f"sprites={len(sprites)}, out={OUT}")
    print(f"core_alpha={Image.open(SOURCE / 'sheet_core_v2.png').getchannel('A').getextrema()}")


if __name__ == "__main__":
    main()
