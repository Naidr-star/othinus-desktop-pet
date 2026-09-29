"""将透明九宫格切分为桌宠动作精灵，并生成 Windows 多尺寸图标。"""

from pathlib import Path

from PIL import Image


ROOT = Path(__file__).resolve().parent
SOURCE = ROOT / "assets" / "othinus_sprite_sheet.png"
OUT = ROOT / "assets" / "sprites"
NAMES = [
    "idle", "wave", "jump",
    "angry", "magic", "surprise",
    "eat", "sleep", "cry",
]


def normalize(cell: Image.Image, size: int = 420) -> Image.Image:
    alpha = cell.getchannel("A")
    bbox = alpha.getbbox()
    if bbox is None:
        return Image.new("RGBA", (size, size), (0, 0, 0, 0))
    sprite = cell.crop(bbox)
    limit = int(size * 0.92)
    scale = min(limit / sprite.width, limit / sprite.height)
    target = (max(1, round(sprite.width * scale)), max(1, round(sprite.height * scale)))
    sprite = sprite.resize(target, Image.Resampling.LANCZOS)
    canvas = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    x = (size - sprite.width) // 2
    y = size - sprite.height - int(size * 0.025)
    canvas.alpha_composite(sprite, (x, y))
    return canvas


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    sheet = Image.open(SOURCE).convert("RGBA")
    cell_w = sheet.width // 3
    cell_h = sheet.height // 3

    sprites = {}
    for index, name in enumerate(NAMES):
        row, col = divmod(index, 3)
        left = col * cell_w
        top = row * cell_h
        right = sheet.width if col == 2 else (col + 1) * cell_w
        bottom = sheet.height if row == 2 else (row + 1) * cell_h
        sprite = normalize(sheet.crop((left, top, right, bottom)))
        sprite.save(OUT / f"{name}.png", optimize=True)
        sprites[name] = sprite

    # 用待机精灵制作程序和系统托盘图标。
    icon_canvas = Image.new("RGBA", (256, 256), (7, 17, 25, 0))
    idle = sprites["idle"]
    bbox = idle.getchannel("A").getbbox()
    idle = idle.crop(bbox)
    idle.thumbnail((244, 244), Image.Resampling.LANCZOS)
    icon_canvas.alpha_composite(idle, ((256 - idle.width) // 2, 256 - idle.height))
    icon_canvas.save(ROOT / "assets" / "othinus_icon.png", optimize=True)
    icon_canvas.save(
        ROOT / "assets" / "othinus_icon.ico",
        format="ICO",
        sizes=[(16, 16), (24, 24), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)],
    )
    print(f"sheet={sheet.size}, sprites={len(sprites)}, alpha={sheet.getchannel('A').getextrema()}")


if __name__ == "__main__":
    main()
